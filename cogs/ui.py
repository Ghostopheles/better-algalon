import discord

from .guild_config import GuildCFG
from discord.ext import bridge


class CDNUi(discord.ui.View):
    def __init__(
        self,
        ctx: bridge.BridgeApplicationContext,
    ):
        super().__init__()
        self.ctx = ctx
        self.guild_cfg = GuildCFG()
        self.guild_id = self.ctx.guild_id

        self.create_select_menu()

    @staticmethod
    async def select_callback(interaction: discord.Interaction):
        await interaction.response.defer()
        guild_cfg = GuildCFG()
        guild_id = interaction.guild_id
        selected_branches = interaction.data.values()  # type: ignore
        existing_watchlist = guild_cfg.get_guild_watchlist(guild_id)  # type: ignore

        if not existing_watchlist:
            await interaction.followup.send(
                content="Watchlist missing, please tell Ghost."
            )
            return False

        success = True

        for value in guild_cfg.CONFIG.PRODUCTS.keys():
            if value in selected_branches and value not in existing_watchlist:
                success = guild_cfg.add_to_guild_watchlist(guild_id, value)  # type: ignore
            elif value in existing_watchlist and value not in selected_branches:
                success = guild_cfg.remove_from_guild_watchlist(guild_id, value)  # type: ignore

        if not success:
            await interaction.followup.send(
                content="Something went wrong when updating your watchlist. Please tell Ghost."
            )
            return False

        return True

    def create_select_menu(self):
        placeholder = "Edit watchlist..."
        min_values = 1
        max_values = 25
        options = []
        disabled = False

        watchlist = self.guild_cfg.get_guild_watchlist(self.guild_id)  # type: ignore

        for branch, name in self.guild_cfg.CONFIG.PRODUCTS.items():
            if len(options) + 1 >= max_values:
                break

            option = discord.SelectOption(
                label=name, value=branch, default=branch in watchlist
            )
            options.append(option)

        branch_select_menu = discord.ui.Select(
            placeholder=placeholder,
            min_values=min_values,
            max_values=max_values,
            options=options,
            disabled=disabled,
        )

        branch_select_menu.callback = self.select_callback  # type: ignore
        self.add_item(branch_select_menu)
