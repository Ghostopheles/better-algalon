import os
import sys
import logging
import asyncio
import discord
import cogs

from dotenv import load_dotenv
from discord.ext import tasks, bridge

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
OWNERID = os.getenv('OWNERID')
DEBUG_GUILDID = os.getenv('DEBUG_GUILDID')
DEBUG = True

DIR = os.path.dirname(os.path.realpath(__file__))
LOG_FILE = os.path.join(DIR, "logs", f"bot_{cogs.get_timestamp(day_only=True)}.log")
LOG_LEVEL = logging.DEBUG if DEBUG else logging.ERROR

START_LOOPS = True

logger = logging.getLogger("discord")
log_format = logging.Formatter("[%(asctime)s]:[%(levelname)s:%(name)s]: %(message)s")

console_handler = logging.StreamHandler()
console_handler.setFormatter(log_format)

logger.addHandler(console_handler)  # adds console handler to our logger
logger.setLevel(LOG_LEVEL)

handler = logging.FileHandler(filename=LOG_FILE, encoding="utf-8", mode="w")
handler.setFormatter(log_format)

logger.addHandler(handler)  # adds filehandler to our logger

logger.propagate = False  # this makes the log entries not repeat themselves

logger.debug(f"Using Python version {sys.version}")
logger.debug(f"Using PyCord version {discord.__version__}")
cogs.log_start()

class CDNBot(bridge.Bot):
    COGS_LIST = [
        'cdnwatcher'
    ]

    def __init__(self, description:str=None, *args, **options):
        super().__init__(description=description, *args, **options)

        for cog in self.COGS_LIST:
            logger.info(f"Loading {cog} cog...")
            self.load_extension(f'cogs.{cog}')
            logger.info(f"{cog} cog loaded!")

    async def on_ready(self):
        logger.info(f"{self.user.name} has successfully connected to Discord!")
        

if __name__ == "__main__":
    bot = CDNBot(
        description="Algalon 2.0",
        command_prefix="!",
        intents=discord.Intents.default(),
        owner_id=OWNERID,
        status=discord.Status.online,
        activity=discord.Activity(type=discord.ActivityType.watching, name="Blizzard's CDN"),
        auto_sync_commands=True,
        #debug_guilds=[DEBUG_GUILDID],
    )
    bot.run(TOKEN)
