import os
import sys
import time
import json
import httpx
import shutil
import logging
import asyncio

from .api.blizzard_tact import BlizzardTACTExplorer
from .config import CacheConfig, FETCH_INTERVAL
from .ribbit_async import RibbitClient

logger = logging.getLogger("discord.cdn.cache")


class CDNCache:
    SELF_PATH = os.path.dirname(os.path.realpath(__file__))
    PLATFORM = sys.platform
    CONFIG = CacheConfig()
    TACT = BlizzardTACTExplorer()

    def __init__(self):
        self.cache_path = os.path.join(self.SELF_PATH, self.CONFIG.CACHE_FOLDER_NAME)
        self.cdn_path = os.path.join(self.cache_path, self.CONFIG.CACHE_FILE_NAME)

        if not os.path.exists(self.cache_path):
            os.mkdir(self.cache_path)
            self.init_cdn()

        self.patch_cdn_keys()

    def patch_cdn_keys(self):
        with open(self.cdn_path, "r+") as file:
            logger.info("Patching CDN file...")
            file_json = json.load(file)
            build_data = file_json[self.CONFIG.indices.BUILDINFO]
            try:
                for branch in build_data:
                    for key, value in self.CONFIG.REQUIRED_KEYS_DEFAULTS.items():
                        if key not in build_data[branch]:
                            logger.info(
                                f"Adding {key} to {branch} with value {value}..."
                            )
                            build_data[branch][key] = value

            except KeyError as exc:
                logger.error("KeyError while patching CDN file", exc_info=exc)

            file_json[self.CONFIG.indices.BUILDINFO] = build_data

            file.seek(0)
            json.dump(file_json, file, indent=4)
            file.truncate()

    def init_cdn(self):
        """Populates the `cdn.json` file with default values if it does not exist."""
        with open(self.cdn_path, "w") as file:
            template = {
                self.CONFIG.indices.BUILDINFO: {},
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
            ) < (FETCH_INTERVAL * 60):
                logger.info("Skipping build comparison, data is outdated")
                return False

            if not "encrypted" in file_json:  # just a safeguard
                file_json["encrypted"] = None

            if (
                file_json[self.CONFIG.indices.BUILDINFO][branch]["encrypted"] == True
                and newBuild["encrypted"] == None
            ):
                newBuild["encrypted"] = True

            # ignore builds with lower seqn numbers because it's probably just a caching issue
            new_seqn, old_seqn = int(newBuild["seqn"]), int(
                file_json[self.CONFIG.indices.BUILDINFO][branch]["seqn"]
            )
            if (new_seqn > 0) and new_seqn < old_seqn:
                logger.warning(f"Lower sequence number found for {branch}")
                return False

            for area in self.CONFIG.AREAS_TO_CHECK_FOR_UPDATES:
                if branch in file_json[self.CONFIG.indices.BUILDINFO]:
                    if (
                        file_json[self.CONFIG.indices.BUILDINFO][branch][area]
                        != newBuild[area]
                    ):
                        logger.debug(f"Updated info found for {branch} @ {area}")
                        return True
                    else:
                        return False
                else:
                    file_json[self.CONFIG.indices.BUILDINFO][branch][area] = newBuild[
                        area
                    ]
                    return True
            return False

    def set_default_entry(self, name: str):
        self.save_build_data(name, self.CONFIG.REQUIRED_KEYS_DEFAULTS)

    def get_all_config_entries(self):
        with open(self.cdn_path, "r") as file:
            file_json = json.load(file)
            return file_json[self.CONFIG.indices.BUILDINFO].keys()

    def create_cache_backup(self):
        logger.info("Backing up CDN cache file...")
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
        logger.info("Backup complete!")

    def save_build_data(self, branch: str, data: dict):
        """Saves new build data to the `cdn.json` file."""
        with open(self.cdn_path, "r+") as file:
            file_json = json.load(file)
            file_json[self.CONFIG.indices.BUILDINFO][branch] = data

            file.seek(0)
            json.dump(file_json, file, indent=4)
            file.truncate()

    def load_build_data(self, branch: str):
        """Loads existing build data from the `cdn.json` file."""
        with open(self.cdn_path, "r") as file:
            file_json = json.load(file)
            if branch in file_json[self.CONFIG.indices.BUILDINFO]:
                return file_json[self.CONFIG.indices.BUILDINFO][branch]
            else:
                file_json[self.CONFIG.indices.BUILDINFO][branch] = {
                    self.CONFIG.settings.REGION["name"]: self.CONFIG.defaults.REGION,
                    self.CONFIG.indices.BUILD: self.CONFIG.defaults.BUILD,
                    self.CONFIG.indices.BUILDTEXT: self.CONFIG.defaults.BUILDTEXT,
                }
                return False

    async def fetch_cdn(self):
        """This is a disaster."""
        logger.info(self.CONFIG.strings.LOG_FETCH_DATA)
        self.create_cache_backup()
        coros = [
            self.fetch_branch_ribbit(branch.name) for branch in self.CONFIG.PRODUCTS
        ]
        new_data = await asyncio.gather(*coros)
        new_data = [i for i in new_data if i is not None]

        return new_data

    async def fetch_branch(self, branch: str, client: httpx.AsyncClient):
        try:
            logger.info(f"Grabbing version for {branch}")
            url = self.CONFIG.CDN_URL + branch + "/versions"

            res = await client.get(url, timeout=20)
            logger.info(f"Parsing CDN response for {branch}...")
            data = await self.parse_response(branch, res.text)

            if data and res.status_code == 200:
                logger.debug(f"Version check payload: {data}")
                logger.info(f"Comparing build data for {branch}")
                is_new = self.compare_builds(branch, data)

                if is_new:
                    output_data = data.copy()

                    old_data = self.load_build_data(branch)

                    if old_data:
                        output_data["old"] = old_data

                    output_data["branch"] = branch
                    logger.debug(f"Updated build payload: {output_data}")

                    logger.info(f"Saving new build data for {branch}")
                    self.save_build_data(branch, data)

                    return output_data
            else:
                logger.warning(
                    f"Invalid response {res.status_code} for branch {branch}"
                )
        except httpx.ConnectError as exc:
            logger.error(
                f"Connection error during CDN check for {branch} using url {url or None}"  # type: ignore
            )
        except Exception as exc:
            logger.error(f"Error during CDN check for {branch}", exc_info=exc)

    async def fetch_branch_ribbit(self, branch: str):
        logger.info(f"Grabbing versions for {branch}")
        _data, seqn = await RibbitClient().fetch_versions_for_product(product=branch)

        if not _data:
            logger.error(f"No response for {branch}.")
            return

        _data = _data["us"]
        data = _data.__dict__()

        logger.info(f"Comparing build data for {branch}")
        is_new = self.compare_builds(branch, data)

        if is_new:
            output_data = data.copy()

            old_data = self.load_build_data(branch)

            if old_data:
                output_data["old"] = old_data

            output_data["branch"] = branch
            logger.debug(f"Updated build payload: {output_data}")

            logger.info(f"Saving new build data for {branch}")
            self.save_build_data(branch, data)

            return output_data
        else:
            logger.debug(f"No new data found for {branch}")
            return

    async def parse_response(self, branch: str, response: str):
        """Parses the API response and attempts to return the new data."""
        try:
            data = response.split("\n")
            if len(data) < 3:
                return False
            seqn = data[1].replace("## seqn = ", "")
            data = data[2].split("|")
            region = data[0]
            build_config = data[1]
            cdn_config = data[2]
            build_number = data[4]
            build_text = data[5].replace(build_number, "")[:-1]
            product_config = data[6]

            output = {
                self.CONFIG.settings.REGION["name"]: region,
                "build_config": build_config,
                "cdn_config": cdn_config,
                "build": build_number,
                "build_text": build_text,
                "product_config": product_config,
                "encrypted": await self.TACT.is_encrypted(branch, product_config),
                "seqn": int(seqn),
            }

            return output
        except KeyError or IndexError as exc:
            logger.warning(
                f"Encountered an error parsing API response for branch: {branch}.",
                exc_info=exc if isinstance(exc, IndexError) else None,
            )

            return False
