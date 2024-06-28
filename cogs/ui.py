import logging
import discord
import discord.ui as ui

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

logger = logging.getLogger("discord.test")


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


class SelectMenu(ui.Select):
    async def callback(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id
        if interaction.data is None:
            return

        selected = interaction.data["values"]
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


class WatchlistUI(ui.View):
    @classmethod
    def create_menus(
        cls,
        watchlist: list[str],
        game: SUPPORTED_GAMES,
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

        menu = SelectMenu(
            select_type=discord.ComponentType.string_select,
            options=options,
            min_values=min_values,
            max_values=len(options),
        )

        view.add_item(menu)

        return view
