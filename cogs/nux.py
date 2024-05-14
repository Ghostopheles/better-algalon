import discord
import logging

from discord.ext import bridge, commands

from .guild_config import GuildCFG

logger = logging.getLogger("discord.nux")


class GuildNUX(commands.Cog):
    def __init__(self, bot: bridge.Bot):
        self.bot = bot
        self.guild_cfg = GuildCFG()
        self.watcher = self.bot.get_cog("CDNCog")

    async def get_nux_message(
        self,
        guild: discord.Guild,
    ) -> str:
        cmd_link_set_channel = self.watcher.get_command_link("setchannel")
        cmd_link_get_watchlist = self.watcher.get_command_link("watchlist")
        cmd_link_add_to_watchlist = self.watcher.get_command_link("addtowatchlist")
        cmd_link_rm_from_watchlist = self.watcher.get_command_link(
            "removefromwatchlist"
        )
        cmd_link_data = self.watcher.get_command_link("cdndata")

        owner_user = await self.bot.get_or_fetch_user(self.bot.owner_id)
        owner_mention = owner_user.mention

        bot_display_name = self.bot.user.display_name

        nux_message = f"""
# Greetings from the Titans!
I'm {bot_display_name} and I'll be {guild.name}'s *personal* constellar :crystal_ball:.

**Here's a few tips to help you get started:**
- Select the channels you want me to send notifications to by calling {cmd_link_set_channel} **from** the channel you want to use. You can set a different channel for each supported game.
- Check out your server's watchlist with {cmd_link_get_watchlist}
- Add branches to your server's watchlist with {cmd_link_add_to_watchlist} and remove them with {cmd_link_rm_from_watchlist}
- View the currently cached data with {cmd_link_data}

:blue_heart: Thanks for trying out Algalon! :blue_heart:

If you have any questions, concerns, or suggestions, please reach out to {owner_mention} here on Discord, or open a GitHub issue [here](https://github.com/Ghostopheles/better-algalon).
"""
        return nux_message

    @commands.Cog.listener("on_guild_join")
    async def on_guild_join(self, guild: discord.Guild):
        logger.info(f"Joined new guild {guild.name} ({guild.id})!")

        if not self.guild_cfg.does_guild_config_exist(guild.id):
            self.guild_cfg.add_guild_config(guild.id)

        channel = guild.system_channel or guild.public_updates_channel
        if not channel:
            return

        nux_message = await self.get_nux_message(guild)
        await channel.send(nux_message)


def setup(bot):
    bot.add_cog(GuildNUX(bot))
