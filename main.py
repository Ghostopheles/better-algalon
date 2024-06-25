import os
import sys
import yaml
import atexit
import discord
import logging
import platform
import logging.config

from cogs.bot import CDNBot
from cogs.utils import get_timestamp, log_start

if platform.machine() != "armv7l":
    from dotenv import load_dotenv

    load_dotenv()

    if not os.getenv("DEBUG"):
        sys.exit(1)

DIR = os.path.dirname(os.path.realpath(__file__))

LOG_DIR = os.path.join(DIR, "logs")
LOG_FILE = os.path.join(LOG_DIR, f"bot_{get_timestamp}.log")

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

log_cfg_path = os.path.join(DIR, "log_config.yaml")
with open(log_cfg_path) as f:
    log_cfg = yaml.safe_load(f)
logging.config.dictConfig(log_cfg)

queue_handler = logging.getHandlerByName("queue_handler")
if queue_handler is not None:
    queue_handler.listener.start()  # type: ignore
    atexit.register(queue_handler.listener.stop)  # type: ignore

logger = logging.getLogger("discord")

owner_id = os.getenv("OWNER_ID")
if owner_id is None:
    logger.critical("Missing owner ID environment variable, aborting...")
    sys.exit(1)

OWNER_ID = int(owner_id)

logger.info(
    f"Using Python version {sys.version}",
)
logger.info(f"Using PyCord version {discord.__version__}")
log_start()

if __name__ == "__main__":
    activity = discord.Activity(
        type=discord.ActivityType.watching,
        name="Blizzard's CDN",
    )

    if os.getenv("DEBUG"):  # is debug mode
        token = os.getenv("DEBUG_DISCORD_TOKEN")
        debug_guilds = [int(os.getenv("DEBUG_GUILD_ID")), int(os.getenv("DEBUG_GUILD_ID2"))]  # type: ignore
    else:  # is NOT debug mode
        token = os.getenv("DISCORD_TOKEN")
        debug_guilds = []

    bot = CDNBot(
        command_prefix="!",
        description="Algalon 2.0",
        intents=discord.Intents.default(),
        owner_id=OWNER_ID,
        status=discord.Status.online,
        activity=activity,
        auto_sync_commands=True,
        debug_guilds=debug_guilds,
    )
    bot.run(token)
