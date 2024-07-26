"""Handles the more specific per-field tracking for users"""

import discord
import logging

from dataclasses import dataclass
from typing import Any
from discord.ext import commands, pages, tasks

from cogs.bot import Algalon
from cogs.user_config import UserConfigFile, Monitorable
from cogs.config import LiveConfig as livecfg
from cogs.config import SUPPORTED_PRODUCTS
from cogs.ui import MonitorUI

logger = logging.getLogger("discord.cdn.watcher")

DELETE_AFTER = livecfg.get_cfg_value("discord", "delete_msgs_after", 120)
COOLDOWN = livecfg.get_cfg_value("discord", "cmd_cooldown", 15)


@dataclass
class UpdatePackage:
    branch: SUPPORTED_PRODUCTS
    field: Monitorable
    new_data: Any


class MonitorCog(commands.Cog):
    """Cog responsible for handling user monitoring"""

    def __init__(self, bot: Algalon):
        self.bot = bot
        self.user_cfg = UserConfigFile()
        self.live_cfg = livecfg()

        self.updates = {}

        watcher = self.bot.get_cog("CDNCog")
        watcher.cdn_cache.register_monitor_cog(self)

    def is_disabled(self):
        return not livecfg.get_cfg_value("discord", "monitoring_enabled", False)

    def get_field_enum_from_value(self, field: str):
        for enum_val in Monitorable:
            if enum_val.value == field:
                return enum_val

    def get_all_watchers_for_branch_field(
        self, branch: SUPPORTED_PRODUCTS, field: Monitorable
    ) -> list[str]:
        users = []
        with self.user_cfg as cfg:
            for user_id, user_entry in cfg.users:
                if user_entry.is_monitoring(branch.name, field):
                    users.append(user_id)

        return users

    def on_field_update(self, branch: str, field: str, new_data: Any):
        if self.is_disabled():
            return

        branch = SUPPORTED_PRODUCTS[branch]
        field = self.get_field_enum_from_value(field)
        package = UpdatePackage(branch, field, new_data)
        watchers = self.get_all_watchers_for_branch_field(branch, field)
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
                if package.field == Monitorable.CDNConfig:
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
                "Monitoring features are currently disabled. Please try again later."
            )
            return

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
