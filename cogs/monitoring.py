"""Handles the more specific per-field tracking for users"""

import time
import httpx
import secrets
import discord
import logging

from typing import Optional, Union
from discord.ext import commands, pages, tasks

from cogs.bot import Algalon
from cogs.user_config import UserConfigFile, Monitorable, MonitorableRegion
from cogs.guild_config import GuildCFG
from cogs.cdn_cache import CDNCache
from cogs.config import CommonStrings
from cogs.config import LiveConfig as livecfg
from cogs.config import WatcherConfig as cfg
from cogs.config import DebugConfig as dbg
from cogs.config import SUPPORTED_GAMES, SUPPORTED_PRODUCTS
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

    @monitor_commands.command(name="add")
    @commands.cooldown(1, COOLDOWN, commands.BucketType.user)
    async def monitor_add(
        self,
        ctx: discord.ApplicationContext,
        branch: str,
        field: Monitorable,
        region: MonitorableRegion = MonitorableRegion.US,
    ):
        """Add a field to monitor for updates"""
        with self.user_cfg as user:
            author_id = ctx.author.id
            if user.is_monitoring(author_id, branch, field, region):
                message = (
                    "You are already monitoring that field for this branch and region"
                )
                await ctx.respond(message, ephemeral=True, delete_after=DELETE_AFTER)
                return
            else:
                success, message = user.monitor(author_id, branch, field, region)
                if not success:
                    await ctx.respond(
                        message, ephemeral=True, delete_after=DELETE_AFTER
                    )
                else:
                    await ctx.respond(
                        f"Now monitoring {field} for the `{branch}` branch in region {region.name}",
                        ephemeral=True,
                        delete_after=DELETE_AFTER,
                    )


def setup(bot: Algalon):
    bot.add_cog(MonitorCog(bot))
