import os
import httpx
import asyncio
import discord
import logging

from base64 import b64encode
from discord.ext import bridge, commands

from ..guild_config import GuildCFG
from ..config import BlizzardAPIConfig, CommonStrings

logger = logging.getLogger("discord.api.blizzard")


class BlizzardAPI:
    def __init__(self, region: str = "us", locale: str = "en_US"):
        self.logger = logger

        self.REGION = region
        self.LOCALE = locale

        self.__API_URL = f"https://{self.REGION}.api.blizzard.com"
        self.__API_TOKEN_URL = f"https://{self.REGION}.battle.net/oauth/token"

        self.__CLIENT_ID = os.getenv("BLIZZARD_API_CLIENT_ID")
        self.__CLIENT_SECRET = os.getenv("BLIZZARD_API_CLIENT_SECRET")

        self.__LAST_STATUS_CODE = 0

        asyncio.run(
            self.__auth()
        )  # authenticate with the Blizzard API for self.access_token

    async def __auth(self) -> bool:
        self.logger.info(
            f"Authenticating with the Blizzard API for region {self.REGION}..."
        )
        body = {"grant_type": "client_credentials"}
        headers = {
            "Authorization": f"Basic {b64encode(f'{self.__CLIENT_ID}:{self.__CLIENT_SECRET}'.encode('utf-8')).decode('utf-8')}"
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.__API_TOKEN_URL, headers=headers, data=body
                )
            except Exception as exc:
                self.logger.error("Blizzard API authentication failed.\n")
                self.logger.error(exc)
                return False

            if response.status_code == 200:
                token_json = response.json()

                self.access_token = token_json["access_token"]
                self.access_token_sub = token_json["sub"]
                self.access_token_type = token_json["token_type"]
                self.access_token_lifetime = token_json["expires_in"]

                self.logger.info("Blizzard API authentication successful.")

                return True
            else:
                self.logger.error(
                    f"Blizzard API authentication failed with status code {response.status_code}."
                )
                return False

    def _generate_headers(self, header_type: str, locale: str):
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Battlenet-Namespace": f"{header_type}-{self.REGION}",
            "locale": locale,
            "region": self.REGION,
        }

        return headers

    # decorator to ensure we're authenticated before making api calls
    def _requires_auth(func, *args):  # type: ignore
        async def auth_wrapper(self, *args):
            self.logger.info("Checking for valid Blizzard authentication...")
            self.logger.debug(f"Calling {func.__name__}.")
            await func(self, *args)  # type: ignore

            if self.__LAST_STATUS_CODE == 401:
                self.logger.info("Authentication is busted. Reacquiring...")
                await self.__auth()
                self.__LAST_STATUS_CODE = 0
                return await func(self, *args)  # type: ignore

            return False

        return auth_wrapper

    @_requires_auth  # type: ignore
    async def get_token_price(self, locale: str) -> dict | bool:
        token_endpoint = f"{self.__API_URL}/data/wow/token/index"

        async with httpx.AsyncClient() as client:
            try:
                headers = self._generate_headers("dynamic", locale)
                data = await client.get(token_endpoint, headers=headers)  # type: ignore
            except:
                self.logger.error("Error fetching token price.")
                return False

            if data.status_code == 200:
                self.logger.info("Token data received!")
                json_data = data.json()
                token_data = {
                    "region": self.REGION,
                    "raw": json_data["price"],
                    "gold": int(json_data["price"] / 10000),
                    "last_updated": int(json_data["last_updated_timestamp"] / 1000),
                }

                return token_data
            else:
                self.logger.error(f"Token API returned status code {data.status_code}.")
                self.__LAST_STATUS_CODE = data.status_code
                return False


class RegionalAPI:
    us = BlizzardAPI(region="us")
    eu = BlizzardAPI(region="eu")
    kr = BlizzardAPI(region="kr")
    tw = BlizzardAPI(region="tw")
    cn = BlizzardAPI(region="cn")


# this is the cog that gets added to the discord bot, aka: where the above class interfaces with discord
class BlizzardAPICog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guild_cfg = GuildCFG()
        self.api = RegionalAPI()

    @bridge.bridge_command(name="cdntokenprice")
    async def cdn_token_price(self, ctx: bridge.BridgeApplicationContext):
        """Get the current WoW Token price."""

        region = self.guild_cfg.get_region(ctx.guild_id)  # type: ignore
        locale = self.guild_cfg.get_locale(ctx.guild_id)  # type: ignore

        api = getattr(self.api, region)

        logger.info("Grabbing newest token price...")
        token_data = await api.get_token_price(locale)

        if isinstance(token_data, dict):
            embed = discord.Embed(
                title="Token Price",
                color=discord.Colour.gold(),
                description=f"Updated <t:{token_data['last_updated']}:R>.",
            )
            embed.set_author(
                name="WoW Token Price", icon_url=BlizzardAPIConfig.assets["token_icon"]
            )
            embed.add_field(
                name=f"Current Price [{token_data['region'].upper()}]",
                value=f"{token_data['gold']:,}g",
                inline=True,
            )
            embed.set_footer(text=CommonStrings.EMBED_FOOTER)

            await ctx.interaction.response.send_message(
                embed=embed, ephemeral=True, delete_after=300
            )


def setup(bot):
    bot.add_cog(BlizzardAPICog(bot))
