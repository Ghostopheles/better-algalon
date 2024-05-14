import os
import json
import logging

from typing import Union, TypeVar, Optional

from .config import CacheConfig
from .config import SUPPORTED_GAMES, SUPPORTED_PRODUCTS

SELF_PATH = os.path.dirname(os.path.realpath(__file__))

logger = logging.getLogger("discord.cdn.user-cfg")

# userID type alias, have to use the old way because old python :(
UID = TypeVar("UID", str, int)


class UserEntry:
    def __init__(self, user_id: UID, user_entry: Optional[dict] = None):
        self.__entry = user_entry if user_entry else self.__get_default_entry()
        self.user_id = str(user_id)
        self.watchlist: list[str] = self.__entry["watchlist"]

    def __get_default_entry(self) -> dict:
        return {"watchlist": []}

    def to_json(self) -> dict:
        return {"watchlist": self.watchlist}

    def get_user_id(self) -> str:
        return self.user_id

    def get_watchlist(self) -> list[str]:
        return self.watchlist

    def is_on_watchlist(self, branch: str) -> bool:
        return branch in self.watchlist

    def add_to_watchlist(self, branch: str) -> bool:
        if not SUPPORTED_PRODUCTS.has_key(branch) or self.is_on_watchlist(branch):
            return False

        self.watchlist.append(branch)
        return True

    def remove_from_watchlist(self, branch: str) -> bool:
        if not SUPPORTED_PRODUCTS.has_key(branch) or not self.is_on_watchlist(branch):
            return False

        self.watchlist.remove(branch)
        return True


class UserTable:
    def __init__(self, user_table: dict):
        self.__user_table = user_table
        self.__users = self.__generate_users()
        self.__user_lookup = None
        self.__update_lookup()  # populates __user_lookup w/ __users keys

        self.__current_index = 0
        self.__num_users = len(self.__user_lookup)

    def __iter__(self):
        return self

    def __next__(self) -> tuple[UID, UserEntry]:
        if self.__current_index < self.__num_users:
            key = self.__user_lookup[self.__current_index]
            entry = self.__users[key]
            self.__current_index += 1
            return key, entry
        else:
            self.__current_index = 0
            raise StopIteration

    def __generate_users(self) -> dict[UID, UserEntry]:
        users = {}
        for user_id, user_entry in self.__user_table.items():
            users[user_id] = UserEntry(user_id, user_entry)

        return users

    # self.__user_lookup helps with iteration support so we want to keep it up to date
    # this might be stupid idk
    def __update_lookup(self):
        self.__user_lookup = list(self.__users.keys())
        self.__num_users = len(self.__user_lookup)

    def to_json(self):
        return {user_id: user_entry.to_json() for user_id, user_entry in self}

    @classmethod
    def get_default(cls):
        return {}

    def user_exists(self, user_id: UID):
        return user_id in self.__users.keys()

    def get_or_add_user(self, user_id: UID) -> UserEntry:
        if self.user_exists(user_id):
            return self.get_user(user_id)
        else:
            return self.add_user(user_id)

    def get_user(self, user_id: UID) -> Optional[UserEntry]:
        user_id = str(user_id)

        if self.user_exists(user_id):
            return self.__users[user_id]

    def add_user(self, user_id: UID) -> Optional[UserEntry]:
        user_id = str(user_id)

        if self.user_exists(user_id):
            return

        entry = UserEntry(user_id)
        self.__users[user_id] = entry
        self.__update_lookup()

        return entry

    def remove_user(self, user_id: UID) -> bool:
        user_id = str(user_id)

        if not self.user_exists(user_id):
            return False

        del self.__users[user_id]
        self.__update_lookup()
        return True

    def get_watchlist_for_user(self, user_id: UID) -> Optional[list[str]]:
        user_id = str(user_id)

        if not self.user_exists(user_id):
            return

        user = self.__users[user_id]
        return user.get_watchlist()


class LookupTable:
    def __init__(self, lookup: dict[str, list[UID]]):
        self.__lookup = lookup

    def to_json(self):
        return self.__lookup

    @classmethod
    def get_default(cls):
        return {branch.name: [] for branch in SUPPORTED_PRODUCTS}

    def has_branch(self, branch: str):
        return branch in self.__lookup.keys()

    def is_subscribed(self, user_id: UID, branch: str):
        return user_id in self.__lookup[branch]

    def get_subscribers_for_branch(
        self, branch: str, convert_to_int: bool = False
    ) -> list[UID]:
        if not self.has_branch(branch):
            return

        if convert_to_int:
            subscribers = [int(uid) for uid in self.__lookup[branch]]
        else:
            subscribers = [str(uid) for uid in self.__lookup[branch]]
        return subscribers

    def add_subscriber_to_branch(self, user_id: UID, branch: str) -> bool:
        if not self.has_branch(branch) or self.is_subscribed(user_id, branch):
            return False

        self.__lookup[branch].append(str(user_id))
        return True

    def remove_subscriber_from_branch(self, user_id: UID, branch: str) -> bool:
        if not self.has_branch(branch) or not self.is_subscribed(user_id, branch):
            return False

        self.__lookup[branch].remove(str(user_id))
        return True


class UserConfigFile:
    CONFIG = CacheConfig()

    def __init__(self):
        self.CACHE_PATH = os.path.join(SELF_PATH, self.CONFIG.CACHE_FOLDER_NAME)
        self.CONFIG_PATH = os.path.join(self.CACHE_PATH, self.CONFIG.USER_CFG_FILE_NAME)

        if not os.path.exists(self.CONFIG_PATH):
            self.__init_cfg_file()

        self.__active = False
        self.stale = True

    def __enter__(self):
        with open(self.CONFIG_PATH, "r") as f:
            data = json.load(f)

        self.__populate(data)
        self.__active = True
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.__active = False
        self.stale = True
        if exc_type is not None:
            logger.error(
                f"Exception of type {exc_type.__name__} occurred within UserConfigFile context: {exc_value}"
            )
            return

        with open(self.CONFIG_PATH, "w") as f:
            json.dump(self, f, indent=4, cls=ConfigFileEncoder)

    def __init_cfg_file(self):
        if not os.path.exists(self.CACHE_PATH):
            os.makedirs(self.CACHE_PATH)

        default_lookup = LookupTable.get_default()
        default_users = UserTable.get_default()
        default = {"lookup": default_lookup, "users": default_users}
        with open(self.CONFIG_PATH, "w") as f:
            json.dump(default, f, indent=4)

    def __populate(self, config: dict):
        self.__config = config

        self.lookup = LookupTable(self.__config["lookup"])
        self.users = UserTable(self.__config["users"])

        self.stale = False

    def to_json(self):
        return {"lookup": self.lookup.to_json(), "users": self.users.to_json()}

    def get_watchlist(self, user_id: int) -> Optional[list[str]]:
        if not self.__active:
            return

        if self.stale:
            return

        user_id = str(user_id)
        user = self.users.get_user(user_id)
        if not user:
            return

        return user.get_watchlist()

    def subscribe(self, user_id: int, branch: str) -> tuple[bool, str]:
        if not self.__active:
            return False, "File context not active"

        if self.stale:
            return False, "Stale config file"

        if not self.lookup.has_branch(branch):
            return False, "Invalid branch"

        user_id = str(user_id)
        user = self.users.get_or_add_user(user_id)

        if user.is_on_watchlist(branch):
            return False, "Already subscribed to branch"

        success = user.add_to_watchlist(branch)
        lookup_success = self.lookup.add_subscriber_to_branch(user_id, branch)

        if success and lookup_success:
            message = "Success"
        elif success and not lookup_success:
            message = "Error occurred adding user to lookup table"
            success = False
        else:
            message = "Error adding branch to watchlist"

        return success, message

    def unsubscribe(self, user_id: int, branch: str) -> tuple[bool, str]:
        if not self.__active:
            return False, "File context not active"

        if self.stale:
            return False, "Stale config file"

        if not self.lookup.has_branch(branch):
            return False, "Invalid branch"

        user_id = str(user_id)
        user = self.users.get_user(user_id)

        if not user:
            return False, "Watchlist is empty"

        if not user.is_on_watchlist(branch):
            return False, "Branch is not on watchlist"

        success = user.remove_from_watchlist(branch)
        lookup_success = self.lookup.remove_subscriber_from_branch(user_id, branch)

        if success and lookup_success:
            message = "Success"
        elif success and not lookup_success:
            message = "Error occurred removing user from lookup table"
            success = False
        else:
            message = "Error removing branch from watchlist"

        return success, message


class ConfigFileEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, UserConfigFile):
            return obj.to_json()
        return super().default(self, obj)


class ConfigFileDecoder(json.JSONDecoder):
    def __init__(self, config_file: UserConfigFile, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config_file = config_file

    def decode(self, json_string):
        parsed_data = super().decode(json_string)
        if "users" in parsed_data and "lookup" in parsed_data and self.config_file:
            return self.config_file.__populate()
        return parsed_data


class UserCFG:
    CONFIG = CacheConfig()

    def is_valid_branch(self, branch: str):
        return SUPPORTED_PRODUCTS.has_key(branch)

    def lookup(self, branch: str) -> list[int]:
        data = self.read()

        return data["lookup"][branch]

    def make_unique(self, obj: list) -> list:
        return list(set(obj))

    def subscribe(self, user_id: int, branch: str) -> tuple[bool, str]:
        if not self.is_valid_branch(branch):
            return False, "Invalid branch"

        config = self.read()

        lookup = config["lookup"][branch]
        if user_id in lookup:
            return False, "Already subscribed"

        lookup.append(user_id)
        lookup = self.make_unique(lookup)

        user_id = str(user_id)
        user_config = config["users"]
        if not user_id in user_config.keys():
            user_config[user_id] = self.get_default_user_entry()

        watchlist = user_config[user_id]["watchlist"]
        watchlist.append(branch)
        watchlist = self.make_unique(watchlist)

        self.write(config)
        return True, "Success"

    def get_subscribed(self, user_id: int):
        config = self.read()

        user_id = str(user_id)
        users = config["users"]
        if user_id not in users.keys():
            users[user_id] = self.get_default_user_entry()

        watchlist = config["users"][user_id]["watchlist"]
        return watchlist

    def unsubscribe(self, user_id: int, branch: str) -> tuple[bool, str]:
        if not self.is_valid_branch(branch):
            return False, "Invalid branch"

        config = self.read()

        lookup = config["lookup"][branch]
        if user_id not in lookup:
            return False, "Not subscribed"

        lookup.remove(user_id)

        user_id = str(user_id)
        user_watchlist = config["users"][user_id]["watchlist"]
        user_watchlist.remove(branch)

        self.write(config)
        return True, "Success"
