import os
import json
import logging

from enum import StrEnum
from typing import TypeVar, Optional

from .config import CacheConfig
from .config import SUPPORTED_PRODUCTS

SELF_PATH = os.path.dirname(os.path.realpath(__file__))

logger = logging.getLogger("discord.cdn.user-cfg")

# userID type alias, have to use the old way because old python :(
UID = TypeVar("UID", str, int)


class Monitorable(StrEnum):
    BuildConfig = "build_config"
    CDNConfig = "cdn_config"
    ProductConfig = "product_config"
    KeyRing = "keyring"


"""
It's a bit arcane but this is the structure I see for the internal monitoring list

monitoring = {
    "keyring": {
        "us": [
            "wow_beta"
        ]
    }
}

"""


class MonitorList:
    def __init__(self, monitoring: Optional[dict[str, list[str]]] = None):
        self.__monitoring = monitoring if monitoring else self.__get_default_list()

    def __get_default_list(self) -> dict:
        return dict()

    def __remove_duplicates(self):
        for field, branches in self.__monitoring.items():
            self.__monitoring[field] = [*set(branches)]

    def to_json(self) -> dict:
        return self.__monitoring

    def is_monitoring_field(
        self,
        branch: str,
        field: Monitorable,
    ) -> bool:
        if field not in self.__monitoring:
            return False

        return branch in self.__monitoring[field]

    def monitor_field(
        self,
        branch: str,
        field: Monitorable,
    ):
        field = field.value
        if field not in self.__monitoring:
            self.__monitoring[field] = list()

        self.__monitoring[field].append(branch)
        self.__remove_duplicates()
        return True

    def unmonitor_field(
        self,
        branch: str,
        field: Monitorable,
    ):
        field = field.value
        if field not in self.__monitoring:
            return False

        if branch not in self.__monitoring[field]:
            return False

        self.__monitoring[field].remove(branch)
        if len(self.__monitoring[field]) == 0:
            del self.__monitoring[field]

        return True


class UserEntry:
    def __init__(self, user_id: UID, user_entry: Optional[dict] = None):
        self.__entry = user_entry if user_entry else self.__get_default_entry()
        self.user_id = str(user_id)
        self.watchlist: list[str] = self.__entry["watchlist"]
        self.monitor: MonitorList = MonitorList(
            self.__entry["monitor"] if "monitor" in self.__entry else None
        )

    def __get_default_entry(self) -> dict:
        return {"watchlist": [], "monitor": MonitorList()}

    def to_json(self) -> dict:
        return {"watchlist": self.watchlist, "monitor": self.monitor.to_json()}

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

    def get_monitor_list(self) -> MonitorList:
        return self.monitor

    def is_monitoring(self, branch: str, field: Monitorable):
        return self.monitor.is_monitoring_field(branch, field)

    def add_to_monitor(self, branch: str, field: Monitorable) -> bool:
        return self.monitor.monitor_field(branch, field)

    def remove_from_monitor(self, branch: str, field: Monitorable) -> bool:
        return self.monitor.unmonitor_field(branch, field)


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
                f"Exception of type {exc_type.__name__} occurred within UserConfigFile context: {exc_value}",
                exc_info=True,
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

    def get_monitor_list(self, user_id: int) -> Optional[MonitorList]:
        if not self.__active:
            return

        if self.stale:
            return

        user_id = str(user_id)
        user = self.users.get_user(user_id)
        if not user:
            return

        return user.get_monitor_list()

    def monitor(
        self, user_id: int, branch: str, field: Monitorable
    ) -> tuple[bool, str]:
        if not self.__active:
            return False, "File context not active"

        if self.stale:
            return False, "Stale config file"

        if not self.lookup.has_branch(branch):
            return False, "Invalid branch"

        user_id = str(user_id)
        user = self.users.get_or_add_user(user_id)

        monitor_list = user.get_monitor_list()
        if monitor_list.is_monitoring_field(branch, field):
            return (
                False,
                "You are already monitoring this field for this branch",
            )

        success = user.add_to_monitor(branch, field)
        if success:
            message = "Success"
        else:
            message = "Error occurred adding branch and field to monitor list"
        return success, message

    def unmonitor(
        self, user_id: int, branch: str, field: Monitorable
    ) -> tuple[bool, str]:
        if not self.__active:
            return False, "File context not active"

        if self.stale:
            return False, "Stale config file"

        if not self.lookup.has_branch(branch):
            return False, "Invalid branch"

        user_id = str(user_id)
        user = self.users.get_or_add_user(user_id)

        monitor_list = user.get_monitor_list()
        if not monitor_list.is_monitoring_field(branch, field):
            return (
                False,
                "You are not monitoring this field for this branch",
            )

        success = user.remove_from_monitor(branch, field)
        if success:
            message = "Success"
        else:
            message = "Error occurred removing branch and fieldfrom monitor list"
        return success, message

    def is_monitoring(self, user_id: int, branch: str, field: Monitorable) -> bool:
        if not self.__active:
            return False, "File context not active"

        if self.stale:
            return False, "Stale config file"

        if not self.lookup.has_branch(branch):
            return False, "Invalid branch"

        user_id = str(user_id)
        user = self.users.get_or_add_user(user_id)

        monitor_list = user.get_monitor_list()
        return monitor_list.is_monitoring_field(branch, field)

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
