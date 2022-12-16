import os
import sys
import cogs
import logging
import discord

from dotenv import load_dotenv
from discord.ext import bridge
from logging.handlers import TimedRotatingFileHandler

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
OWNERID = os.getenv('OWNERID')
DEBUG_GUILDID = os.getenv('DEBUG_GUILDID')

DIR = os.path.dirname(os.path.realpath(__file__))
LOG_FILE = os.path.join(DIR, "logs", f"bot_{cogs.get_timestamp()}.log")

START_LOOPS = True

logger = logging.getLogger("discord")
logger.setLevel(logging.DEBUG)
log_format = logging.Formatter("[%(asctime)s]:[%(levelname)s:%(name)s]: %(message)s")

console_handler = logging.StreamHandler()
console_handler.setFormatter(log_format)
console_handler.setLevel(logging.INFO)

logger.addHandler(console_handler)  # adds console handler to our logger

file_handler = TimedRotatingFileHandler(filename=LOG_FILE,
    encoding="utf-8", when='midnight', backupCount=30)
file_handler.setFormatter(log_format)
file_handler.setLevel(logging.DEBUG)

logger.addHandler(file_handler)  # adds filehandler to our logger

logger.propagate = False  # this makes the log entries not repeat themselves

logger.info("Using Python version %s", sys.version)
logger.info("Using PyCord version %s", discord.__version__)
cogs.log_start()

class CDNBot(bridge.Bot): # pylint: disable=too-many-ancestors
    """This is the almighty CDN bot, also known as Algalon. Inherits from `discord.ext.bridge.Bot`."""
    COGS_LIST = [
        'cdnwatcher'
    ]

    def __init__(self, description:str=None, *args, **options):
        super().__init__(description, *args, **options)

        for cog in self.COGS_LIST:
            logger.info("Loading %s cog...", cog)
            try:
                self.load_extension(f'cogs.{cog}')
                logger.info("%s cog loaded!", cog)
            except Exception as exc:
                logger.error("Error loading cog %s", cog)
                logger.error(exc)

    async def on_ready(self):
        """This `async` function runs once when the bot is connected to Discord and ready to execute commands."""
        logger.info("%s has successfully connected to Discord!", self.user.name)

if __name__ == "__main__":
    activity = discord.Activity(
        type=discord.ActivityType.watching,
        name="Blizzard's CDN",
    )

    bot = CDNBot(
        description="Algalon 2.0",
        intents=discord.Intents.default(),
        owner_id=OWNERID,
        status=discord.Status.online,
        activity=activity,
        auto_sync_commands=True,
    )
    bot.run(TOKEN)

