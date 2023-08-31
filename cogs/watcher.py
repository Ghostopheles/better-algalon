"""This is the module that handles watching the Blizzard CDN and posting updates to the correct places."""

import os
import time
import httpx
import secrets
import discord
import logging

from discord.ext import bridge, commands, pages, tasks

from .guild_config import GuildCFG
from .cdn_cache import CDNCache
from .config import FETCH_INTERVAL, CommonStrings
from .config import WatcherConfig as cfg
from .config import DebugConfig as dbg
from .config import SUPPORTED_GAMES, SUPPORTED_PRODUCTS
from .utils import get_discord_timestamp
from .api.twitter import Twitter

START_LOOPS = True

logger = logging.getLogger("discord.cdn.watcher")


class CDNCog(commands.Cog):
    """This is the actual Cog that gets added to the Discord bot."""

    def __init__(self, bot: bridge.Bot):
        self.bot = bot
        self.cdn_cache = CDNCache()
        self.guild_cfg = GuildCFG()
        self.twitter = Twitter()
        self.last_update = 0
        self.last_update_formatted = ""

        if dbg.debug_enabled:
            logger.debug("<- Starting bot in DEBUG mode ->")

        if START_LOOPS:
            self.cdn_auto_refresh.add_exception_type(httpx.ConnectTimeout)
            self.cdn_auto_refresh.start()

            self.integrity_check.start()

    @tasks.loop(hours=24)
    async def integrity_check(self):
        await self.bot.wait_until_ready()

        logger.info("Running guild configuration integrity check...")

        for guild in self.bot.guilds:
            if not self.guild_cfg.does_guild_config_exist(guild.id):
                logger.info(
                    f"Adding missing guild configuration for guild {guild.id}..."
                )
                self.guild_cfg.add_guild_config(guild.id)

        self.guild_cfg.validate_guild_configs()

        for guild_id in self.guild_cfg.get_all_guild_configs().keys():
            if int(guild_id) not in [guild.id for guild in self.bot.guilds]:
                logger.info(
                    f"No longer a part of guild {guild_id}, removing guild configuration..."
                )
                self.guild_cfg.remove_guild_config(guild_id)

        logger.info("Running cache configuration check...")

        for product in self.cdn_cache.CONFIG.PRODUCTS:
            if product.name not in self.cdn_cache.get_all_config_entries():
                logger.info(f"New product detected. Adding default entry for {product}")
                self.cdn_cache.set_default_entry(product.name)

    def get_command_link(self, command: str):
        all_cmds = self.get_commands()
        for cmd in all_cmds:
            if isinstance(cmd, bridge.BridgeCommand):
                slash = cmd.slash_variant
                if slash and slash.name == command:
                    return slash.mention
            elif isinstance(cmd, discord.SlashCommand):
                if cmd.name == command:
                    return cmd.mention

    async def notify_owner_of_exception(
        self,
        error,
        ctx: discord.ApplicationContext | bridge.BridgeApplicationContext | None = None,
    ):
        """This is supposed to notify the owner of an error, but doesn't always work."""
        owner = await self.bot.fetch_user(self.bot.owner_id)  # type: ignore
        channel = await owner.create_dm()

        if isinstance(error, Exception):
            message = (
                f"I've encountered an error! Help!\n```py\n{error.args}\n{error}\n```\n"
            )
        else:
            message = f"I've encountered an error! Help!\n```py\n{error}\n```\n"

        if ctx:
            message += f"CALLER: {ctx.author}\nGUILD: {ctx.guild.name} | {ctx.guild_id}"  # type: ignore

        await channel.send(message)

    def build_embeds(self, data: dict, guild_id: int):
        """This builds notification embeds with the given data."""

        guild_watchlist = self.guild_cfg.get_guild_watchlist(guild_id)

        all_embeds = []

        for game, update_data in data.items():
            target_channel = self.guild_cfg.get_notification_channel(guild_id, game)

            if not target_channel:
                logger.warning(
                    f"Guild {guild_id} has not chosen a notification channel, skipping..."
                )
                continue

            color = (
                discord.Color.dark_blue() if game == "wow" else discord.Color.dark_red()
            )

            embed = discord.Embed(
                color=color,
                title=cfg.strings.EMBED_GAME_STRINGS[game]["title"],
                description=f"{get_discord_timestamp()} **|** {get_discord_timestamp(relative=True)}",
                url=cfg.strings.EMBED_GAME_STRINGS[game]["url"],
            )

            embed.set_author(
                name=cfg.strings.EMBED_GAME_STRINGS[game]["name"],
                icon_url=cfg.strings.EMBED_GAME_STRINGS[game]["icon_url"],
            )

            embed.set_footer(text=CommonStrings.EMBED_FOOTER)

            value_string = ""

            for ver in update_data:
                branch = ver["branch"]
                logger.debug(f"Building embed for {branch}")

                if branch not in guild_watchlist:
                    continue

                if "old" in ver:
                    build_text_old = ver["old"][cfg.indices.BUILDTEXT]
                    build_old = ver["old"][cfg.indices.BUILD]
                else:
                    build_text_old = cfg.cache_defaults.BUILDTEXT
                    build_old = cfg.cache_defaults.BUILD

                build_text = ver[cfg.indices.BUILDTEXT]
                build = ver[cfg.indices.BUILD]

                public_name = self.cdn_cache.CONFIG.PRODUCTS[branch]

                build_text = (
                    f"**{build_text}**" if build_text != build_text_old else build_text
                )
                build = f"**{build}**" if build != build_old else build

                encrypted = ":lock:" if ver["encrypted"] else ""

                value_string += f"`{public_name} ({branch})`{encrypted}: {build_text_old}.{build_old} --> {build_text}.{build}\n"

            if value_string == "":
                continue

            embed.add_field(
                name=cfg.strings.EMBED_UPDATE_TITLE, value=value_string, inline=False
            )

            all_embeds.append({"embed": embed, "target": target_channel, "game": game})

        return all_embeds

    def preprocess_update_data(self, data: list):
        embed_data = {}
        for branch in data:
            game = self.get_game_from_branch(branch["branch"])
            if not game:
                logger.warning(f"Game could not be determined for {branch['branch']}")
                continue

            if game not in embed_data:
                logger.debug("Adding new game to embed data...")
                embed_data[game] = []

            logger.debug("Adding branch data to existing game entry")
            embed_data[game].append(branch)

        logger.debug("EMBED DATA: ", embed_data)

        return embed_data

    async def distribute_embed(self, first_run: bool = False):
        """This handles distributing the generated embeds to the various servers that should receive them."""
        logger.info("Building CDN update embed...")
        new_data = await self.cdn_cache.fetch_cdn()

        token = secrets.token_urlsafe()

        if new_data and not dbg.debug_enabled and not first_run:
            # Send live notification to all appropriate guilds
            if type(new_data) == Exception:
                logger.error(new_data)
                await self.notify_owner_of_exception(new_data)
                return False

            logger.info("New CDN data found! Creating posts...")

            embed_data = self.preprocess_update_data(new_data)

            for guild in self.bot.guilds:
                try:
                    embeds = self.build_embeds(embed_data, guild.id)
                except Exception as exc:
                    logger.error(
                        f"Error distributing embed(s) for guild {guild.id}.",
                        exc_info=exc,
                    )
                    await self.notify_owner_of_exception(
                        f"Error distributing embed(s) for guild {guild.id}.\n{exc}"
                    )
                    continue

                if not embeds:
                    logger.error(
                        f"Embeds could not be built for guild {guild.id}, aborting."
                    )
                    continue

                for embed in embeds:
                    channel = await guild.fetch_channel(embed["target"])
                    actual_embed = embed["embed"]  # god save me

                    if actual_embed and channel:
                        logger.info("Sending CDN update post and tweet...")
                        message = await channel.send(embed=actual_embed)  # type: ignore

                        if channel.id == int(os.getenv("ANNOUNCEMENT_CHANNEL")):
                            await message.publish()

                        response = await self.twitter.send_tweet(
                            actual_embed.to_dict(), token
                        )
                        if response:
                            logger.error(
                                f"Tweet failed with: {response}.\n{actual_embed.to_dict()}"
                            )
                            await self.notify_owner_of_exception(response)
                    elif actual_embed and not channel:
                        logger.error(f"No channel found for guild {guild}, aborting.")
                        continue
                    elif not embed:
                        logger.error(f"No embed built for guild {guild}, aborting.")
                        continue
            return True
        else:
            if new_data:
                if dbg.debug_enabled or first_run:
                    # Debug notifcations, as well as absorbing the first update check if cache is outdated.
                    logger.info(
                        "New data found, but debug mode is active or it's the first run. Sending posts to debug channel."
                    )

                    if not dbg.debug_guild_id:
                        logger.error(
                            "Debug mode is enabled, but no debug guild ID is set. Aborting."
                        )
                        return False

                    embed_data = self.preprocess_update_data(new_data)
                    embeds = self.build_embeds(embed_data, dbg.debug_guild_id)  # type: ignore

                    if not embeds:
                        logger.error("No debug embeds built, aborting.")
                        return False

                    for embed in embeds:
                        actual_embed = embed["embed"]  # god save me
                        channel = await self.bot.fetch_channel(dbg.debug_channel_id_by_game[embed["game"]])  # type: ignore
                        if actual_embed:
                            logger.info("Sending debug CDN update...")
                            await channel.send(embed=actual_embed)  # type: ignore
                        else:
                            logger.error("No debug embed built, aborting.")
                            continue
            else:
                logger.info("No CDN changes found.")

    def get_game_from_branch(self, branch: str):
        if "wow" in branch:
            return "wow"
        elif "fenris" in branch:
            return "d4"
        else:
            return False

    def build_paginator_for_current_build_data(self):
        buttons = [
            pages.PaginatorButton(
                "first", label="<<-", style=discord.ButtonStyle.green
            ),
            pages.PaginatorButton("prev", label="<-", style=discord.ButtonStyle.green),
            pages.PaginatorButton(
                "page_indicator", style=discord.ButtonStyle.gray, disabled=True
            ),
            pages.PaginatorButton("next", label="->", style=discord.ButtonStyle.green),
            pages.PaginatorButton("last", label="->>", style=discord.ButtonStyle.green),
        ]

        data_pages = []

        for product in self.cdn_cache.CONFIG.PRODUCTS:
            data = self.cdn_cache.load_build_data(product.name)

            if not data:
                logger.warning(
                    f"No data found for product {product}, skipping paginator entry..."
                )
                continue

            lock = ":lock:" if data["encrypted"] else ""

            embed = discord.Embed(
                title=f"CDN Data for: {product}{lock}",
                color=discord.Color.blurple(),
            )

            data_text = f"**Region:** `{data['region']}`\n"
            data_text += f"**Build Config:** `{data['build_config']}`\n"
            data_text += f"**CDN Config:** `{data['cdn_config']}`\n"
            data_text += f"**Build:** `{data['build']}`\n"
            data_text += f"**Version:** `{data['build_text']}`\n"
            data_text += f"**Product Config:** `{data['product_config']}`\n"
            data_text += f"**Encrypted:** `{data['encrypted']}`"

            embed.add_field(name="Current Data", value=data_text, inline=False)

            data_pages.append(embed)

        paginator = pages.Paginator(
            pages=data_pages,
            show_indicator=True,
            use_default_buttons=False,
            custom_buttons=buttons,
            timeout=300,
        )

        return paginator

    @tasks.loop(minutes=FETCH_INTERVAL, reconnect=True)
    async def cdn_auto_refresh(self):
        """Forever problematic loop that handles auto-checking for CDN updates."""
        await self.bot.wait_until_ready()

        logger.info("Checking for CDN updates...")

        try:
            await self.distribute_embed(self.cdn_auto_refresh.current_loop == 0)
        except Exception as exc:
            logger.error("Error occurred when distributing embeds.", exc_info=exc)

            await self.notify_owner_of_exception(exc)
            return

        self.last_update = time.time()
        self.last_update_formatted = get_discord_timestamp(relative=True)

    # DISCORD LISTENERS

    @commands.Cog.listener(name="on_command_error")
    @commands.Cog.listener(name="on_application_command_error")
    async def handle_command_error(
        self, ctx: discord.ApplicationContext, exception: discord.DiscordException
    ):
        error_message = "I have encountered an error handling your command. The Titans have been notified."

        logger.error(
            f"Logging application command error in guild {ctx.guild_id}.",
            exc_info=exception,
        )

        await self.bot.notify_owner_of_command_exception(ctx, exception)  # type: ignore

        await ctx.interaction.response.send_message(
            error_message, ephemeral=True, delete_after=300
        )

    # DISCORD COMMANDS

    @bridge.bridge_command(name="cdndata")
    async def cdn_data(self, ctx: bridge.BridgeApplicationContext):
        """Returns a paginator with the currently cached CDN data."""
        logger.info("Generating paginator to display CDN data...")
        paginator = self.build_paginator_for_current_build_data()
        await paginator.respond(ctx.interaction, ephemeral=True)

    @bridge.bridge_command(name="cdnbranches")
    async def cdn_branches(self, ctx: bridge.BridgeApplicationContext):
        """Returns all observable branches."""
        message = f"## These are all the branches I can watch for you:\n```\n"
        for product in self.cdn_cache.CONFIG.PRODUCTS:
            message += f"{product.name} : {product}\n"

        message += "```"

        await ctx.interaction.response.send_message(
            message, ephemeral=True, delete_after=300
        )

    @bridge.bridge_command(
        name="cdnaddtowatchlist",
        default_member_permissions=discord.Permissions(administrator=True),
        guild_only=True,
    )
    async def cdn_add_to_watchlist(
        self, ctx: bridge.BridgeApplicationContext, branch: str
    ):
        """Add a branch to the watchlist. Add multiple branches by separating them with a comma."""
        branch = branch.lower()
        branch = branch.replace(" ", "")
        delimeter = ","
        if delimeter in branch:
            bad_branches = []
            good_branches = []
            branches = branch.split(delimeter)
            for branch in branches:
                if self.cdn_cache.CONFIG.is_valid_branch(branch) != True:
                    bad_branches.append(
                        branch + f" ({self.cdn_cache.CONFIG.errors.BRANCH_NOT_VALID})"
                    )
                    continue

                success, error = self.guild_cfg.add_to_guild_watchlist(ctx.guild_id, branch)  # type: ignore
                if success != True:
                    bad_branches.append(branch + f" ({error})")
                else:
                    good_branches.append(branch)

            if len(bad_branches) > 0:
                message = "The following branches were invalid:\n```\n"
                message += "\n".join(bad_branches)

                help_string = self.cdn_cache.CONFIG.errors.VIEW_VALID_BRANCHES
                cmdlink = self.get_command_link("cdnbranches")
                help_string = help_string.format(cmdlink=cmdlink)

                message += f"```\n\n{help_string}"

                if len(good_branches) > 0:
                    message += (
                        "\n\nThe following branches were added succesfully:\n```\n"
                    )
                    message += "\n".join(good_branches)
                    message += "```"

                await ctx.interaction.response.send_message(
                    message, ephemeral=True, delete_after=300
                )
                return False
            else:
                message = "The following branches were successfully added to the watchlist:\n```\n"
                message += "\n".join(good_branches)
                message += "```"
                await ctx.interaction.response.send_message(
                    message, ephemeral=True, delete_after=300
                )
                return True
        else:
            success, error = self.guild_cfg.add_to_guild_watchlist(ctx.guild_id, branch)  # type: ignore
            if success != True:
                message = f"{error}\n\n"

                help_string = self.cdn_cache.CONFIG.errors.VIEW_VALID_BRANCHES
                cmdlink = self.get_command_link("cdnbranches")
                help_string = help_string.format(cmdlink=cmdlink)

                message += help_string

                await ctx.interaction.response.send_message(
                    message, ephemeral=True, delete_after=300
                )
                return False

            await ctx.interaction.response.send_message(
                f"`{branch}` successfully added to watchlist.",
                ephemeral=True,
                delete_after=300,
            )

    @bridge.bridge_command(
        name="cdnremovefromwatchlist",
        default_member_permissions=discord.Permissions(administrator=True),
        guild_only=True,
    )
    async def cdn_remove_from_watchlist(
        self, ctx: bridge.BridgeApplicationContext, branch: str
    ):
        """Remove specific branches from this guild's watchlist."""
        success, error = self.guild_cfg.remove_from_guild_watchlist(ctx.guild_id, branch)  # type: ignore
        if success != True:
            message = f"{error}\n\n"

            help_string = self.cdn_cache.CONFIG.errors.VIEW_VALID_BRANCHES
            cmdlink = self.get_command_link("cdnbranches")
            help_string = help_string.format(cmdlink=cmdlink)

            message += help_string

            await ctx.interaction.response.send_message(
                message, ephemeral=True, delete_after=300
            )
            return False
        else:
            await ctx.interaction.response.send_message(
                f"`{branch}` successfully removed from watchlist.",
                ephemeral=True,
                delete_after=300,
            )

    @bridge.bridge_command(
        name="cdnwatchlist",
        guild_only=True,
    )
    async def cdn_watchlist(self, ctx: bridge.BridgeApplicationContext):
        """Returns the watchlist for your guild."""
        message = (
            "## These are the branches I'm currently observing for this guild:\n```\n"
        )

        watchlist = self.guild_cfg.get_guild_watchlist(ctx.guild_id)  # type: ignore

        for product in watchlist:
            product = SUPPORTED_PRODUCTS[product]
            message += f"{product.name} : {product}\n"

        message += "```"

        await ctx.interaction.response.send_message(
            message, ephemeral=True, delete_after=300
        )

    @bridge.bridge_command(
        name="cdnsetchannel",
        default_member_permissions=discord.Permissions(administrator=True),
        guild_only=True,
    )
    async def cdn_set_channel(
        self, ctx: bridge.BridgeApplicationContext, game: SUPPORTED_GAMES | None = None
    ):
        """Sets the current channel as the notification channel for the given game. Defaults to Warcraft."""
        channel = ctx.channel_id
        guild = ctx.guild_id

        game = game or SUPPORTED_GAMES.Warcraft

        self.guild_cfg.set_notification_channel(guild, channel, game)  # type: ignore

        await ctx.interaction.response.send_message(
            f"{game.name} notification channel set!",
            ephemeral=True,
            delete_after=300,
        )

    @bridge.bridge_command(
        name="cdngetchannel",
        guild_only=True,
    )
    async def cdn_get_channel(
        self, ctx: bridge.BridgeApplicationContext, game: SUPPORTED_GAMES | None = None
    ):
        """Returns the current notification channel for the given game. Defaults to Warcraft."""
        guild = ctx.guild_id
        game = game or SUPPORTED_GAMES.Warcraft
        channel = self.guild_cfg.get_notification_channel(guild, game)  # type: ignore

        if channel:
            await ctx.interaction.response.send_message(
                f"This server's {game.name} notification channel is set to <#{channel}>",
                ephemeral=True,
                delete_after=300,
            )
        else:
            await ctx.interaction.response.send_message(
                f"This server does not have a notification channel set, try `/cdnsetchannel` to set your notification channel!",
                ephemeral=True,
                delete_after=300,
            )

    @bridge.bridge_command(name="cdnlastupdate")
    async def cdn_last_update(self, ctx: bridge.BridgeApplicationContext):
        """Returns the last time the bot checked for an update."""
        await ctx.interaction.response.send_message(
            f"Last update: {self.last_update_formatted}.",
            ephemeral=True,
            delete_after=300,
        )

    @commands.is_owner()
    @bridge.bridge_command(
        name="cdnsetregion",
        default_member_permissions=discord.Permissions(administrator=True),
        guild_only=True,
    )
    async def cdn_set_region(self, ctx: bridge.BridgeApplicationContext, region: str):
        """Sets the region for your guild."""

        success, message = self.guild_cfg.set_region(ctx.guild_id, region)  # type: ignore

        if not success:
            valid_regions = "\n\nSupported Regions:```\n"
            for region in self.guild_cfg.CONFIG.SUPPORTED_REGIONS_STRING:
                valid_regions += f"{region}\n"
            valid_regions += "```"

            message += valid_regions

        await ctx.interaction.response.send_message(
            message, ephemeral=True, delete_after=300
        )

    @commands.is_owner()
    @bridge.bridge_command(
        name="cdngetregion",
        guild_only=True,
    )
    async def cdn_get_region(self, ctx: bridge.BridgeApplicationContext):
        """Returns the current region for your guild."""

        region = self.guild_cfg.get_region(ctx.guild_id)  # type: ignore

        message = f"This guild's region is: `{region}`."

        await ctx.interaction.response.send_message(
            message, ephemeral=True, delete_after=300
        )

    @commands.is_owner()
    @bridge.bridge_command(
        name="cdnsetlocale",
        default_member_permissions=discord.Permissions(administrator=True),
        guild_only=True,
    )
    async def cdn_set_locale(self, ctx: bridge.BridgeApplicationContext, locale: str):
        """Sets the locale for your guild."""

        success, message = self.guild_cfg.set_locale(ctx.guild_id, locale)  # type: ignore

        if not success:
            current_region = self.guild_cfg.get_region(ctx.guild_id)  # type: ignore
            supported_locales = self.guild_cfg.get_region_supported_locales(
                current_region
            )
            if not supported_locales:
                return

            help_string = f"\n\nSupported Locales for `{current_region}`: ```\n"
            for locale in supported_locales:
                help_string += f"{locale.value}\n"  # type: ignore
            help_string += "```"

            message += help_string

        await ctx.interaction.response.send_message(
            message, ephemeral=True, delete_after=300
        )

    @commands.is_owner()
    @bridge.bridge_command(
        name="cdngetlocale",
    )
    async def cdn_get_locale(self, ctx: bridge.BridgeApplicationContext):
        """Returns the current locale for your guild."""

        locale = self.guild_cfg.get_locale(ctx.guild_id)  # type: ignore

        message = f"This guild's locale is: `{locale}`."

        await ctx.interaction.response.send_message(
            message, ephemeral=True, delete_after=300
        )


def setup(bot):
    bot.add_cog(CDNCog(bot))
