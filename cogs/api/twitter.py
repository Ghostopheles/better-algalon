import os
import time
import logging

import tweepy.asynchronous as tweepy

from ..config import DebugConfig as dbg

API_KEY = os.getenv("TWITTER_API_KEY_PROD")
API_SECRET = os.getenv("TWITTER_API_SECRET_PROD")

BEARER_KEY = os.getenv("TWITTER_API_BEARER_PROD")

ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")

logger = logging.getLogger("discord.api.twitter")


class Twitter:
    def __init__(self, bot):
        self.bot_client = tweepy.AsyncClient(
            consumer_key=API_KEY,
            consumer_secret=API_SECRET,
            access_token=ACCESS_TOKEN,
            access_token_secret=ACCESS_TOKEN_SECRET,
        )
        self.bot_client.user_agent = "Algalon Ghost"

        self.sent_tokens = []
        self.encrypted_icon = "\U0001F510"

        self.bot = bot
        self.flags = self.bot.features.flags.twitter

    async def send_tweet(self, embed, nonce: str):
        if not self.flags.doTweets:
            logger.info("Tweets disabled, skipping...")
            return

        logger.info("Sending tweet...")
        if nonce in self.sent_tokens:
            logger.info("Tweet already sent for this package. Skipping...")
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

        hashtag = "#Warcraft" if is_warcraft else ""

        title = f"New {hashtag} build{'s' if len(embed['fields']) > 1 else ''} found"

        text = f"{title}:\n{updates}\nFound at: {timestamp} {time_object.tm_zone}"

        if not dbg.debug_enabled:
            response = await self.bot_client.create_tweet(text=text)

            if response and len(response.errors) == 0:  # type: ignore
                logger.info("Tweet sent successfully!")
                self.sent_tokens.append(nonce)
                return
            else:
                logger.error(
                    f"Error occurred sending tweet. Please investigate.\n{response.errors or response}"  # type: ignore
                )
                return
        else:
            logger.debug("Debug mode enabled. Skipping tweet...")
            logger.debug(f"Tweet text:\n{text}")
            return
