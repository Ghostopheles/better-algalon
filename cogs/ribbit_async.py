import logging
import asyncio

from dataclasses import dataclass

from .api.blizzard_tact import BlizzardTACTExplorer

logger = logging.getLogger("discord.ribbit")

TACT = BlizzardTACTExplorer()
REGION = "us"
PORT = 1119
URL = f"{REGION}.version.battle.net:{PORT}"
url_raw = URL.split(":")

field_name_conversions = {
    "BuildConfig": "build_config",
    "CDNConfig": "cdn_config",
    "BuildId": "build",
    "VersionsName": "build_text",
    "ProductConfig": "product_config",
}


@dataclass
class Version:
    region: str
    build_config: str
    cdn_config: str
    build: str
    build_text: str
    product_config: str
    encrypted: bool
    branch: str
    seqn: int

    def __init__(self, data: dict, seqn: int):
        for k, v in data.items():
            if k in field_name_conversions.keys():
                key = field_name_conversions[k]
            else:
                key = k

            self.__setattr__(key, v)

        build_text_split = self.build_text.split(".")[:-1]
        self.build_text = ".".join(build_text_split)
        self.seqn = seqn

    def __dict__(self):
        return {
            "region": self.region,
            "build_config": self.build_config,
            "cdn_config": self.cdn_config,
            "build": self.build,
            "build_text": self.build_text,
            "product_config": self.product_config,
            "encrypted": self.encrypted,
            "branch": self.branch,
            "seqn": self.seqn,
        }


class RibbitClient:
    bNEWLINE = "\r\n"
    sNEWLINE = "\n"

    url = url_raw[0]
    port = int(url_raw[1])

    async def __connect(self):
        logger.debug("Initializing new socket connection...")
        self.reader, self.writer = await asyncio.open_connection(self.url, self.port)

    def __parse(self, data: bytes):
        data_str = data.decode("utf-8")
        data_split = data_str.split("\n")
        sequence = None
        index = []
        output = {}

        for line in data_split:
            if not line:
                continue

            if line.startswith("## seqn = "):
                sequence = line.replace("## seqn = ", "")
                continue

            line_split = line.split("|")

            if len(line_split) > 1:
                if not index:
                    for index_key in line_split:
                        l = index_key.split("!")
                        if len(l) == 2:
                            index.append(l[0])
                    continue
                else:
                    key = line_split[0]
                    for i, entry in enumerate(line_split):
                        if key not in output.keys():
                            output[key] = {}
                        k = index[i]
                        output[key][k] = entry

        return sequence, output

    async def __send(self, command: str):
        logger.info(f"Sending Ribbit command '{command}'...")
        bcommand = bytes(command + self.bNEWLINE, "ascii")

        self.writer.write(bcommand)
        await self.writer.drain()

        seq, data = await self.__receive()
        await self.__close()

        return seq, data

    async def __receive(self):
        chunks = []
        while True:
            chunk = await self.reader.read(4096)
            if chunk:
                chunks.append(chunk)
            else:
                break
        seq, data = self.__parse(b"".join(chunks))
        return seq, data

    async def __close(self):
        self.writer.close()
        await self.writer.wait_closed()

    async def fetch_summary(self) -> tuple[dict, int]:
        await self.__connect()
        sequence, data = await self.__send("v2/summary")
        return data, sequence

    async def fetch_cdn_info_for_product(self, product: str) -> tuple[dict, int]:
        await self.__connect()
        sequence, data = await self.__send(f"v2/products/{product}/cdns")
        return data, sequence

    async def fetch_versions_for_product(
        self, product: str = "wow"
    ) -> tuple[dict, int]:
        await self.__connect()
        logger.info(f"Fetching versions data summary for {product}...")
        command = f"v2/products/{product}/versions"
        sequence, data = await self.__send(command)
        if not data:
            return None, None

        output = {}

        for region in data:
            if region != "us":
                continue

            d = data[region]
            regionData = d
            regionData["region"] = region
            regionData["branch"] = product
            regionData["encrypted"] = await TACT.is_encrypted(
                product, regionData["ProductConfig"]
            )
            output[d["Region"]] = Version(regionData, sequence)

        return output, sequence

    def shutdown(self):
        logger.info("Shutting down...")
        self.__close()


if __name__ == "__main__":
    client = RibbitClient()
