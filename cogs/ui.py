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

from cogs.guild_config import GuildCFG
from cogs.user_config import UserConfigFile, Monitorable, MonitorableRegion

logger = logging.getLogger("discord.test")


class WatchlistMenuType(Enum):
    GUILD = 1
    USER = 2


def get_branches_for_game(game: SUPPORTED_GAMES):
    match game:
        case SUPPORTED_GAMES.Warcraft:
            return WOW_BRANCHES
        case SUPPORTED_GAMES.Diablo4:
            return DIABLO_BRANCHES
        case SUPPORTED_GAMES.Gryphon:
            return RUMBLE_BRANCHES
        case SUPPORTED_GAMES.BattleNet:
            return BNET_BRANCHES
        case _:
            return None


GUILD_CONFIG = GuildCFG()
USER_CONFIG = UserConfigFile()


class GuildSelectMenu(ui.Select):
    async def callback(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id
        if interaction.data is None:
            return

        selected = interaction.data["values"]
        if len(selected) > 0:
            game = WatcherConfig.get_game_from_branch(selected[0])
            branches = get_branches_for_game(game)
            old_watchlist = GUILD_CONFIG.get_guild_watchlist(guild_id)
            for branch in branches:
                branch = branch.name
                if branch in selected and branch not in old_watchlist:
                    GUILD_CONFIG.add_to_guild_watchlist(guild_id, branch)
                elif branch in old_watchlist and branch not in selected:
                    GUILD_CONFIG.remove_from_guild_watchlist(guild_id, branch)

        await interaction.response.defer(ephemeral=True, invisible=True)


class UserSelectMenu(ui.Select):
    async def callback(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        if interaction.data is None:
            return

        selected = interaction.data["values"]
        if len(selected) > 0:
            game = WatcherConfig.get_game_from_branch(selected[0])
            with USER_CONFIG as cfg:

                branches = get_branches_for_game(game)
                old_watchlist = cfg.get_watchlist(user_id)
                for branch in branches:
                    branch = branch.name
                    if branch in selected and branch not in old_watchlist:
                        cfg.subscribe(user_id, branch)
                    elif branch in old_watchlist and branch not in selected:
                        cfg.unsubscribe(user_id, branch)

        await interaction.response.defer(ephemeral=True, invisible=True)


class WatchlistUI(ui.View):
    @classmethod
    def create_menu(
        cls, watchlist: list[str], game: SUPPORTED_GAMES, menuType: WatchlistMenuType
    ):
        branches = get_branches_for_game(game)
        if branches is None:
            return None

        view = cls()

        options = []
        for branch in branches:
            branch: SUPPORTED_PRODUCTS

            if branch in TEST_BRANCHES:
                description = "This is a test branch"
            elif branch in INTERNAL_BRANCHES:
                description = "This is an internal branch"
            else:
                description = None

            option = discord.SelectOption(
                label=f"{branch.value} ({branch.name})",
                value=branch.name,
                default=branch.name in watchlist,
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


class MonitorSelectMode(Enum):
    FIELD = 1
    REGION = 2


class MonitorSelectMenu(ui.Select):
    mode: MonitorSelectMode

    async def callback(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        if interaction.data is None:
            return

        selected = interaction.data["values"]

        await interaction.response.defer(ephemeral=True, invisible=True)


class MonitorUI(ui.View):
    @classmethod
    def create_monitor_setup(cls, user_id: int, field: Monitorable):
        view = cls()

        min_field_values = 1
        max_field_values = len(Monitorable)
        field_options = []
        for field in Monitorable:
            option = discord.SelectOption(
                label=field,
                value=field.name,
                default=False,
                description="Monitor changes to this field in only this region",
            )

        min_region_values = 1
        max_region_values = 1
        region_options = []
        for region in MonitorableRegion:
            option = discord.SelectOption(
                label=region,
                value=region.name,
                default=region == MonitorableRegion.US,
                description="Monitor changes to this field in only this region",
            )

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
