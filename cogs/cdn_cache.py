import os
import sys
import time
import json
import shutil
import logging
import asyncio

from .api.blizzard_tact import BlizzardTACTExplorer
from .config import LiveConfig, CacheConfig
from .ribbit_async import RibbitClient

logger = logging.getLogger("discord.cdn.cache")


class CDNCache:
    SELF_PATH = os.path.dirname(os.path.realpath(__file__))
    PLATFORM = sys.platform
    CONFIG = CacheConfig()
    LIVE_CONFIG = LiveConfig()
    TACT = BlizzardTACTExplorer()

    def __init__(self):
        self.cache_path = os.path.join(self.SELF_PATH, self.CONFIG.CACHE_FOLDER_NAME)
        self.cdn_path = os.path.join(self.cache_path, self.CONFIG.CACHE_FILE_NAME)

        self.fetch_interval = self.LIVE_CONFIG.get_fetch_interval()

        if not os.path.exists(self.cache_path):
            os.mkdir(self.cache_path)
            self.init_cdn()

        self.patch_cdn_keys()

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

    def compare_builds(self, branch: str, newBuild: dict) -> bool:
        """
        Compares two builds.

        Returns `True` if the build is new, else `False`.
        """
        with open(self.cdn_path, "r") as file:
            file_json = json.load(file)

            if file_json[self.CONFIG.indices.LAST_UPDATED_BY] != self.PLATFORM and (
                time.time() - file_json[self.CONFIG.indices.LAST_UPDATED_AT]
            ) < (self.fetch_interval * 60):
                logger.info(
                    f"Skipping build comparison for '{branch}', data is outdated"
                )
                return False

            if not "encrypted" in file_json:  # just a safeguard
                file_json["encrypted"] = None

            if (
                file_json["buildInfo"][branch]["encrypted"] == True
                and newBuild["encrypted"] == None
            ):
                newBuild["encrypted"] = True

            # ignore builds with lower seqn numbers because it's probably just a caching issue
            new_seqn, old_seqn = int(newBuild["seqn"]), int(
                file_json["buildInfo"][branch]["seqn"]
            )
            if (new_seqn > 0) and new_seqn < old_seqn:
                logger.warning(f"Lower sequence number found for {branch}")
                return False

            for area in self.CONFIG.AREAS_TO_CHECK_FOR_UPDATES:
                if branch in file_json["buildInfo"]:
                    if file_json["buildInfo"][branch][area] != newBuild[area]:
                        logger.debug(f"Updated info found for {branch} @ {area}")
                        return True
                else:
                    file_json["buildInfo"][branch][area] = newBuild[area]
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

        region = "PUB-29" if branch == "catalogs" else "us"

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
            return
