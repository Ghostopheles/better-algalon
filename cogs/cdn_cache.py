import os
import sys
import time
import json
import shutil
import logging
import asyncio

from typing import Any

from cogs.user_config import Monitorable
from .api.blizzard_tact import BlizzardTACTExplorer
from .config import LiveConfig, CacheConfig
from .ribbit_async import RibbitClient

logger = logging.getLogger("discord.cdn.cache")


class CDNCache:
    SELF_PATH = os.path.dirname(os.path.realpath(__file__))
    PLATFORM = sys.platform
    CONFIG = CacheConfig()
    LIVE_CONFIG = LiveConfig
    TACT = BlizzardTACTExplorer()

    def __init__(self):
        self.cache_path = os.path.join(self.SELF_PATH, self.CONFIG.CACHE_FOLDER_NAME)
        self.cdn_path = os.path.join(self.cache_path, self.CONFIG.CACHE_FILE_NAME)
        self.seqn_cache = os.path.join(self.cache_path, "seqn_cache.json")

        self.fetch_interval = self.LIVE_CONFIG.get_cfg_value("meta", "fetch_interval")

        if not os.path.exists(self.cache_path):
            os.mkdir(self.cache_path)
            self.init_cdn()

        if not os.path.exists(self.seqn_cache):
            with open(self.seqn_cache, "w") as file:
                json.dump({}, file, indent=4)

        self.patch_cdn_keys()

        self.monitor = None

    def patch_cdn_keys(self):
        with open(self.cdn_path, "r+") as file:
            logger.debug("Patching CDN file...")
            file_json = json.load(file)
            build_data = file_json["buildInfo"]
            try:
                for branch in build_data:
                    for key, value in self.CONFIG.REQUIRED_KEYS_DEFAULTS.items():
                        if key not in build_data[branch]:
                            logger.debug(
                                f"Adding {key} to {branch} with value {value}..."
                            )
                            build_data[branch][key] = value

            except KeyError:
                logger.error("KeyError while patching CDN file", exc_info=True)

            file_json["buildInfo"] = build_data

            file.seek(0)
            json.dump(file_json, file, indent=4)
            file.truncate()

    def init_cdn(self):
        """Populates the `cdn.json` file with default values if it does not exist."""
        with open(self.cdn_path, "w") as file:
            template = {
                "buildInfo": {},
                self.CONFIG.indices.LAST_UPDATED_BY: self.PLATFORM,
                self.CONFIG.indices.LAST_UPDATED_AT: time.time(),
            }
            json.dump(template, file, indent=4)

    def register_monitor_cog(self, cog):
        self.monitor = cog

    def notify_watched_field_updated(self, branch: str, field: str, new_data: Any):
        if not self.monitor:
            return

        self.monitor.on_field_update(branch, field, new_data)

    def is_seen_seqn(self, branch, seqn):
        """
        Checks if the sequence number has been seen before.

        Returns `True` if it has, else `False`.
        """
        with open(self.seqn_cache, "r") as file:
            seqn_cache = json.load(file)
            if branch in seqn_cache:
                return seqn in seqn_cache[branch]

    def mark_seqn_seen(self, branch, seqn):
        """
        Marks a sequence number as seen.

        This will prevent the same sequence number from being processed again.
        """
        with open(self.seqn_cache, "r+") as file:
            seqn_cache = json.load(file)
            if branch not in seqn_cache:
                seqn_cache[branch] = []
            if seqn not in seqn_cache[branch]:
                seqn_cache[branch].append(seqn)
                file.seek(0)
                json.dump(seqn_cache, file, indent=4)
                file.truncate()

    def compare_builds(self, branch: str, newBuild: dict) -> bool:
        """
        Compares two builds.

        Returns `True` if the build is new, else `False`.
        """
        if self.is_seen_seqn(branch, newBuild["seqn"]):
            logger.info(f"Skipping {branch} with seqn {newBuild['seqn']}")
            return False

        with open(self.cdn_path, "r") as file:
            file_json = json.load(file)

            if file_json[self.CONFIG.indices.LAST_UPDATED_BY] != self.PLATFORM and (
                time.time() - file_json[self.CONFIG.indices.LAST_UPDATED_AT]
            ) < (self.fetch_interval * 60):
                logger.info(
                    f"Skipping build comparison for '{branch}', data is outdated"
                )
                return False

            # ignore builds with lower seqn numbers because it's probably just a caching issue
            new_seqn, old_seqn = int(newBuild["seqn"]), int(
                file_json["buildInfo"][branch]["seqn"]
            )
            if (new_seqn > 0) and new_seqn < old_seqn:
                logger.warning(f"Lower sequence number found for {branch}")
                return False

            build_info = file_json["buildInfo"]
            for area in newBuild:
                if area not in Monitorable._value2member_map_:
                    continue

                if branch not in build_info:
                    break

                if area not in build_info[branch]:
                    build_info[branch][area] = None

                if build_info[branch][area] != newBuild[area]:
                    self.notify_watched_field_updated(branch, area, newBuild[area])

            for area in self.CONFIG.AREAS_TO_CHECK_FOR_UPDATES:
                if branch in build_info:
                    if build_info[branch][area] != newBuild[area]:
                        logger.debug(f"Updated info found for {branch} @ {area}")
                        self.mark_seqn_seen(branch, newBuild["seqn"])
                        return True
                else:
                    build_info[branch][area] = newBuild[area]
                    self.mark_seqn_seen(branch, newBuild["seqn"])
                    return True
            return False

    def set_default_entry(self, name: str):
        self.save_build_data(name, self.CONFIG.REQUIRED_KEYS_DEFAULTS)

    def get_all_config_entries(self):
        with open(self.cdn_path, "r") as file:
            file_json = json.load(file)
            return file_json["buildInfo"].keys()

    def create_cache_backup(self):
        logger.debug("Backing up CDN cache file...")
        backup_path = os.path.join(self.cache_path, "backups")
        if not os.path.exists(backup_path):
            os.mkdir(backup_path)

        backup_files = os.listdir(backup_path)

        if len(backup_files) >= self.CONFIG.FILE_BACKUP_COUNT:
            oldest_file = min(
                backup_files,
                key=lambda x: os.path.getmtime(os.path.join(backup_path, x)),
            )
            os.remove(os.path.join(backup_path, oldest_file))

        backup_filename = os.path.join(
            backup_path, f"cdn_{len(backup_files)+1}.json.bak"
        )
        shutil.copyfile(self.cdn_path, backup_filename)
        logger.debug("Backup complete!")

    def save_build_data(self, branch: str, data: dict):
        """Saves new build data to the `cdn.json` file."""
        with open(self.cdn_path, "r+") as file:
            file_json = json.load(file)
            file_json["buildInfo"][branch] = data

            file.seek(0)
            json.dump(file_json, file, indent=4)
            file.truncate()

    def load_build_data(self, branch: str):
        """Loads existing build data from the `cdn.json` file."""
        with open(self.cdn_path, "r") as file:
            file_json = json.load(file)
            if branch in file_json["buildInfo"]:
                return file_json["buildInfo"][branch]
            else:
                file_json["buildInfo"][branch] = {
                    "region": self.CONFIG.defaults.REGION,
                    "build": self.CONFIG.defaults.BUILD,
                    "build_text": self.CONFIG.defaults.BUILDTEXT,
                }
                return False

    async def fetch_cdn(self):
        """This is sort of a disaster."""
        logger.info("Fetching CDN versions...")
        self.create_cache_backup()
        coros = [
            self.fetch_branch_ribbit(branch.name) for branch in self.CONFIG.PRODUCTS
        ]
        new_data = await asyncio.gather(*coros)
        new_data = [i for i in new_data if i is not None]

        return new_data

    async def fetch_branch_ribbit(self, branch: str):
        logger.info(f"Fetching versions for {branch}...")
        _data, seqn = await RibbitClient().fetch_versions_for_product(product=branch)

        if not _data:
            logger.warning(f"No response for {branch}")
            return

        if branch == "catalogs":
            highest_region = None
            highest_build = 0
            for region, data in _data.items():
                build_text = int(data.build_text)
                if build_text > highest_build:
                    highest_build = build_text
                    highest_region = region

            region = highest_region
        else:
            region = "us"

        _data = _data[region]
        data = _data.__dict__()

        logger.debug(f"Comparing build data for {branch}")
        is_new = self.compare_builds(branch, data)

        if is_new:
            output_data = data.copy()

            old_data = self.load_build_data(branch)

            if old_data:
                output_data["old"] = old_data

            output_data["branch"] = branch
            logger.debug(f"Saving new build data for {branch}. New data: {output_data}")
            self.save_build_data(branch, data)

            return output_data
        else:
            logger.debug(f"No new data found for {branch}")
            self.save_build_data(branch, data)
            return
