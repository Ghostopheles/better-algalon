import io
import logging
import discord

from discord.ext import commands

from cogs.bot import Algalon
from cogs.config import LiveConfig as cfg

logger = logging.getLogger("discord.admin")

TRUSTED_GUILDS = cfg.get_cfg_value("discord", "trusted_guilds")

HOME_GUILD = [cfg.get_debug_value("debug_guild")]


class AdminCog(commands.Cog):
    def __init__(self, bot: Algalon):
        self.bot = bot

    admin_commands = discord.SlashCommandGroup(
        name="admin",
        description="Administration commands",
        guild_ids=HOME_GUILD,
    )

    @commands.is_owner()
    @admin_commands.command(name="reload")
    async def reload_cog(self, ctx: discord.ApplicationContext, cog_name: str):
        """Reloads a currently loaded cog."""

        if cog_name == self.qualified_name:
            await ctx.interaction.response.send_message(
                "You cannot kill a god.", ephemeral=True, delete_after=300
            )
            return

        cog_name_internal = f"cogs.{cog_name}"
        logger.info(f"Reloading {cog_name_internal}")
        try:
            self.bot.reload_extension(cog_name_internal)
        except Exception as exc:
            logger.error(f"Error reloading cog '{cog_name_internal}'", exc_info=True)
            await self.bot.notify_owner_of_command_exception(ctx, exc)
            await ctx.interaction.response.send_message(
                f"busted.\n`{exc}`", ephemeral=True, delete_after=300
            )
            return

        logger.debug(f"{cog_name_internal} reloaded successfully.")

        await ctx.interaction.response.send_message(
            f"`{cog_name}` reloaded successfully."
        )

    @commands.is_owner()
    @admin_commands.command(name="guilds")
    async def get_all_guilds(self, ctx: discord.ApplicationContext):
        """Dumps details for all guilds Algalon is a part of."""
        await ctx.defer()
        message = ""
        for guild in self.bot.guilds:
            guild = await self.bot.fetch_guild(guild.id)
            message += f"""Guild: {guild.name}
ID: {guild.id}
Members (approx): {guild.approximate_member_count}\n
"""

        message_bytes = io.BytesIO(message.encode())
        file = discord.File(message_bytes, filename="guilds.txt")
        await ctx.respond(file=file)
        message_bytes.close()

    @commands.is_owner()
    @admin_commands.command(name="forceupdate")
    async def force_update_check(self, ctx: discord.ApplicationContext):
        """Forces a CDN check."""
        watcher = self.bot.get_cog("CDNCog")
        await ctx.defer()
        await watcher.cdn_auto_refresh()
        await ctx.respond("Updates complete.", ephemeral=True, delete_after=300)

    # funni commands

    @discord.slash_command(
        name="alien",
        guild_ids=TRUSTED_GUILDS,
    )
    async def alien(self, ctx: discord.ApplicationContext):
        """secre"""
        await ctx.respond("behind you")

    @commands.is_owner()
    @commands.message_command(
        name="Perceive",
        guild_ids=TRUSTED_GUILDS,
    )
    async def Perceive(self, ctx: discord.ApplicationContext, message: discord.Message):
        diffs = 1141816184405229608
        fatcathuh = 1140450046748397691
        emoji = self.bot.get_emoji(fatcathuh)
        if emoji is None:
            emoji = self.bot.get_emoji(diffs)

        await message.add_reaction(emoji)
        await ctx.respond("gottem", ephemeral=True, delete_after=5)


def setup(bot):
    bot.add_cog(AdminCog(bot))
