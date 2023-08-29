import os
import discord
import logging

from discord.ext import bridge, commands

logger = logging.getLogger("discord.admin")

DEBUG_GUILDS = [int(os.getenv("DEBUG_GUILD_ID")), int(os.getenv("DEBUG_GUILD_ID2"))]


class AdminCog(commands.Cog):
    def __init__(self, bot: bridge.Bot):
        self.bot = bot

    @commands.is_owner()
    @bridge.bridge_command(name="reload", guild_ids=DEBUG_GUILDS)
    async def reload_cog(self, ctx: bridge.BridgeApplicationContext, cog_name: str):
        """Reloads a currently loaded cog."""

        if cog_name == self.qualified_name:
            await ctx.interaction.response.send_message(
                "You cannot kill a god.", ephemeral=True, delete_after=300
            )
            return

        cog_name_internal = f"cogs.{cog_name}"
        logger.debug(f"Reloading {cog_name_internal}")
        try:
            self.bot.reload_extension(cog_name_internal)
        except Exception as exc:
            logger.error(f"Error reloading {cog_name_internal}.")
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
    @bridge.bridge_command(name="guilds", guild_ids=DEBUG_GUILDS, guild_only=True)
    async def get_all_guilds(self, ctx: bridge.BridgeApplicationContext):
        """Dumps details for all guilds Algalon is a part of."""
        message = "```\n"
        for guild in self.bot.guilds:
            guild = await self.bot.fetch_guild(guild.id)
            message += f"""
{guild.name}
ID: {guild.id}
Members (approx): {guild.approximate_member_count}
Description: {guild.description or 'N/A'}
Icon: {guild.icon.url if guild.icon else 'N/A'}
Banner: {guild.banner.url if guild.banner else 'N/A'}
"""

        message += "```"
        await ctx.interaction.response.send_message(
            message, ephemeral=True, delete_after=300
        )

    @commands.is_owner()
    @bridge.bridge_command(name="forceupdate", guild_ids=DEBUG_GUILDS, guild_only=True)
    async def force_update_check(self, ctx: bridge.BridgeApplicationContext):
        """Forces a CDN check."""
        watcher = self.bot.get_cog("CDNCog")
        await watcher.cdn_auto_refresh()
        await ctx.respond("Update in progress...")


def setup(bot):
    bot.add_cog(AdminCog(bot))
