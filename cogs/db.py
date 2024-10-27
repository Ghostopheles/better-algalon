import os
import httpx
import asyncio

from dotenv import load_dotenv
from typing import Union

load_dotenv("F:/better-algalon/.env")

DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_URL = os.getenv("DB_URL")
DB_PORT = os.getenv("DB_PORT")
DB_NAMESPACE = os.getenv("DB_NAMESPACE")
DB_DATABASE = os.getenv("DB_DATABASE")

DB_URL = f"http://{DB_URL}:{DB_PORT}"

HEADERS = {
    "Accept": "application/json",
    "surreal-ns": DB_NAMESPACE,
    "surreal-db": DB_DATABASE,
}

HTTPX_CLIENT = httpx.AsyncClient(
    base_url=DB_URL, headers=HEADERS, auth=httpx.BasicAuth(DB_USER, DB_PASS), http2=True
)


class BaseModel:
    @classmethod
    def from_json(cls, data: dict):
        new_obj = cls()
        for anno in cls.__annotations__:
            if anno not in data:
                continue

            setattr(new_obj, anno, data[anno])

        return new_obj

    def __repr__(self):
        desc = f"{str(self.__class__).replace(">", "")} "
        for anno in self.__annotations__:
            desc += f"{anno}='{getattr(self, anno)}' "

        desc = desc[:-1] + ">"
        return desc


class Locale(BaseModel):
    id: str
    enabled: bool


class Region(BaseModel):
    id: str
    enabled: bool
    locale: Locale
    name: str


class Branch(BaseModel):
    id: str
    enabled: bool
    encrypted: bool
    internal: bool
    internal_name: str
    public_name: str
    test: bool


class Version(BaseModel):
    id: str
    branch: Branch
    build_number: int
    build_text: str
    found_at: str
    keyring: str
    build_config: str
    cdn_config: str
    product_config: str
    region: Region
    seqn: int


async def execute_query(query: str) -> dict:
    res = await HTTPX_CLIENT.post("/sql", data=query)
    res.raise_for_status()
    return res.json()[0]["result"]


def get_channel_key_for_game(game: str):
    return f"{game}_channel"


class AlgalonDB:
    @staticmethod
    async def get_current_version_for_branch(branch: str, region: str) -> Version:
        query = f"SELECT * FROM version WHERE region=region:{region} AND branch=branch:{branch};"
        results = await execute_query(query)
        return Version.from_json(results[0])

    # GUILD CONFIG STUFF
    @staticmethod
    async def get_all_guilds_watching_branch(branch: str):
        query = f"SELECT * FROM guild WHERE ->(watching WHERE out=branch:{branch});"
        results = await execute_query(query)
        return [int(guild["id"].split(":")[1]) for guild in results]

    @staticmethod
    async def get_notification_channel_for_guild(
        guild_id: Union[str, int], game: str
    ) -> int:
        channel_key = get_channel_key_for_game(game)
        query = f"SELECT {channel_key} FROM guild:{guild_id};"
        results = await execute_query(query)
        return results[0][f"{channel_key}"]

    @staticmethod
    async def set_notification_channel_for_guild(
        guild_id: Union[str, int], game: str, channel_id: Union[str, int]
    ) -> bool:
        channel_key = get_channel_key_for_game(game)
        query = f"UPDATE guild:{guild_id} SET {channel_key}={channel_id};"
        results = await execute_query(query)
        return results[0][channel_key] == channel_id

    @staticmethod
    async def get_guild_watchlist(guild_id: Union[int, str]) -> list[Branch]:
        query = f"SELECT out FROM guild:{guild_id}->watching;"
        results = await execute_query(query)
        watchlist = []
        for result in results:
            branch_query = f"SELECT * FROM {result['out']}"
            branch = await execute_query(branch_query)
            watchlist.append(Branch.from_json(branch[0]))

        return watchlist

    @staticmethod
    async def check_guild_exists(guild_id: Union[int, str]):
        query = f"SELECT * FROM guild:{guild_id};"
        results = await execute_query(query)
        if len(results) == 0:
            query = f"CREATE guild:{guild_id};"

    @staticmethod
    async def is_on_guild_watchlist(guild_id: Union[int, str], branch: str) -> bool:
        query = f"SELECT out FROM guild:{guild_id}->watching WHERE out=branch:{branch};"
        results = await execute_query(query)
        return len(results) > 0

    @staticmethod
    async def add_to_guild_watchlist(guild_id: Union[int, str], branch: str) -> bool:
        if await AlgalonDB.is_on_guild_watchlist(guild_id, branch):
            return False

        query = f"RELATE guild:{guild_id}->watching->branch:{branch};"
        results = await execute_query(query)
        return (
            results[0]["in"] == f"guild:{guild_id}"
            and results[0]["out"] == f"branch:{branch}"
        )

    @staticmethod
    async def remove_from_guild_watchlist(
        guild_id: Union[int, str], branch: str
    ) -> bool:
        if not await AlgalonDB.is_on_guild_watchlist(guild_id, branch):
            return False

        query = f"DELETE guild:{guild_id}->watching WHERE out=branch:{branch};"
        results = await execute_query(query)
        return len(results) == 0

    # USER CONFIG STUFF

    @staticmethod
    async def get_all_users_watching_branch(branch: str):
        query = f"SELECT * FROM user WHERE ->(watching WHERE out=branch:{branch});"
        results = await execute_query(query)
        return [int(user["id"].split(":")[1]) for user in results]

    @staticmethod
    async def get_user_watchlist(user_id: Union[int, str]) -> list[Branch]:
        query = f"SELECT out FROM user:{user_id}->watching;"
        results = await execute_query(query)
        watchlist = []
        for result in results:
            branch_query = f"SELECT * FROM {result['out']}"
            branch = await execute_query(branch_query)
            watchlist.append(Branch.from_json(branch[0]))

        return watchlist

    @staticmethod
    async def is_on_user_watchlist(user_id: Union[int, str], branch: str) -> bool:
        query = f"SELECT out FROM user:{user_id}->watching WHERE out=branch:{branch};"
        results = await execute_query(query)
        return len(results) > 0

    @staticmethod
    async def add_to_user_watchlist(user_id: Union[int, str], branch: str) -> bool:
        if await AlgalonDB.is_on_user_watchlist(user_id, branch):
            return False

        query = f"RELATE user:{user_id}->watching->branch:{branch};"
        results = await execute_query(query)
        return (
            results[0]["in"] == f"user:{user_id}"
            and results[0]["out"] == f"branch:{branch}"
        )

    @staticmethod
    async def remove_from_user_watchlist(user_id: Union[int, str], branch: str) -> bool:
        if not await AlgalonDB.is_on_user_watchlist(user_id, branch):
            return False

        query = f"DELETE user:{user_id}->watching WHERE out=branch:{branch};"
        results = await execute_query(query)
        return len(results) == 0

    # METADATA MONITORING

    ALL_METADATA_FIELDS = None

    @staticmethod
    async def get_all_metadata_fields() -> list[str]:
        if AlgalonDB.ALL_METADATA_FIELDS is not None:
            return AlgalonDB.ALL_METADATA_FIELDS

        query = f"SELECT id FROM metadata_field;"
        results = await execute_query(query)
        AlgalonDB.ALL_METADATA_FIELDS = [
            result["id"].split(":")[1] for result in results
        ]
        return AlgalonDB.ALL_METADATA_FIELDS

    @staticmethod
    async def get_all_monitors_for_branch_field(branch: str, field: str) -> list[int]:
        print(branch, field)
        query = f"SELECT id FROM user WHERE ->(monitoring WHERE out=metadata_field:{field} AND branches CONTAINS branch:{branch});"
        results = await execute_query(query)
        return [int(result["id"].split(":")[1]) for result in results]

    @staticmethod
    async def is_user_monitoring(
        user_id: Union[int, str], branch: str, field: str
    ) -> bool:
        query = f"SELECT * FROM user:{user_id}->monitoring WHERE out=metadata_field:{field} AND branches CONTAINS branch:{branch};"
        results = await execute_query(query)
        return len(results) > 0

    @staticmethod
    async def user_monitor(user_id: Union[int, str], branch: str, field: str) -> bool:
        if await AlgalonDB.is_user_monitoring(user_id, branch, field):
            return False

        query = f"""LET $entry_exists = (SELECT * FROM user:{user_id}->monitoring WHERE out=metadata_field:{field});
        IF array::len($entry_exists) > 0 THEN
            UPDATE monitoring SET branches += branch:{branch} WHERE in=user:{user_id} AND out=metadata_field:{field};
        ELSE
            RELATE user:{user_id}->monitoring->metadata_field:{field} SET branches = <set>[branch:{branch}];
        END;"""
        results = await execute_query(query)
        print(results)

    @staticmethod
    async def user_unmonitor(user_id: Union[int, str], branch: str, field: str) -> bool:
        if not await AlgalonDB.is_user_monitoring(user_id, branch, field):
            return False

        query = f"""LET $entry_exists = (SELECT * FROM user:{user_id}->monitoring WHERE out=metadata_field:{field});
        IF array::len($entry_exists) > 0 THEN
            UPDATE monitoring SET branches -= branch:{branch} WHERE in=user:{user_id} AND out=metadata_field:{field};
        END;"""
        results = await execute_query(query)
        print(results)


TEST_GUILD_ID = 193762909220896769
TEST_USER_ID = 130987844125720576


async def main():
    print(await AlgalonDB.get_current_version_for_branch("wow", "us"))
    print(await AlgalonDB.get_notification_channel_for_guild(87306153297457152, "bnet"))
    print(
        await AlgalonDB.set_notification_channel_for_guild(
            TEST_GUILD_ID, "bnet", TEST_GUILD_ID
        )
    )
    print(await AlgalonDB.add_to_guild_watchlist(TEST_GUILD_ID, "wow"))
    print(await AlgalonDB.remove_from_guild_watchlist(TEST_GUILD_ID, "wow"))
    print(await AlgalonDB.get_guild_watchlist(TEST_GUILD_ID))
    print(await AlgalonDB.is_on_guild_watchlist(TEST_GUILD_ID, "wowt"))

    print(await AlgalonDB.add_to_user_watchlist(TEST_USER_ID, "wow"))
    print(await AlgalonDB.remove_from_user_watchlist(TEST_USER_ID, "wow"))
    print(await AlgalonDB.get_user_watchlist(TEST_USER_ID))
    print(await AlgalonDB.is_on_user_watchlist(TEST_USER_ID, "wowt"))

    print(await AlgalonDB.get_all_users_watching_branch("wow"))
    print(await AlgalonDB.get_all_guilds_watching_branch("wow"))


if __name__ == "__main__":
    asyncio.run(main())
