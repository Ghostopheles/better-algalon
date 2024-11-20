import logging
import discord
import discord.ui as ui

from enum import Enum

from cogs.config import (
    SUPPORTED_GAMES,
    SUPPORTED_PRODUCTS,
    TEST_BRANCHES,
    INTERNAL_BRANCHES,
    WOW_BRANCHES,
    DIABLO_BRANCHES,
    RUMBLE_BRANCHES,
    BNET_BRANCHES,
    WatcherConfig,
)

from cogs.utils import convert_watchlist_to_name_set
from cogs.db import AlgalonDB as DB, Branch


logger = logging.getLogger("discord.test")


class WatchlistMenuType(Enum):
    GUILD = 1
    USER = 2


class GuildSelectMenu(ui.Select):
    async def callback(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id
        if interaction.data is None:
            return

        selected = interaction.data["values"]
        if len(selected) > 0:
            game = await DB.get_game_from_branch(selected[0])
            branches = await DB.get_branches_for_game(game)
            old_watchlist = await DB.get_guild_watchlist(guild_id)
            old_watchlist_set = convert_watchlist_to_name_set(old_watchlist)
            for branch in branches:
                branch = branch.internal_name
                if branch in selected and branch not in old_watchlist_set:
                    await DB.add_to_guild_watchlist(guild_id, branch)
                elif branch in old_watchlist_set and branch not in selected:
                    await DB.remove_from_guild_watchlist(guild_id, branch)

        await interaction.response.defer(ephemeral=True, invisible=True)


class UserSelectMenu(ui.Select):
    async def callback(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        if interaction.data is None:
            return

        selected = interaction.data["values"]
        if len(selected) > 0:
            game = await DB.get_game_from_branch(selected[0])
            branches = await DB.get_branches_for_game(game)
            old_watchlist = await DB.get_user_watchlist(user_id)
            old_watchlist_set = convert_watchlist_to_name_set(old_watchlist)
            for branch in branches:
                branch = branch.internal_name
                if branch in selected and branch not in old_watchlist_set:
                    await DB.add_to_user_watchlist(user_id, branch)
                elif branch in old_watchlist_set and branch not in selected:
                    await DB.remove_from_user_watchlist(user_id, branch)

        await interaction.response.defer(ephemeral=True, invisible=True)


class WatchlistUI(ui.View):
    @classmethod
    async def create_menu(
        cls, watchlist: set[str], game: SUPPORTED_GAMES, menuType: WatchlistMenuType
    ):
        branches = await DB.get_branches_for_game(game.value)
        if branches is None or len(branches) == 0:
            return None

        view = cls()

        options = []
        for branch in branches:
            if branch.test:
                description = "This is a test branch"
            elif branch.internal:
                description = "This is an internal branch"
            else:
                description = None

            option = discord.SelectOption(
                label=f"{branch.internal_name} ({branch.public_name})",
                value=branch.internal_name,
                default=branch.internal_name in watchlist,
                description=description,
            )
            options.append(option)

        min_values = 0

        menuClass = (
            GuildSelectMenu if menuType == WatchlistMenuType.GUILD else UserSelectMenu
        )

        menu = menuClass(
            select_type=discord.ComponentType.string_select,
            options=options,
            min_values=min_values,
            max_values=len(options),
        )

        view.add_item(menu)

        return view


class MonitorSelectMenu(ui.Select):
    branch: SUPPORTED_PRODUCTS

    async def callback(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        if interaction.data is None:
            return

        monitorable_fields = await DB.get_all_metadata_fields()

        branch = self.branch.name
        selected = interaction.data["values"]
        for field in monitorable_fields:
            monitoring = await DB.is_user_monitoring(user_id, branch, field)
            if field in selected and not monitoring:
                await DB.user_monitor(user_id, branch, field)
            elif monitoring and field not in selected:
                await DB.user_unmonitor(user_id, branch, field)

        await interaction.response.defer(ephemeral=True, invisible=True)

    def set_branch(self, branch: str):
        self.branch = branch


class MonitorUI(ui.View):
    @classmethod
    async def create(cls, user_id: int, branch: SUPPORTED_PRODUCTS):
        view = cls()

        monitorable_fields = await DB.get_all_metadata_fields()

        min_values = 0
        options = []
        for field in monitorable_fields:
            option = discord.SelectOption(
                label=field,
                value=field,
                default=await DB.is_user_monitoring(user_id, branch.name, field),
                description=f"Notify on changes to the {field} field in {branch}",
            )
            options.append(option)

        menu = MonitorSelectMenu(
            select_type=discord.ComponentType.string_select,
            options=options,
            min_values=min_values,
            max_values=len(options),
        )
        menu.set_branch(branch)

        view.add_item(menu)
        return view


class PremiumButton(ui.Button):
    async def callback(self, interaction: discord.Interaction):
        await interaction.respond("uwu")


class PremiumRequired(ui.View):
    @classmethod
    def create(cls, label: str, sku: int):
        view = cls()
        button = PremiumButton(
            label=label, style=discord.ButtonStyle.premium, sku_id=sku
        )
        view.add_item(button)
        return view
