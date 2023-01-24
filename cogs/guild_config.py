import os
import sys
import json
import logging

from .config import CacheConfig


logger = logging.getLogger("discord.cdn.guild-cfg")


class GuildCFG:
    SELF_PATH = os.path.dirname(os.path.realpath(__file__))
    PLATFORM = sys.platform
    CONFIG = CacheConfig()

    def __init__(self):
        self.cache_path = os.path.join(self.SELF_PATH, self.CONFIG.CACHE_FOLDER_NAME)
        self.guild_cfg_path = os.path.join(
            self.cache_path, self.CONFIG.GUILD_CFG_FILE_NAME
        )

        if not os.path.exists(self.cache_path):
            os.mkdir(self.cache_path)
            self.init_guild_cfg()

    # GUILD CFG DEFAULTS

    def get_default_guild_cfg(self):
        return {
            self.CONFIG.indices.CHANNEL: "None",
            self.CONFIG.indices.WATCHLIST: self.CONFIG.defaults.WATCHLIST,
        }

    def init_guild_cfg(self, guild_id: int | str = 0):
        """Populates the `guild_cfg.json` file with related guild configuration data."""
        with open(self.guild_cfg_path, "w") as file:
            file_json = json.load(file)
            file_json[guild_id] = self.get_default_guild_cfg()
            json.dump(file_json, file, indent=4)

    # GUILD CFG IO

    def does_guild_config_exist(self, guild_id: int | str):
        with open(self.guild_cfg_path, "r+") as file:
            file_json = json.load(file)
            return str(guild_id) in file_json

    def add_guild_config(self, guild_id: int | str):
        logger.info("Adding new guild to configuration file...")
        with open(self.guild_cfg_path, "r+") as file:
            file_json = json.load(file)
            file_json[guild_id] = self.get_default_guild_cfg()

            file.seek(0)
            json.dump(file_json, file, indent=4)
            file.truncate()

    def remove_guild_config(self, guild_id: int | str):
        logger.info("Adding new guild to configuration file...")
        with open(self.guild_cfg_path, "r+") as file:
            file_json = json.load(file)
            del file_json[str(guild_id)]

            file.seek(0)
            json.dump(file_json, file, indent=4)
            file.truncate()

    def get_guild_config(self, guild_id: int | str):
        logger.info(f"Fetching guild config for guild {guild_id}...")
        with open(self.guild_cfg_path, "r") as file:
            file_json = json.load(file)
            guild_id = str(guild_id)
            if guild_id not in file_json:
                self.add_guild_config(guild_id)

            return file_json[guild_id]

    def get_all_guild_configs(self):
        logger.info(f"Fetching all guild configurations...")
        with open(self.guild_cfg_path, "r") as file:
            file_json = json.load(file)
            return file_json

    def update_guild_config(self, guild_id: int | str, new_data, category):
        logger.info(f"Updating guild configuration for guild {guild_id}...")
        logger.debug(
            f"Guild config update payload - new data: {new_data}, category: {category}."
        )

        if not new_data:
            return  # WHY IS NEW_DATA NONE? HELLO?

        with open(self.guild_cfg_path, "r+") as file:
            file_json = json.load(file)
            file_json[str(guild_id)][category] = new_data

            file.seek(0)
            json.dump(file_json, file, indent=4)
            file.truncate()

    # WATCHLIST IO

    def add_to_guild_watchlist(self, guild_id: int | str, branch: str):
        logger.info(f'Adding "{branch}" to watchlist for guild {guild_id}...')

        guild_config = self.get_guild_config(guild_id)

        watchlist = guild_config[self.CONFIG.indices.WATCHLIST]

        if branch in watchlist:
            return self.CONFIG.strings.BRANCH_ALREADY_IN_WATCHLIST
        elif branch in self.CONFIG.PRODUCTS.keys():
            if isinstance(watchlist, str):
                watchlist = [watchlist, branch]
            else:
                watchlist.append(branch)

            self.update_guild_config(guild_id, watchlist, self.CONFIG.indices.WATCHLIST)
            return True
        else:
            return self.CONFIG.strings.BRANCH_NOT_VALID

    def remove_from_guild_watchlist(self, guild_id: int | str, branch: str):
        logger.info(f'Removing "{branch}" from watchlist for guild {guild_id}...')
        guild_config = self.get_guild_config(guild_id)

        watchlist = guild_config[self.CONFIG.indices.WATCHLIST]

        if branch not in watchlist:
            return self.CONFIG.strings.ARG_BRANCH_NOT_ON_WATCHLIST
        elif branch in self.CONFIG.PRODUCTS.keys():
            if isinstance(watchlist, str):
                return  # CANT REMOVE THE LAST BRANCH ON WATCHLIST
            else:
                watchlist.remove(branch)

            self.update_guild_config(guild_id, watchlist, self.CONFIG.indices.WATCHLIST)
            return True
        else:
            raise ValueError("Invalid branch ID.")

    def get_guild_watchlist(self, guild_id: int | str):
        logger.info(f"Grabbing guild watchlist for guild {guild_id}...")
        guild_config = self.get_guild_config(guild_id)

        return guild_config[self.CONFIG.indices.WATCHLIST]

    # CHANNEL IO

    def set_notification_channel(self, guild_id: int | str, new_channel: int):
        logger.info(
            f"Setting notification channel for guild {guild_id} to {new_channel}..."
        )
        guild_config = self.get_guild_config(guild_id)

        channel = guild_config[self.CONFIG.indices.CHANNEL]

        if channel == new_channel:
            return  # WHY ARE YOU SETTING THE CHANNEL TO THE ALREADY SET CHANNEL

        self.update_guild_config(guild_id, new_channel, self.CONFIG.indices.CHANNEL)
        return True

    def get_notification_channel(self, guild_id: int | str):
        logger.info(f"Grabbing notification channel setting for guild {guild_id}...")

        guild_config = self.get_guild_config(guild_id)

        return guild_config[self.CONFIG.indices.CHANNEL]
