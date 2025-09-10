import os
import time
import aiohttp
import logging

from typing import Optional

from atproto import AsyncClient as BskyAsyncClient
from atproto.exceptions import AtProtocolError
from tweepy.asynchronous import AsyncClient as TwitterAsyncClient

from cogs.config import DebugConfig as dbg, CacheConfig as cfg, LiveConfig as live_cfg

TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET")

TWITTER_BEARER_KEY = os.getenv("TWITTER_API_BEARER")

TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")

BSKY_URL = "https://bsky.social/xrpc"
BSKY_USER = os.getenv("BSKY_USER")
BSKY_PASS = os.getenv("BSKY_PASS")

logger = logging.getLogger("discord.api.socials")

DISALLOWED_GAMES = [game.name for game in cfg.PRODUCTS if "wow" not in game.name]


class SocialPlatforms:
    twitter_sent_tokens = []
    bsky_sent_tokens = []
    encrypted_icon = "\U0001f510"

    def __init__(self):
        self.twitter = TwitterAsyncClient(
            consumer_key=TWITTER_API_KEY,
            consumer_secret=TWITTER_API_SECRET,
            access_token=TWITTER_ACCESS_TOKEN,
            access_token_secret=TWITTER_ACCESS_TOKEN_SECRET,
        )
        self.bsky = BskyAsyncClient(base_url=BSKY_URL)

    def can_tweet(self, nonce: Optional[str] = None) -> bool:
        if nonce is not None and nonce in self.twitter_sent_tokens:
            return False

        return live_cfg.is_social_platform_enabled("twitter")

    def can_bsky_post(self, nonce: Optional[str] = None) -> bool:
        if nonce is not None and nonce in self.bsky_sent_tokens:
            return False

        return live_cfg.is_social_platform_enabled("bsky")

    def remove_disallowed_games(self, data: dict):
        for field in data["fields"]:
            for line in field["value"].split("\n"):
                product = line[line.find("(") + 1 : line.find(")")]
                if product in DISALLOWED_GAMES:
                    field["value"] = field["value"].replace(line + "\n", "")

        if len(data["fields"][0]["value"].splitlines()) == 0:
            return False

        return data

    async def distribute_posts(self, embed, nonce: str):
        if dbg.debug_enabled:
            logger.debug("Debug mode enabled. Skipping social posts...")
            return

        embed = self.remove_disallowed_games(embed)

        if not embed:
            logger.debug("Skipping social posts for disallowed game...")
            return

        logger.info("Sending social posts...")
        if nonce in self.twitter_sent_tokens and nonce in self.bsky_sent_tokens:
            logger.critical("Social posts already sent for this package. Skipping...")
            return

        is_warcraft = False

        for field in embed["fields"]:
            if "wow" in field["value"]:
                is_warcraft = True

        updates = "".join(  # commit a crime to filter out the new diff link
            [field["value"].split(" | ")[0] + "\n" for field in embed["fields"]]
        )
        updates = updates.replace("`", "").replace("*", "")
        updates = updates.replace(":lock:", self.encrypted_icon)

        timestamp = (
            embed["description"].split("**|**")[0].replace("<t:", "").replace(":f>", "")
        )

        time_object = time.localtime(int(timestamp))

        timestamp = time.strftime("%m-%d-%Y@%I:%M:%S", time_object)

        hashtag = " #Warcraft" if is_warcraft else ""

        title = f"New{hashtag} build{'s' if len(embed['fields']) > 1 else ''} found"

        text = f"{title}:\n{updates}Found at: {timestamp} {time_object.tm_zone}"

        if self.can_tweet(nonce):
            try:  # round one, twitter (X?)
                logger.info("Tweeting...")
                await self.send_tweet(text)
                self.twitter_sent_tokens.append(nonce)
            except aiohttp.ClientResponseError as exc:
                logger.critical(
                    f'Error occurred sending tweet with status {exc.code}: "{exc.message}"',
                    exc_info=True,
                )

        if self.can_bsky_post(nonce):
            try:  # round two, bluesky
                logger.info("Sending Bluesky post...")
                await self.send_bsky_post(text)
                self.bsky_sent_tokens.append(nonce)
            except AtProtocolError:
                logger.critical(f"Failed to create Bluesky post", exc_info=True)

    async def send_tweet(self, text: str):
        response = await self.twitter.create_tweet(text=text)
        if isinstance(response, aiohttp.ClientResponse):
            response.raise_for_status()
            logger.info("Tweet sent successfully!")

    async def send_bsky_post(self, text: str):
        await self.bsky.login(BSKY_USER, BSKY_PASS)
        await self.bsky.send_post(text, langs=["en-US"])
        logger.info("Bluesky post sent successfully!")
