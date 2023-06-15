import os
import sys
import cogs
import logging
import discord

from discord.ext import bridge, commands
from logging.handlers import TimedRotatingFileHandler

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

OWNER_ID = os.getenv("OWNER_ID")

DIR = os.path.dirname(os.path.realpath(__file__))

LOG_DIR = os.path.join(DIR, "logs")
LOG_FILE = os.path.join(LOG_DIR, f"bot_{cogs.get_timestamp()}.log")

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

logger = logging.getLogger("discord")
logger.setLevel(logging.DEBUG)
log_format = logging.Formatter("[%(asctime)s]:[%(levelname)s:%(name)s]: %(message)s")

console_handler = logging.StreamHandler()
console_handler.setFormatter(log_format)
console_handler.setLevel(logging.DEBUG)

logger.addHandler(console_handler)  # adds console handler to our logger

file_handler = TimedRotatingFileHandler(
    filename=LOG_FILE, encoding="utf-8", when="midnight", backupCount=30
)
file_handler.setFormatter(log_format)
file_handler.setLevel(logging.DEBUG)

logger.addHandler(file_handler)  # adds filehandler to our logger

logger.info(
    f"Using Python version {sys.version}",
)
logger.info(f"Using PyCord version {discord.__version__}")
cogs.log_start()


# This subclasses the default help command to provide our bot with a prettier help command.
class CDNBotHelpCommand(commands.HelpCommand):
    def get_command_signature(self, command):
        return "%s%s %s" % (
            self.context.clean_prefix,
            command.qualified_name,
            command.signature,
        )

    async def send_bot_help(self, mapping):
        embed = discord.Embed(title="Help", color=discord.Color.blue())

        for cog, commands in mapping.items():
            filtered = await self.filter_commands(commands, sort=True)

            if command_signatures := [self.get_command_signature(c) for c in filtered]:
                cog_name = getattr(cog, "qualified_name", "No Category")
                embed.add_field(
                    name=cog_name, value="\n".join(command_signatures), inline=False
                )

        await self.get_destination().send(embed=embed)

    async def send_command_help(self, command):
        embed = discord.Embed(
            title=self.get_command_signature(command), color=discord.Color.random()
        )

        if command.help:
            embed.description = command.help
        if alias := command.aliases:
            embed.add_field(name="Aliases", value=", ".join(alias), inline=False)

        await self.get_destination().send(embed=embed)

    async def send_help_embed(self, title, description, commands):
        embed = discord.Embed(
            title=title, description=description or "No help found..."
        )

        if filtered_commands := await self.filter_commands(commands):
            for command in filtered_commands:
                embed.add_field(
                    name=self.get_command_signature(command),
                    value=command.help or "No help found...",
                )

        await self.get_destination().send(embed=embed)

    async def send_group_help(self, group):
        title = self.get_command_signature(group)
        await self.send_help_embed(title, group.help, group.commands)

    async def send_cog_help(self, cog):
        title = cog.qualified_name or "No"
        await self.send_help_embed(
            f"{title} Category", cog.description, cog.get_commands()
        )


# The almighty Algalon himself
class CDNBot(bridge.Bot):
    """This is the almighty CDN bot, also known as Algalon. Inherits from `discord.ext.bridge.Bot`."""

    COGS_LIST = ["watcher"]

    def __init__(self, command_prefix, help_command=None, **options):
        command_prefix = command_prefix or "!"
        help_command = help_command or commands.DefaultHelpCommand()

        super().__init__(
            command_prefix=command_prefix, help_command=help_command, **options  # type: ignore
        )

        for cog in self.COGS_LIST:
            logger.info(f"Loading {cog} cog...")
            try:
                self.load_extension(f"cogs.{cog}")
                logger.info(f"{cog} cog loaded!")
            except Exception as exc:
                logger.error(f"Error loading cog {cog}")
                logger.error(exc)

    async def on_ready(self):
        """This `async` function runs once when the bot is connected to Discord and ready to execute commands."""
        logger.info(f"{self.user.name} has successfully connected to Discord!")  # type: ignore

    async def notify_owner_of_command_exception(
        self, ctx: discord.ApplicationContext, exc: discord.DiscordException
    ):
        owner = await self.get_or_fetch_user(self.owner_id)  # type: ignore
        dm_channel = await owner.create_dm()  # type: ignore

        message = f"An error occurred in command `{ctx.command}`:\n```py\n{exc.__class__.__name__}\n"
        message += f"Args:\n"
        message += "\n".join(arg for arg in exc.args)
        message += f"\nCALLER: {ctx.author} ({ctx.author.id})\n"
        message += f"GUILD: {ctx.guild} ({ctx.guild.id})\n```"  # type: ignore
        message += "See logs for traceback."

        await dm_channel.send(message)

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
        help_command=CDNBotHelpCommand(),
        description="Algalon 2.0",
        intents=discord.Intents.default(),
        owner_id=OWNER_ID,
        status=discord.Status.online,
        activity=activity,
        auto_sync_commands=True,
        debug_guilds=debug_guilds,  # debug_guilds,
    )
    bot.run(token)
