import os
import sys
import json
import logging

from .config import CacheConfig
from .config import SUPPORTED_GAMES, SUPPORTED_PRODUCTS


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

        # remember to clear and update with new builds - contains an old key and a new value
        self.KEYS_TO_PATCH = ["d4_channel"]

    # GUILD CFG DEFAULTS

    def get_default_guild_cfg(self):
        return {
            self.CONFIG.settings.CHANNEL["name"]: self.CONFIG.settings.CHANNEL[
                "default"
            ],
            self.CONFIG.settings.D4_CHANNEL["name"]: self.CONFIG.settings.D4_CHANNEL[
                "default"
            ],
            self.CONFIG.settings.WATCHLIST["name"]: self.CONFIG.settings.WATCHLIST[
                "default"
            ],
            self.CONFIG.settings.REGION["name"]: self.CONFIG.settings.REGION["default"],
            self.CONFIG.settings.LOCALE["name"]: self.CONFIG.settings.LOCALE["default"],
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
        logger.debug(f"Fetching guild config for guild {guild_id}...")
        with open(self.guild_cfg_path, "r") as file:
            file_json = json.load(file)
            guild_id = str(guild_id)
            if guild_id not in file_json and guild_id.isdigit():
                self.add_guild_config(guild_id)

            return file_json[guild_id]

    def get_all_guild_configs(self):
        logger.debug(f"Fetching all guild configurations...")
        with open(self.guild_cfg_path, "r") as file:
            file_json = json.load(file)

            return file_json

    def get_guild_setting(self, guild_id: int | str, setting: str):
        logger.debug(f"Fetching {setting} for guild {guild_id}...")
        guild_config = self.get_guild_config(guild_id)
        _setting: dict = getattr(self.CONFIG.settings, setting.upper())

        if not _setting["name"] in guild_config:
            return self.reset_guild_setting_to_default(guild_id, _setting)
        elif _setting["name"] in self.KEYS_TO_PATCH:
            if _setting["name"] == "d4_channel" and guild_config["d4_channel"] == 0:
                return self.patch_guild_setting(guild_id, _setting)
        else:
            return guild_config[_setting["name"]]

    def validate_guild_configs(self):
        logger.debug(f"Validating guild configurations...")
        all_configs = self.get_all_guild_configs()

        for guild_id, config in all_configs.items():
            for key in self.CONFIG.settings.KEYS:
                _setting: dict = getattr(self.CONFIG.settings, key.upper())
                if key not in config:
                    self.reset_guild_setting_to_default(guild_id, _setting)
                elif key == "d4_channel" and config[key] == 0:
                    channel = config["channel"]
                    self.update_guild_config(guild_id, channel, "d4_channel")

    def reset_guild_setting_to_default(self, guild_id: int | str, setting: dict):
        logger.debug(f"Resetting {setting} to default for guild {guild_id}.")
        logger.debug(f"Default value: {setting['default']}, name: {setting['name']}")
        self.update_guild_config(guild_id, setting["default"], setting["name"])
        return self.get_guild_setting(guild_id, setting["name"])

    def patch_guild_setting(self, guild_id: int | str, setting: dict):
        logger.debug(f"Patching {setting} for guild {guild_id}.")

        g_config = self.get_guild_config(guild_id)
        old_channel_id = g_config["channel"]

        self.update_guild_config(guild_id, old_channel_id, "d4_channel")

        return True

    def update_guild_config(self, guild_id: int | str, new_data, setting):
        logger.debug(f"Updating guild configuration for guild {guild_id}...")
        logger.debug(
            f"Guild config update payload - new data: {new_data}, setting: {setting}."
        )

        with open(self.guild_cfg_path, "r+") as file:
            file_json = json.load(file)
            file_json[str(guild_id)][setting] = new_data

            file.seek(0)
            json.dump(file_json, file, indent=4)
            file.truncate()

        return True

    # WATCHLIST IO

    def add_to_guild_watchlist(self, guild_id: int | str, branch: SUPPORTED_PRODUCTS):
        logger.info(f'Adding "{branch}" to watchlist for guild {guild_id}...')

        guild_config = self.get_guild_config(guild_id)

        watchlist = guild_config[self.CONFIG.settings.WATCHLIST["name"]]

        if branch in watchlist:
            return False, self.CONFIG.errors.BRANCH_ALREADY_IN_WATCHLIST
        elif self.CONFIG.PRODUCTS.has_key(branch):
            if isinstance(watchlist, str):
                watchlist = [watchlist, branch]
            else:
                watchlist.append(branch)

            self.update_guild_config(
                guild_id, [*set(watchlist)], self.CONFIG.settings.WATCHLIST["name"]
            )
            return True, self.CONFIG.errors.OK
        else:
            return False, self.CONFIG.errors.ARG_BRANCH_NOT_VALID

    def remove_from_guild_watchlist(
        self, guild_id: int | str, branch: SUPPORTED_PRODUCTS
    ):
        logger.info(f'Removing "{branch}" from watchlist for guild {guild_id}...')
        guild_config = self.get_guild_config(guild_id)

        watchlist = guild_config[self.CONFIG.settings.WATCHLIST["name"]]

        if not self.CONFIG.PRODUCTS.has_key(branch):
            return False, self.CONFIG.errors.ARG_BRANCH_NOT_VALID
        elif branch not in watchlist:
            return False, self.CONFIG.errors.ARG_BRANCH_NOT_ON_WATCHLIST
        elif self.CONFIG.PRODUCTS[branch]:
            if isinstance(watchlist, str):
                return False, self.CONFIG.errors.WATCHLIST_CANNOT_BE_EMPTY
            else:
                watchlist.remove(branch)

            self.update_guild_config(
                guild_id, [*set(watchlist)], self.CONFIG.settings.WATCHLIST["name"]
            )
            return True, self.CONFIG.errors.OK
        else:
            return (
                False,
                self.CONFIG.errors.ARG_BRANCH_NOT_VALID,
            )  # this should never happen?

    def get_guild_watchlist(self, guild_id: int | str):
        logger.info(f"Grabbing guild watchlist for guild {guild_id}...")
        guild_config = self.get_guild_config(guild_id)

        return guild_config[self.CONFIG.settings.WATCHLIST["name"]]

    # CHANNEL IO

    def set_notification_channel(
        self, guild_id: int | str, new_channel: int, game: SUPPORTED_GAMES | None = None
    ) -> bool:
        logger.info(
            f"Setting {game or 'wow'} notification channel for guild {guild_id} to {new_channel}..."
        )

        # TODO: wtf
        if game == SUPPORTED_GAMES.Warcraft or not game:
            self.update_guild_config(
                guild_id, new_channel, self.CONFIG.settings.CHANNEL["name"]
            )
        elif game == SUPPORTED_GAMES.Diablo4:
            self.update_guild_config(
                guild_id, new_channel, self.CONFIG.settings.D4_CHANNEL["name"]
            )
        elif game == SUPPORTED_GAMES.Gryphon:
            self.update_guild_config(
                guild_id, new_channel, self.CONFIG.settings.GRYPHON_CHANNEL["name"]
            )
        else:
            return False

        return True

    def get_notification_channel(
        self, guild_id: int | str, game: SUPPORTED_GAMES | None = None
    ):
        logger.info(f"Grabbing notification channel setting for guild {guild_id}...")

        # TODO: this is dumb
        if game is None or game == SUPPORTED_GAMES.Warcraft:
            key = self.CONFIG.settings.CHANNEL["name"]
        elif game == SUPPORTED_GAMES.Diablo4:
            key = self.CONFIG.settings.D4_CHANNEL["name"]
        elif game == SUPPORTED_GAMES.Gryphon:
            key = self.CONFIG.settings.GRYPHON_CHANNEL["name"]

        guild_config = self.get_guild_config(guild_id)

        return guild_config[key]

    # REGION / LOCALE IO

    def get_region_supported_locales(self, region: str):
        for reg in self.CONFIG.SUPPORTED_REGIONS:
            if reg.name == region:
                return reg.locales

        return  # REGION NOT FOUND?

    def is_locale_supported_by_region(self, locale: str, region: str):
        locales = self.get_region_supported_locales(region)

        if not locales:
            return
        else:
            for value in locales:
                if value.value == locale:
                    return True

            return False

    def get_region_default_locale(self, region: str):
        for reg in self.CONFIG.SUPPORTED_REGIONS:
            if reg.name == region:
                return reg.locales[0].value

    def set_region(self, guild_id: int | str, new_region: str):
        logger.info(f"Setting region for guild {guild_id}...")

        current_region = self.get_guild_setting(guild_id, "region")
        current_locale = self.get_guild_setting(guild_id, "locale")

        if new_region == current_region:
            logger.error(f"New region is the same as current region.")

            return False, self.CONFIG.errors.REGION_SAME_AS_CURRENT

        elif not new_region in self.CONFIG.SUPPORTED_REGIONS_STRING:
            logger.error(f"Region '{new_region}' not supported, returning.")

            return False, self.CONFIG.errors.REGION_NOT_SUPPORTED

        elif not current_locale in self.get_region_supported_locales(new_region):
            logger.error(
                f"Locale '{current_locale}' not supported in {new_region}, setting locale to region default."
            )
            self.update_guild_config(
                guild_id, self.get_region_default_locale(new_region), "locale"
            )
            self.update_guild_config(guild_id, new_region, "region")

            return True, self.CONFIG.strings.REGION_LOCALE_CHANGED

        else:
            self.update_guild_config(guild_id, new_region, "region")

            return True, self.CONFIG.strings.REGION_UPDATED

    def get_region(self, guild_id: int | str):
        logger.info(f"Fetching region for guild {guild_id}...")

        return self.get_guild_setting(guild_id, "region")

    def set_locale(self, guild_id: int | str, new_locale: str):
        logger.info(f"Setting locale for guild {guild_id}...")

        current_region = self.get_guild_setting(guild_id, "region")
        current_locale = self.get_guild_setting(guild_id, "locale")

        if new_locale == current_locale:
            logger.error(f"New locale is the same as current locale.")
            return False, self.CONFIG.errors.LOCALE_SAME_AS_CURRENT

        elif not self.is_locale_supported_by_region(new_locale, current_region):
            logger.error(f"New locale not supported in current region.")
            return False, self.CONFIG.errors.LOCALE_NOT_SUPPORTED

        else:
            return (
                self.update_guild_config(guild_id, new_locale, "locale"),
                self.CONFIG.strings.LOCALE_UPDATED,
            )

    def get_locale(self, guild_id: int | str):
        logger.info(f"Fetching locale for guild {guild_id}...")

        return self.get_guild_setting(guild_id, "locale")
