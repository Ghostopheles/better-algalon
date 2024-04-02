import os
import json
import logging

from .config import CacheConfig
from .config import SUPPORTED_GAMES, SUPPORTED_PRODUCTS


logger = logging.getLogger("discord.cdn.user-cfg")


class UserCFG:
    SELF_PATH = os.path.dirname(os.path.realpath(__file__))
    CONFIG = CacheConfig()

    def __init__(self):
        self.cache_path = os.path.join(self.SELF_PATH, self.CONFIG.CACHE_FOLDER_NAME)
        self.user_cfg_path = os.path.join(
            self.cache_path, self.CONFIG.USER_CFG_FILE_NAME
        )

        if not os.path.exists(self.cache_path):
            os.mkdir(self.cache_path)

        if not os.path.exists(self.user_cfg_path):
            self.init_user_cfg()

    # structure here should be <userid> -> <watchlist>
    def init_user_cfg(self):
        default_lookup = {branch_name.name: [] for branch_name in SUPPORTED_PRODUCTS}

        defaults = {"users": {}, "lookup": default_lookup}

        self.write(defaults)

    def get_default_user_entry(self) -> dict:
        return {"watchlist": []}

    def write(self, data: dict):
        with open(self.user_cfg_path, "w") as f:
            json.dump(data, f, indent=4)

    def read(self):
        with open(self.user_cfg_path, "r") as f:
            data = json.load(f)

        return data

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
