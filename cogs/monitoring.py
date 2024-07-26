"""Handles the more specific per-field tracking for users"""

import discord
import logging

from typing import Optional, Union
from discord.ext import commands, pages, tasks

from cogs.bot import Algalon
from cogs.user_config import UserConfigFile, Monitorable
from cogs.config import LiveConfig as livecfg
from cogs.config import SUPPORTED_PRODUCTS
from cogs.ui import MonitorUI
from cogs.utils import get_discord_timestamp

logger = logging.getLogger("discord.cdn.watcher")

DELETE_AFTER = livecfg.get_cfg_value("discord", "delete_msgs_after", 120)
COOLDOWN = livecfg.get_cfg_value("discord", "cmd_cooldown", 15)


class MonitorCog(commands.Cog):
    """Cog responsible for handling user monitoring"""

    def __init__(self, bot: Algalon):
        self.bot = bot
        self.user_cfg = UserConfigFile()
        self.live_cfg = livecfg()

    monitor_commands = discord.SlashCommandGroup(
        name="monitor",
        description="Data monitoring commands",
        contexts={
            discord.InteractionContextType.private_channel,
            discord.InteractionContextType.guild,
            discord.InteractionContextType.bot_dm,
        },
        integration_types={
            discord.IntegrationType.guild_install,
            discord.IntegrationType.user_install,
        },
    )

    @monitor_commands.command(name="edit")
    @commands.cooldown(1, COOLDOWN, commands.BucketType.user)
    @discord.Option(input_type=str, description="Branch name")
    async def monitor_edit(
        self,
        ctx: discord.ApplicationContext,
        branch: str,
    ):
        """Edit the fields you're watching for the given branch"""
        try:
            branch = SUPPORTED_PRODUCTS[branch]
        except:
            await ctx.respond(
                "Invalid branch specified", ephemeral=True, delete_after=DELETE_AFTER
            )

        view = MonitorUI.create(ctx.author.id, branch)
        await ctx.respond(
            f"Edit the fields you're watching for `{branch.name}` below.",
            view=view,
            ephemeral=True,
            delete_after=300,
        )


def setup(bot: Algalon):
    bot.add_cog(MonitorCog(bot))
