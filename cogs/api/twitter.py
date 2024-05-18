import os
import time
import logging

import tweepy.asynchronous as tweepy

from ..config import DebugConfig as dbg, CacheConfig as cfg

API_KEY = os.getenv("TWITTER_API_KEY")
API_SECRET = os.getenv("TWITTER_API_SECRET")

BEARER_KEY = os.getenv("TWITTER_API_BEARER")

ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")

logger = logging.getLogger("discord.api.twitter")

DISALLOWED_GAMES = [game.name for game in cfg.PRODUCTS if "wow" not in game.name]


class Twitter:
    def __init__(self):
        self.bot_client = tweepy.AsyncClient(
            consumer_key=API_KEY,
            consumer_secret=API_SECRET,
            access_token=ACCESS_TOKEN,
            access_token_secret=ACCESS_TOKEN_SECRET,
        )

        self.sent_tokens = []
        self.encrypted_icon = "\U0001F510"

    def filter_tweet_to_remove_disallowed_games(self, data: dict):
        for field in data["fields"]:
            for line in field["value"].split("\n"):
                product = line[line.find("(") + 1 : line.find(")")]
                if product in DISALLOWED_GAMES:
                    field["value"] = field["value"].replace(line + "\n", "")

        if len(data["fields"][0]["value"].splitlines()) == 0:
            return False

        return data

    async def send_tweet(self, embed, nonce: str):
        embed = self.filter_tweet_to_remove_disallowed_games(embed)

        if not embed:
            logger.debug("Skipping tweet for disallowed game...")
            return

        logger.info("Sending tweet...")
        if nonce in self.sent_tokens:
            logger.critical("Tweet already sent for this package. Skipping...")
            return

        is_warcraft = False

        for field in embed["fields"]:
            if "wow" in field["value"]:
                is_warcraft = True

        updates = "".join([field["value"] for field in embed["fields"]])
        updates = updates.replace("`", "").replace("*", "")
        updates = updates.replace(":lock:", self.encrypted_icon)

        timestamp = (
            embed["description"].split("**|**")[0].replace("<t:", "").replace(":f>", "")
        )

        time_object = time.localtime(int(timestamp))

        timestamp = time.strftime("%m-%d-%Y@%I:%M:%S", time_object)

        hashtag = " #Warcraft" if is_warcraft else ""

        title = f"New{hashtag} build{'s' if len(embed['fields']) > 1 else ''} found"

        text = f"{title}:\n{updates}\nFound at: {timestamp} {time_object.tm_zone}"

        if not dbg.debug_enabled:
            try:
                response = await self.bot_client.create_tweet(text=text)
                if response and len(response.errors) == 0:  # type: ignore
                    logger.info("Tweet sent successfully!")
                    self.sent_tokens.append(nonce)
                    return
                else:
                    logger.critical(
                        f"Error occurred sending tweet.\n{response.errors or response}"  # type: ignore
                    )
                    return response
            except Exception:
                logger.critical("Error occurred sending tweet.", exc_info=True)
                return text
        else:
            logger.info("Debug mode enabled. Skipping tweet...")
            return
