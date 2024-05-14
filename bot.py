import os
import sys
import cogs
import yaml
import atexit
import discord
import logging
import platform
import logging.config

from discord.ext import bridge

if platform.machine() != "armv71":
    from dotenv import load_dotenv

    load_dotenv()

    if not os.getenv("DEBUG"):
        sys.exit(0)

OWNER_ID = int(os.getenv("OWNER_ID"))

DIR = os.path.dirname(os.path.realpath(__file__))

LOG_DIR = os.path.join(DIR, "logs")
LOG_FILE = os.path.join(LOG_DIR, f"bot_{cogs.get_timestamp()}.log")

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

log_cfg_path = os.path.join(DIR, "log_config.yaml")
with open(log_cfg_path) as f:
    log_cfg = yaml.safe_load(f)
logging.config.dictConfig(log_cfg)

queue_handler = logging.getHandlerByName("queue_handler")
if queue_handler is not None:
    queue_handler.listener.start()
    atexit.register(queue_handler.listener.stop)

logger = logging.getLogger("discord")

logger.info(
    f"Using Python version {sys.version}",
)
logger.info(f"Using PyCord version {discord.__version__}")
cogs.log_start()


# The almighty Algalon himself
class CDNBot(bridge.Bot):
    """This is the almighty CDN bot, also known as Algalon. Inherits from `discord.ext.bridge.Bot`."""

    COGS_LIST = ["watcher", "nux", "admin"]

    def __init__(self, command_prefix, **options):
        command_prefix = command_prefix or "!"

        super().__init__(command_prefix=command_prefix, **options)  # type: ignore

        for cog in self.COGS_LIST:
            logger.info(f"Loading {cog} cog...")
            try:
                self.load_extension(f"cogs.{cog}")
                logger.info(f"{cog} cog loaded!")
            except Exception:
                logger.error(f"Error loading cog '{cog}'", exc_info=True)

    async def on_ready(self):
        """This `async` function runs once when the bot is connected to Discord and ready to execute commands."""
        logger.info(f"{self.user.name} has successfully connected to Discord!")  # type: ignore

    async def notify_owner_of_command_exception(
        self, ctx: discord.ApplicationContext, exc: discord.DiscordException
    ):
        message = f"An error occurred in command `{ctx.command}`:\n```py\n{exc.__class__.__name__}\n"
        message += f"Args:\n"
        message += "\n".join(arg for arg in exc.args)
        message += f"\nCALLER: {ctx.author} ({ctx.author.id})\n"
        message += f"GUILD: {ctx.guild} ({ctx.guild.id})\n```"  # type: ignore
        message += "See logs for traceback."

        await self.send_message_to_owner(message)

    async def send_message_to_owner(self, message: str):
        owner = await self.get_or_fetch_user(self.owner_id)  # type: ignore
        dm_channel = await owner.create_dm()  # type: ignore
        await dm_channel.send(message)


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
