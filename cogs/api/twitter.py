import os
import time
import tweepy.asynchronous as tweepy
import logging

BEARER_KEY = os.getenv("TWITTER_API_BEARER_DEV")

API_KEY = os.getenv("TWITTER_API_KEY_DEV")
API_SECRET = os.getenv("TWITTER_API_SECRET_DEV")

ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")

logger = logging.getLogger("discord.api.twitter")


class Twitter:
    def __init__(self):
        self.bot_client = tweepy.AsyncClient(
            consumer_key=API_KEY,
            consumer_secret=API_SECRET,
            access_token=ACCESS_TOKEN,
            access_token_secret=ACCESS_TOKEN_SECRET,
        )
        self.bot_client.user_agent = "Algalon Ghost"

        self.sent_tokens = []

    async def send_tweet(self, embed, nonce: str):
        logger.info("Sending tweet...")
        if nonce in self.sent_tokens:
            logger.info("Tweet already sent for this package. Skipping...")
            return

        title = f"New build{'s' if len(embed['fields']) > 1 else ''} detected"

        updates = "".join([field["value"] for field in embed["fields"]])
        updates = updates.replace("`", "").replace("*", "")

        timestamp = (
            embed["description"].split("**|**")[0].replace("<t:", "").replace(":f>", "")
        )

        time_object = time.localtime(int(timestamp))

        timestamp = time.strftime("%m-%d-%Y@%I:%M:%S", time_object)

        text = f"{title}:\n{updates}\nFound at: {timestamp} {time_object.tm_zone}"

        response = await self.bot_client.create_tweet(text=text)

        if response and len(response.errors) == 0:  # type: ignore
            logger.info("Tweet sent successfully!")
            self.sent_tokens.append(nonce)
            return
        else:
            logger.error("Error occurred sending tweet. Please investigate.")
            return
