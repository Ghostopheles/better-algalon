import os
import httpx
import asyncio

from typing import Union

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
    enabled: bool = False
    encrypted: bool = False
    internal: bool = False
    internal_name: str
    public_name: str
    test: bool = False


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


async def execute_query(query: str, **kwargs) -> dict:
    query_params = httpx.QueryParams(kwargs)
    res = await HTTPX_CLIENT.post("/sql", data=query, params=query_params)
    res.raise_for_status()
    return res.json()[0]["result"]


def get_channel_key_for_game(game: str):
    return f"{game}_channel"


class AlgalonDB:
    @staticmethod
    async def get_current_version_for_branch(branch: str, region: str) -> Version:
        query = "SELECT * FROM version WHERE region=type::thing('region', $region) AND branch=type::thing('branch', $branch);"
        results = await execute_query(query, branch=branch, region=region)
        return Version.from_json(results[0])

    # GUILD CONFIG STUFF
    @staticmethod
    async def get_all_guilds_watching_branch(branch: str):
        query = "SELECT * FROM guild WHERE ->(watching WHERE out=type::thing('branch', $branch));"
        results = await execute_query(query, branch=branch)
        return [int(guild["id"].split(":")[1]) for guild in results]

    @staticmethod
    async def get_notification_channel_for_guild(
        guild_id: Union[str, int], game: str
    ) -> int:
        channel_key = get_channel_key_for_game(game)
        query = "SELECT type::field($channel_key) FROM type::thing('guild', $guild_id);"
        results = await execute_query(query, channel_key=channel_key, guild_id=guild_id)
        return results[0]

    @staticmethod
    async def set_notification_channel_for_guild(
        guild_id: Union[str, int], game: str, channel_id: Union[str, int]
    ) -> bool:
        channel_key = get_channel_key_for_game(game)
        query = f"UPDATE type::thing('guild', $guild_id) SET {channel_key}=type::int($channel_id);"
        await execute_query(query, guild=guild_id, channel_id=channel_id)
        return True

    @staticmethod
    async def get_guild_watchlist(guild_id: Union[int, str]) -> list[Branch]:
        query = "SELECT ->watching.out.* AS branches FROM type::thing('guild', $guild_id) FETCH branch;"
        results = await execute_query(query, guild_id=guild_id)
        watchlist = [Branch.from_json(branch) for branch in results[0]["branches"]]
        return watchlist

    @staticmethod
    async def check_guild_exists(guild_id: Union[int, str]):
        query = "SELECT * FROM type::thing('guild', $guild_id);"
        results = await execute_query(query, guild_id=guild_id)
        if len(results) == 0:
            query = "CREATE type::thing('guild', $guild_id);"
            await execute_query(query, guild_id=guild_id)

    @staticmethod
    async def is_on_guild_watchlist(guild_id: Union[int, str], branch: str) -> bool:
        watchlist = await AlgalonDB.get_guild_watchlist(guild_id)
        for entry in watchlist:
            if entry.internal_name == branch:
                return True

        return False

    @staticmethod
    async def add_to_guild_watchlist(guild_id: Union[int, str], branch: str) -> bool:
        query = """LET $guild = type::thing('guild', $guild_id);
        LET $branch_rec = type::thing('branch', $branch);
        RELATE $guild->watching->$branch_rec;"""
        await execute_query(query, guild_id=guild_id, branch=branch)
        return True

    @staticmethod
    async def remove_from_guild_watchlist(
        guild_id: Union[int, str], branch: str
    ) -> bool:
        query = "DELETE type::thing('guild', $guild_id)->watching WHERE out=type::thing('branch', $branch);"
        results = await execute_query(query, guild_id=guild_id, branch=branch)
        return len(results) == 0

    # USER CONFIG STUFF

    @staticmethod
    async def get_all_users_watching_branch(branch: str):
        query = "SELECT * FROM user WHERE ->(watching WHERE out=type::thing('branch', $branch));"
        results = await execute_query(query, branch=branch)
        return [int(user["id"].split(":")[1]) for user in results]

    @staticmethod
    async def get_user_watchlist(user_id: Union[int, str]) -> list[Branch]:
        query = "SELECT ->watching.out.* AS branches FROM type::thing('user', $user_id) FETCH branch;"
        results = await execute_query(query, user_id=user_id)
        watchlist = [Branch.from_json(branch) for branch in results[0]["branches"]]
        return watchlist

    @staticmethod
    async def is_on_user_watchlist(user_id: Union[int, str], branch: str) -> bool:
        watchlist = await AlgalonDB.get_user_watchlist(user_id)
        for entry in watchlist:
            if entry.internal_name == branch:
                return True

        return False

    @staticmethod
    async def add_to_user_watchlist(user_id: Union[int, str], branch: str) -> bool:
        query = """LET $user = type::thing('user', $user_id);
        LET $branch_rec = type::thing('branch', $branch);
        RELATE $user->watching->$branch_rec;"""
        await execute_query(query, user_id=user_id, branch=branch)
        return True

    @staticmethod
    async def remove_from_user_watchlist(user_id: Union[int, str], branch: str) -> bool:
        query = "DELETE type::thing('user', $user_id)->watching WHERE out=type::thing('branch', $branch);"
        results = await execute_query(query, user_id=user_id, branch=branch)
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
        query = "SELECT id FROM user WHERE ->(monitoring WHERE out=type::thing('metadata_field', $field) AND branches CONTAINS type::thing('branch', $branch));"
        results = await execute_query(query, field=field, branch=branch)
        return [int(result["id"].split(":")[1]) for result in results]

    @staticmethod
    async def is_user_monitoring(
        user_id: Union[int, str], branch: str, field: str
    ) -> bool:
        query = "SELECT * FROM type::thing('user', $user_id)->monitoring WHERE out=type::thing('metadata_field', $field) AND branches CONTAINS type::thing('branch', $branch);"
        results = await execute_query(
            query, user_id=user_id, branch=branch, field=field
        )
        return len(results) > 0

    @staticmethod
    async def user_monitor(user_id: Union[int, str], branch: str, field: str) -> bool:
        if await AlgalonDB.is_user_monitoring(user_id, branch, field):
            return False

        query = """LET $user = type::thing('user', $user_id);
        LET $meta_field = type::thing('metadata_field', $field);
        LET $branch_rec = type::thing('branch', $branch);

        LET $entry_exists = (SELECT * FROM $user->monitoring WHERE out=$meta_field);
        IF array::len($entry_exists) > 0 THEN
            UPDATE monitoring SET branches += $branch_rec WHERE in=$user AND out=$meta_field;
        ELSE
            RELATE $user->monitoring->$meta_field SET branches = <set>[$branch_rec];
        END;"""
        await execute_query(query, user_id=user_id, branch=branch, field=field)
        return True

    @staticmethod
    async def user_unmonitor(user_id: Union[int, str], branch: str, field: str) -> bool:
        if not await AlgalonDB.is_user_monitoring(user_id, branch, field):
            return False

        query = """LET $user = type::thing('user', $user_id);
        LET $meta_field = type::thing('metadata_field', $field);
        LET $branch_rec = type::thing('branch', $branch);

        LET $entry_exists = (SELECT * FROM $user->monitoring WHERE out=$meta_field);
        IF array::len($entry_exists) > 0 THEN
            UPDATE monitoring SET branches -= $branch_rec WHERE in=$user AND out=$meta_field;
        END;"""
        await execute_query(query, user_id=user_id, branch=branch, field=field)
        return True

    # MISC

    @staticmethod
    async def fetch_branch_entry(branch: str) -> Branch:
        query = "SELECT * FROM type::thing('branch', $branch);"
        branch = await execute_query(query, branch=branch)
        return Branch.from_json(branch[0])

    @staticmethod
    async def get_branches_for_game(game: str) -> list[Branch]:
        query = "SELECT in FROM branchxgame WHERE out=type::thing('game', $game);"
        results = await execute_query(query, game=game)
        coros = [AlgalonDB.fetch_branch_entry(result["in"]) for result in results]
        data = await asyncio.gather(*coros)
        return [i for i in data if i is not None]

    @staticmethod
    async def get_game_from_branch(branch: str) -> str:
        query = f"SELECT out FROM branchxgame WHERE in=type::thing('branch', $branch);"
        results = await execute_query(query, branch=branch)
        return results[0]["out"].split(":")[1]
