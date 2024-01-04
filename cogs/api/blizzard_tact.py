import httpx
import logging

from ..config import CacheConfig

logger = logging.getLogger("discord.api.blizzard.tact")


class BlizzardTACTExplorer:
    def __init__(self):
        self.logger = logger
        self.cfg = CacheConfig()

        self.__API_URL = self.cfg.CDN_URL
        self.__API_ENDPOINT = "/cdns"

    def parse_cdn_response(self, response):
        all_data = {}

        try:
            data = response.split("\n")[2:]  # remove key and sequence id
            if not data:
                return False

            for line in data:
                data_set = line.split("|")
                region = data_set[0]

                if region != "us":
                    continue

                path = data_set[1]
                hosts = [host for host in data_set[2].split(" ") if host]
                servers = data_set[3]
                config_path = data_set[4]

                output = {
                    "path": path,
                    "hosts": hosts,
                    "servers": servers,
                    "config_path": config_path,
                }

                all_data[region] = output

            return all_data
        except Exception as exc:
            self.logger.error(f"Encountered an error parsing API response.")
            self.logger.error(exc)

            return False

    def construct_url(self, host: str, path: str, hash: str):
        return f"http://{host}/{path}/{hash[:2]}/{hash[2:4]}/{hash}"

    async def is_encrypted(self, branch: str, product_config_hash: str):
        async with httpx.AsyncClient(timeout=2) as client:
            url = f"{self.__API_URL}{branch}{self.__API_ENDPOINT}"
            try:
                response = await client.get(url)
            except httpx.ConnectTimeout as exc:
                self.logger.error("TACT CDN info request timed out.")
                return None

            if response.status_code != 200:
                return None

            data = self.parse_cdn_response(response.text)

            product_config = None

            while not product_config:  # loop over all possible hosts until one works
                if not data["us"]["hosts"]:  # type: ignore
                    self.logger.error("Blizzard TACT hosts are broken. Help.")
                    return None

                host = data["us"]["hosts"].pop(0)  # type: ignore
                path = data["us"]["config_path"]  # type: ignore
                cdn_config_url = self.construct_url(host, path, product_config_hash)

                try:
                    self.logger.info(
                        f"Attempting to fetch product config for {branch}..."
                    )
                    cdn_response = await client.get(cdn_config_url)

                    if cdn_response.status_code != 200:
                        self.logger.debug(
                            "Blizzard TACT host returned non 200 status code. Skipping..."
                        )
                        continue
                    else:
                        self.logger.info(
                            f"{branch} product config found, returning encryption status..."
                        )
                        product_config = cdn_response.json()

                except httpx.ConnectTimeout as exc:
                    self.logger.error("TACT API request timed out.")
                    self.logger.error(exc)

            return "decryption_key_name" in product_config["all"]["config"]
