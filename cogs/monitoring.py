"""Handles the more specific per-field tracking for users"""

import discord
import logging

from dataclasses import dataclass
from typing import Any
from discord.ext import commands

from cogs.bot import Algalon
from cogs.config import LiveConfig as livecfg
from cogs.config import SUPPORTED_PRODUCTS
from cogs.ui import MonitorUI
from cogs.db import AlgalonDB as DB

logger = logging.getLogger("discord.cdn.watcher")

DELETE_AFTER = livecfg.get_cfg_value("discord", "delete_msgs_after", 120)
COOLDOWN = livecfg.get_cfg_value("discord", "cmd_cooldown", 15)


@dataclass
class UpdatePackage:
    branch: SUPPORTED_PRODUCTS
    field: str
    new_data: Any


class MonitorCog(commands.Cog):
    """Cog responsible for handling user monitoring"""

    def __init__(self, bot: Algalon):
        self.bot = bot
        self.live_cfg = livecfg()

        self.updates = {}

        watcher = self.bot.get_cog("CDNCog")
        watcher.cdn_cache.register_monitor_cog(self)

    def is_disabled(self):
        return not livecfg.get_cfg_value("features", "monitoring_enabled", False)

    async def on_field_update(self, branch: str, field: str, new_data: Any):
        if self.is_disabled():
            return

        if SUPPORTED_PRODUCTS.has_key(branch):
            branch = SUPPORTED_PRODUCTS[branch]
        else:
            return

        package = UpdatePackage(branch, field, new_data)
        watchers = await DB.get_all_monitors_for_branch_field(branch.name, field)
        if len(watchers) == 0:
            return

        for user_id in watchers:
            if user_id in self.updates:
                self.updates[user_id].append(package)
            else:
                self.updates[user_id] = [package]

    async def distribute_notifications(self):
        if self.is_disabled():
            return

        updates = self.updates
        if len(updates) == 0:
            return

        num_cdn_config_updates = 0
        for user_id, packages in self.updates.items():
            user = await self.bot.get_or_fetch_user(int(user_id))
            if user is None:
                logger.warning(
                    f"Unable to fetch {user_id} from Discord to distribute field updates"
                )
                return

            i = len(packages)
            message = f"## Field change{'s'[:i^1]} found:\n"
            for package in packages:
                package: UpdatePackage
                if package.field == "cdn_config":  # TODO: don't hardcode this
                    if num_cdn_config_updates > 0:
                        continue
                    else:
                        num_cdn_config_updates += 1

                new_data = package.new_data
                if new_data == "":
                    new_data = "EMPTY"
                else:
                    new_data = f"`{new_data}`"

                message += f"**{package.branch}**: `{package.branch.name}`.`{package.field}` -> {new_data}\n"

            dm_channel = await user.create_dm()
            if dm_channel:
                await dm_channel.send(message)

        self.updates.clear()

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
    @discord.option(name="branch", input_type=str, description="Branch name")
    async def monitor_edit(
        self,
        ctx: discord.ApplicationContext,
        branch: str,
    ):
        """Edit the fields you're watching for the given branch"""
        if self.is_disabled():
            await ctx.respond(
                "Monitoring features are currently disabled. Please try again later.",
                ephemeral=True,
                delete_after=DELETE_AFTER,
            )
            return

        if SUPPORTED_PRODUCTS.has_key(branch):
            branch = SUPPORTED_PRODUCTS[branch]
        else:
            await ctx.respond(
                "Invalid branch specified", ephemeral=True, delete_after=DELETE_AFTER
            )
            return

        view = await MonitorUI.create(ctx.author.id, branch)
        await ctx.respond(
            f"Edit the fields you're watching for `{branch.name}` below.",
            view=view,
            ephemeral=True,
            delete_after=300,
        )


def setup(bot: Algalon):
    bot.add_cog(MonitorCog(bot))
