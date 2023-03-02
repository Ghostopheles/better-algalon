import os
import sys
import time
import json
import httpx
import logging

from .config import CacheConfig, FETCH_INTERVAL

logger = logging.getLogger("discord.cdn.cache")


class CDNCache:
    SELF_PATH = os.path.dirname(os.path.realpath(__file__))
    PLATFORM = sys.platform
    CONFIG = CacheConfig()

    def __init__(self):
        self.cache_path = os.path.join(self.SELF_PATH, self.CONFIG.CACHE_FOLDER_NAME)
        self.cdn_path = os.path.join(self.cache_path, self.CONFIG.CACHE_FILE_NAME)

        if not os.path.exists(self.cache_path):
            os.mkdir(self.cache_path)
            self.init_cdn()

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

            for area in self.CONFIG.AREAS_TO_CHECK_FOR_UPDATES:
                if branch in file_json[self.CONFIG.indices.BUILDINFO]:
                    if (
                        file_json[self.CONFIG.indices.BUILDINFO][branch][area]
                        != newBuild[area]
                    ):
                        return True
                    else:
                        return False
                else:
                    file_json[self.CONFIG.indices.BUILDINFO][branch][area] = newBuild[
                        area
                    ]
                    return True
            return False

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
        logger.debug(self.CONFIG.strings.LOG_FETCH_DATA)
        async with httpx.AsyncClient() as client:
            new_data = []
            for branch in self.CONFIG.PRODUCTS:
                try:
                    logger.debug(f"Grabbing data for branch: {branch}")
                    url = self.CONFIG.CDN_URL + branch + "/versions"

                    res = await client.get(url, timeout=20)
                    logger.debug(self.CONFIG.strings.LOG_PARSE_DATA)
                    data = self.parse_response(branch, res.text)

                    if data:
                        logger.debug(f"Comparing build data for {branch}")
                        is_new = self.compare_builds(branch, data)

                        if is_new:
                            output_data = data.copy()

                            old_data = self.load_build_data(branch)

                            if old_data:
                                output_data["old"] = old_data

                            output_data["branch"] = branch
                            new_data.append(output_data)

                        logger.debug(f"Saving build data for {branch}")
                        self.save_build_data(branch, data)
                    else:
                        continue
                except httpx.ConnectError as exc:
                    logger.error(
                        f"Connection error during CDN check for {branch} using url {url or None}"  # type: ignore
                    )
                    return exc
                except Exception as exc:
                    logger.error(f"Timeout error during CDN check for {branch}")
                    return exc

            return new_data

    def parse_response(self, branch: str, response: str):
        """Parses the API response and attempts to return the new data."""
        try:
            data = response.split("\n")
            if len(data) < 3:
                return False
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
            }

            return output
        except Exception as exc:
            logger.error(
                f"Encountered an error parsing API response for branch: {branch}."
            )
            logger.error(exc)

            return False
