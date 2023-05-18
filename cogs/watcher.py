"""This is the module that handles watching the Blizzard CDN and posting updates to the correct places."""

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

        for guild_id in self.guild_cfg.get_all_guild_configs():
            for key in self.guild_cfg.CONFIG.settings.KEYS:
                self.guild_cfg.get_guild_setting(guild_id, key)

            if int(guild_id) not in [guild.id for guild in self.bot.guilds]:
                logger.info(
                    f"No longer a part of guild {guild_id}, removing guild configuration..."
                )
                self.guild_cfg.remove_guild_config(guild_id)

        logger.info("Running cache configuration check...")

        for product in self.cdn_cache.CONFIG.PRODUCTS.keys():
            if product not in self.cdn_cache.get_all_config_entries():
                logger.info(f"New product detected. Adding default entry for {product}")
                self.cdn_cache.set_default_entry(product)

    async def notify_owner_of_exception(
        self,
        error,
        ctx: discord.ApplicationContext | bridge.BridgeApplicationContext | None = None,
    ):
        """This is supposed to notify the owner of an error, but doesn't always work."""
        owner = await self.bot.fetch_user(self.bot.owner_id)  # type: ignore
        channel = await owner.create_dm()

        message = f"I've encountered an error! Help!\n```py\n{error}\n```\n"

        if ctx:
            message += f"CALLER: {ctx.author}\nGUILD: {ctx.guild.name} | {ctx.guild_id}"  # type: ignore

        await channel.send(message)

    def build_embed(self, data: dict, guild_id: int):
        """This builds a notification embed with the given data."""

        guild_watchlist = self.guild_cfg.get_guild_watchlist(guild_id)

        embed = discord.Embed(
            color=discord.Color.blue(),
            title=cfg.strings.EMBED_WAGOTOOLS_TITLE,
            description=f"{get_discord_timestamp()} **|** {get_discord_timestamp(relative=True)}",
            url=cfg.strings.EMBED_WAGOTOOLS_URL,
        )

        embed.set_author(
            name=cfg.strings.EMBED_NAME,
            icon_url=cfg.strings.EMBED_ICON_URL,
        )

        embed.set_footer(text=CommonStrings.EMBED_FOOTER)

        value_string = ""

        for ver in data:
            branch = ver["branch"]

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
            return False

        embed.add_field(
            name=cfg.strings.EMBED_UPDATE_TITLE, value=value_string, inline=False
        )

        return embed

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

            for guild in self.bot.guilds:
                try:
                    channel_id = self.guild_cfg.get_notification_channel(guild.id)

                    if channel_id:
                        cdn_channel = await guild.fetch_channel(channel_id)
                    else:
                        logger.info(
                            f"Guild {guild.id} has not chosen a notification channel, skipping..."
                        )
                        raise Exception("Channel not found.")
                except Exception as exc:
                    logger.error(
                        "Error fetching channel for guild %s.", guild.id, exc_info=exc
                    )
                    continue

                embed = self.build_embed(new_data, guild.id)  # type: ignore
                if embed and cdn_channel:
                    logger.info("Sending CDN update post and tweet...")
                    await cdn_channel.send(embed=embed)  # type: ignore
                    response = await self.twitter.send_tweet(embed.to_dict(), token)
                    if response:
                        logger.info(
                            f"Tweet failed with: {response}.\n{embed.to_dict()}"
                        )
                        await self.notify_owner_of_exception(response)

                elif embed and not cdn_channel:
                    logger.warning(f"No channel found for guild {guild}, aborting.")
                    continue
                elif not embed:
                    logger.error(f"No embed built for guild {guild}, aborting.")
                    continue
        else:
            if new_data:
                if dbg.debug_enabled or first_run:
                    # Debug notifcations, as well as absorbing the first update check if cache is outdated.
                    logger.info(
                        "New data found, but debug mode is active or it's the first run. Sending post to debug channel."
                    )

                    channel = await self.bot.fetch_channel(dbg.debug_channel_id)  # type: ignore
                    embed = self.build_embed(new_data, dbg.debug_guild_id)  # type: ignore
                    if embed:
                        await channel.send(embed=embed)  # type: ignore
                    else:
                        logger.error("No embed built, aborting.")
            else:
                logger.info("No CDN changes found.")

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

        for product, name in self.cdn_cache.CONFIG.PRODUCTS.items():
            data = self.cdn_cache.load_build_data(product)

            if not data:
                continue

            lock = ":lock:" if data["encrypted"] else ""

            embed = discord.Embed(
                title=f"CDN Data for: {name}{lock}", color=discord.Color.blurple()
            )

            data_text = f"**Region:** `{data['region']}`\n"
            data_text += f"**Build Config:** `{data['build_config']}`\n"
            data_text += f"**CDN Config:** `{data['cdn_config']}`\n"
            data_text += f"**Build:** `{data['build']}`\n"
            data_text += f"**Version:** `{data['build_text']}`\n"
            data_text += f"**Product Config:** `{data['product_config']}`"
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

    @commands.Cog.listener(name="on_application_command_error")
    async def handle_command_error(
        self, ctx: discord.ApplicationContext, exception: discord.DiscordException
    ):
        error_message = "I have encountered an error handling your command. The Titans have been notified."

        logger.error(
            f"Logging application command error in guild {ctx.guild_id}.",
            exc_info=exception,
        )

        await self.notify_owner_of_exception(exception, ctx)

        await ctx.interaction.response.send_message(
            error_message, ephemeral=True, delete_after=300
        )

    @commands.Cog.listener("on_guild_join")
    async def on_guild_join(self, guild: discord.Guild):
        logger.info(f"Joined new guild {guild.id}!")
        self.guild_cfg.add_guild_config(guild.id)

    # DISCORD COMMANDS

    @bridge.bridge_command(name="cdncurrentdata")
    async def cdn_current_data(self, ctx: bridge.BridgeApplicationContext):
        logger.info("Generating paginator to display current build data.")
        paginator = self.build_paginator_for_current_build_data()
        await paginator.respond(ctx.interaction, ephemeral=True)

    @bridge.bridge_command(
        name="cdnaddtowatchlist",
        default_member_permissions=discord.Permissions(administrator=True),
    )
    async def cdn_add_to_watchlist(
        self, ctx: bridge.BridgeApplicationContext, branch: str
    ):
        """Command for adding specific branches to the watchlist for your guild."""
        added = self.guild_cfg.add_to_guild_watchlist(ctx.guild_id, branch)  # type: ignore
        if added != True:
            message = f"{added}\n\n**Valid branches:**\n```\n"

            for product, name in self.cdn_cache.CONFIG.PRODUCTS.items():
                message += f"{product} : {name}\n"

            message += "```"

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
    )
    @commands.has_permissions(administrator=True)
    async def cdn_remove_from_watchlist(
        self, ctx: bridge.BridgeApplicationContext, branch: str
    ):
        """Command for removing specific branches from the watchlist for you guild."""
        try:
            self.guild_cfg.remove_from_guild_watchlist(ctx.guild_id, branch)  # type: ignore
        except ValueError:
            message = "Invalid branch argument, please try again.\n\n**Valid branches:**\n```\n"

            for product in self.cdn_cache.CONFIG.PRODUCTS.keys():
                message += f"{product}\n"

            message += "```"

            await ctx.interaction.response.send_message(
                message, ephemeral=True, delete_after=300
            )
            return False

        await ctx.interaction.response.send_message(
            f"`{branch}` successfully removed from watchlist.",
            ephemeral=True,
            delete_after=300,
        )

    @bridge.bridge_command(name="cdnwatchlist")
    async def cdn_watchlist(self, ctx: bridge.BridgeApplicationContext):
        """Returns the entire watchlist for your guild."""
        message = (
            "**These are the branches I'm currently observing for this guild:**\n```\n"
        )

        watchlist = self.guild_cfg.get_guild_watchlist(ctx.guild_id)  # type: ignore

        for product in watchlist:
            message += f"{product}\n"

        message += "```"

        await ctx.interaction.response.send_message(
            message, ephemeral=True, delete_after=300
        )

    # FIXME: This command will be a pain to fix so I'm just deleting it for now
    # @bridge.bridge_command(
    #    name="cdnedit",
    #    default_member_permissions=discord.Permissions(administrator=True),
    # )
    # async def cdn_edit(self, ctx: bridge.BridgeApplicationContext):
    #    """Returns a graphical editor for your guilds watchlist."""
    #    view = CDNUi(ctx=ctx, guild_cfg=self.guild_cfg)
    #    message = "Edit the branches you are currently watching using the menu below.\nTo save your changes, just click out of the menu."

    #    await ctx.interaction.response.send_message(
    #        message, view=view, ephemeral=True, delete_after=300
    #    )

    @bridge.bridge_command(
        name="cdnsetchannel",
        default_member_permissions=discord.Permissions(administrator=True),
    )
    async def cdn_set_channel(self, ctx: bridge.BridgeApplicationContext):
        """Sets the notification channel for your guild."""
        channel = ctx.channel_id
        guild = ctx.guild_id

        self.guild_cfg.set_notification_channel(guild, channel)  # type: ignore

        await ctx.interaction.response.send_message(
            "Notification channel set!", ephemeral=True, delete_after=300
        )

    @bridge.bridge_command(name="cdngetchannel")
    async def cdn_get_channel(self, ctx: bridge.BridgeApplicationContext):
        """Returns the current notification channel for your guild."""
        guild = ctx.guild_id

        channel = self.guild_cfg.get_notification_channel(guild)  # type: ignore

        if channel:
            await ctx.interaction.response.send_message(
                f"This server's notification channel is set to <#{channel}>",
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

    @bridge.bridge_command(
        name="cdnsetregion",
        default_member_permissions=discord.Permissions(administrator=True),
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

    @bridge.bridge_command(
        name="cdngetregion",
    )
    async def cdn_get_region(self, ctx: bridge.BridgeApplicationContext):
        """Returns the current region for your guild."""

        region = self.guild_cfg.get_region(ctx.guild_id)  # type: ignore

        message = f"This guild's region is: `{region}`."

        await ctx.interaction.response.send_message(
            message, ephemeral=True, delete_after=300
        )

    @bridge.bridge_command(
        name="cdnsetlocale",
        default_member_permissions=discord.Permissions(administrator=True),
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
