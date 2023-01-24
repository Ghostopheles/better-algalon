import discord

from .guild_config import GuildCFG
from discord.ext import bridge


class CDNUi(discord.ui.View):
    def __init__(
        self,
        ctx: bridge.BridgeApplicationContext,
        guild_cfg: GuildCFG,
        utility=False,
    ):
        super().__init__()
        self.guild_cfg = guild_cfg
        self.ctx = ctx
        self.utility = utility
        self.guild_id = self.ctx.guild_id

        if not self.utility:
            self.create_select_menu()

    def create_select_menu(self):
        placeholder = "Edit watchlist..."
        min_values = 0
        max_values = len(self.guild_cfg.CONFIG.PRODUCTS)
        options = []
        disabled = False

        watchlist = self.guild_cfg.get_guild_watchlist(self.guild_id)

        for branch, name in self.guild_cfg.CONFIG.PRODUCTS.items():
            default = branch in watchlist

            option = discord.SelectOption(label=name, value=branch, default=default)
            options.append(option)

        branch_select_menu = discord.ui.Select(
            placeholder=placeholder,
            min_values=min_values,
            max_values=max_values,
            options=options,
            disabled=disabled,
        )
        self.branch_menu = branch_select_menu

        async def update_watchlist(interaction: discord.Interaction):
            selected_branches = branch_select_menu.values
            new_watchlist = self.guild_cfg.get_guild_watchlist(self.guild_id)

            for value in self.guild_cfg.CONFIG.PRODUCTS.keys():
                if value in selected_branches and value not in new_watchlist:
                    self.guild_cfg.add_to_guild_watchlist(self.guild_id, value)
                elif value in new_watchlist and value not in selected_branches:
                    self.guild_cfg.remove_from_guild_watchlist(self.guild_id, value)

            await interaction.response.defer()

            return True

        branch_select_menu.callback = update_watchlist
        self.add_item(branch_select_menu)
