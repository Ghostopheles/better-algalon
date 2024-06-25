import discord
import logging

from typing import Union
from discord.ext import bridge

logger = logging.getLogger("discord")


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
        self,
        ctx: discord.ApplicationContext,
        exc: Union[discord.DiscordException, Exception],
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
