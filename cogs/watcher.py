"""This is the module that handles watching the Blizzard CDN and posting updates to the correct places."""

import time
import httpx
import secrets
import discord
import logging

from typing import Optional, Union
from discord.ext import commands, pages, tasks

from cogs.bot import Algalon
from cogs.user_config import UserConfigFile
from cogs.guild_config import GuildCFG
from cogs.cdn_cache import CDNCache
from cogs.config import CommonStrings
from cogs.config import LiveConfig as livecfg
from cogs.config import WatcherConfig as cfg
from cogs.config import DebugConfig as dbg
from cogs.config import SUPPORTED_GAMES, SUPPORTED_PRODUCTS
from cogs.utils import get_discord_timestamp
from cogs.api.social import SocialPlatforms
from cogs.ui import WatchlistUI, WatchlistMenuType

START_LOOPS = livecfg.get_cfg_value("meta", "start_loops")

logger = logging.getLogger("discord.cdn.watcher")

DELIMITER = ","
FETCH_INTERVAL = livecfg.get_cfg_value("meta", "fetch_interval", 5)

ANNOUNCEMENT_CHANNELS = livecfg.get_cfg_value("discord", "announcement_channels")

DELETE_AFTER = livecfg.get_cfg_value("discord", "delete_msgs_after", 120)
COOLDOWN = livecfg.get_cfg_value("discord", "cmd_cooldown", 15)


class CDNCog(commands.Cog):
    """This is the actual Cog that gets added to the Discord bot."""

    def __init__(self, bot: Algalon):
        self.bot = bot
        self.cdn_cache = CDNCache()
        self.guild_cfg = GuildCFG()
        self.user_cfg = UserConfigFile()
        self.live_cfg = livecfg()
        self.socials = SocialPlatforms()
        self.last_update = 0
        self.last_update_formatted = ""

        if dbg.debug_enabled:
            logger.info("<- Starting bot in DEBUG mode ->")

        if START_LOOPS:
            self.cdn_auto_refresh.add_exception_type(httpx.ConnectTimeout)
            self.cdn_auto_refresh.start()
            self.integrity_check.start()

    @staticmethod
    def user_is_admin_or_owner(ctx: discord.ApplicationContext):
        if ctx.guild.owner_id == ctx.user.id:
            return True

        return ctx.user.top_role.permissions.administrator

    __ADMIN_CHECKS = [user_is_admin_or_owner]

    @tasks.loop(hours=24)
    async def integrity_check(self):
        await self.bot.wait_until_ready()

        logger.info("Running guild configuration integrity check...")

        for guild in self.bot.guilds:
            if not self.guild_cfg.does_guild_config_exist(guild.id):
                logger.debug(
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

        logger.info("Guild configuration integrity check complete")
        logger.info("Running cache configuration check...")

        for product in self.cdn_cache.CONFIG.PRODUCTS:
            if product.name not in self.cdn_cache.get_all_config_entries():
                logger.info(f"New product detected. Adding default entry for {product}")
                self.cdn_cache.set_default_entry(product.name)

        logger.info("Cache configuration check complete")

    def get_command_link(
        self, command: str, cmd_group: Optional[discord.SlashCommandGroup] = None
    ):
        if cmd_group is not None and isinstance(cmd_group, discord.SlashCommandGroup):
            all_cmds = cmd_group.subcommands
        else:
            all_cmds = self.get_commands()

        for cmd in all_cmds:
            if isinstance(cmd, discord.SlashCommand):
                if cmd.qualified_name == command:
                    return cmd.mention

        return f"`/{command}`"

    async def notify_owner_of_exception(
        self,
        error: Union[discord.ApplicationCommandError, str],
        ctx: Optional[discord.ApplicationContext] = None,
    ):
        """This is supposed to notify the owner of an error, but doesn't always work."""
        owner = await self.bot.fetch_user(self.bot.owner_id)  # type: ignore
        channel = await owner.create_dm()
        message = f"I've encountered an error! Help!\n```py\n{error}\n```\n"

        if ctx:
            message += f"CALLER: {ctx.author}\nGUILD: {ctx.guild.name} | {ctx.guild_id}"  # type: ignore

        await channel.send(message)

    def build_embeds(self, data: dict, guild_id: int):
        """This builds notification embeds with the given data."""

        guild_watchlist = self.guild_cfg.get_guild_watchlist(guild_id)

        product_config = self.live_cfg.get_all_products()

        all_embeds = []

        for game, update_data in data.items():
            target_channel = self.guild_cfg.get_notification_channel(guild_id, game)

            if not target_channel or target_channel == 0:
                logger.warning(
                    f"Guild {guild_id} has not chosen a notification channel, skipping..."
                )
                continue

            config = cfg.strings.EMBED_GAME_CONFIG[game]
            color = config["color"]

            embed = discord.Embed(
                color=color,
                title=config["title"],
                description=f"{get_discord_timestamp()} **|** {get_discord_timestamp(relative=True)}",
                url=config["url"],
            )

            embed.set_author(
                name=config["name"],
                icon_url=config["icon_url"],
            )

            algalon_version = self.live_cfg.get_cfg_value("meta", "version", "Dev")
            embed.set_footer(
                text=CommonStrings.EMBED_FOOTER.format(version=algalon_version)
            )

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

                public_name = product_config[branch]["public_name"]

                build_text = (
                    f"**{build_text}**" if build_text != build_text_old else build_text
                )
                build = f"**{build}**" if build != build_old else build

                branch_is_encrypted = product_config[branch]["encrypted"]
                encrypted = ":lock:" if branch_is_encrypted else ""

                value_string += f"`{public_name} ({branch})`{encrypted}: {build_text_old}.{build_old} --> {build_text}.{build}"

                # hack to add diff links
                if (
                    not branch_is_encrypted
                    and game == SUPPORTED_GAMES.Warcraft
                    and "old" in ver
                ):
                    url = cfg.strings.EMBED_WAGOTOOLS_DIFF_URL
                    old_build = f"{ver["old"][cfg.indices.BUILDTEXT]}.{ver["old"][cfg.indices.BUILD]}"
                    new_build = f"{ver[cfg.indices.BUILDTEXT]}.{ver[cfg.indices.BUILD]}"
                    value_string += (
                        f" | [Diffs]({url.format(old=old_build, new=new_build)})"
                    )

                value_string += "\n"

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
            game = cfg.get_game_from_branch(branch["branch"])
            if not game:
                logger.warning(f"Game could not be determined for {branch['branch']}")
                continue

            game = game.value

            if game not in embed_data:
                logger.debug("Adding new game to embed data...")
                embed_data[game] = []

            logger.debug("Adding branch data to game entry")
            embed_data[game].append(branch)

        return embed_data

    async def distribute_direct_messages(self, data: dict, owner_only: bool = False):
        with self.user_cfg as config:
            for game, updates in data.items():
                for update in updates:
                    branch = update["branch"]
                    subscribers = config.lookup.get_subscribers_for_branch(branch, True)
                    if subscribers is None or len(subscribers) == 0:
                        continue

                    new_build_text = update["build_text"]
                    if new_build_text != update["old"]["build_text"]:
                        new_build_text = f"**{new_build_text}**"

                    new_build_id = update["build"]
                    if new_build_id != update["old"]["build"]:
                        new_build_id = f"**{new_build_id}**"

                    message = f"{SUPPORTED_GAMES._value2member_map_[game].name} build: `{branch}` -> {new_build_text}.{new_build_id}"
                    # more hacks for diff links
                    if game == SUPPORTED_GAMES.Warcraft and "old" in update:
                        product_config = self.live_cfg.get_all_products()
                        encrypted = product_config[branch]["encrypted"]
                        if not encrypted:
                            url = cfg.strings.EMBED_WAGOTOOLS_DIFF_URL
                            old_build = f"{update["old"]["build_text"]}.{update["old"]["build"]}"
                            new_build = f"{update["build_text"]}.{update["build"]}"
                            message += f" | [Diffs](<{url.format(old=old_build, new=new_build)}>)"

                    for subscriber in subscribers:
                        user = await self.bot.get_or_fetch_user(subscriber)
                        is_owner = await self.bot.is_owner(user)
                        if owner_only and not is_owner:
                            continue

                        try:
                            channel = await user.create_dm()
                            await channel.send(message)
                        except:
                            logger.error(
                                f"Encountered an error when sending DM to {user.id}",
                                exc_info=True,
                            )

    async def distribute_embeds(self, first_run: bool = False):
        """This handles distributing the generated embeds to the various servers that should receive them."""
        new_data = await self.cdn_cache.fetch_cdn()

        token = secrets.token_urlsafe()

        if new_data and not dbg.debug_enabled and not first_run:
            # Send live notification to all appropriate guilds
            if type(new_data) == Exception:
                logger.error(
                    "Encountered an error while distributing embeds", exc_info=True
                )
                await self.notify_owner_of_exception(new_data)
                return False

            logger.info("New CDN version(s) found! Creating posts...")

            embed_data = self.preprocess_update_data(new_data)
            await self.distribute_direct_messages(embed_data)

            for guild in self.bot.guilds:
                try:
                    embeds = self.build_embeds(embed_data, guild.id)
                except Exception as exc:
                    logger.error(
                        f"Error distributing embed(s) for guild {guild.id}.",
                        exc_info=True,
                    )
                    await self.notify_owner_of_exception(
                        f"Error distributing embed(s) for guild {guild.id}.\n{exc}"
                    )
                    continue

                if not embeds:
                    logger.warning(
                        f"Embeds could not be built for guild {guild.id}, skipping..."
                    )
                    continue

                for embed in embeds:
                    try:
                        channel = await guild.fetch_channel(embed["target"])
                    except discord.NotFound:
                        logger.warning(f"Chosen channel not found for guild {guild}")
                        continue
                    except discord.Forbidden:
                        logger.warning(
                            f"No permission to access chosen channel for guild {guild}"
                        )
                        continue

                    actual_embed = embed["embed"]  # god save me

                    if actual_embed and channel:
                        logger.info("Sending CDN update post and tweet...")
                        try:
                            message = await channel.send(embed=actual_embed)  # type: ignore
                        except discord.NotFound:
                            logger.warning(
                                f"Chosen channel not found for guild {guild}"
                            )
                            continue
                        except discord.Forbidden:
                            logger.warning(
                                f"No permission to post to chosen channel for guild {guild}"
                            )
                            continue

                        if channel.id == ANNOUNCEMENT_CHANNELS["wow"]:
                            await message.publish()
                            try:
                                await self.socials.distribute_posts(
                                    actual_embed.to_dict(), token
                                )
                            except:
                                logger.error(
                                    "Encountered an error while distributing social media posts"
                                )
                        elif channel.id in ANNOUNCEMENT_CHANNELS.values():
                            await message.publish()
                    elif actual_embed and not channel:
                        logger.warning(f"No channel found for guild {guild}, aborting.")
                        continue
                    elif not embed:
                        logger.warning(f"No embed built for guild {guild}, aborting.")
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
                    await self.distribute_direct_messages(embed_data, True)

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

            encrypted = self.live_cfg.get_product_encryption_state(product.name)
            lock = ":lock:" if encrypted else ""

            embed = discord.Embed(
                title=f"CDN Data for: {product}{lock}",
                color=discord.Color.blurple(),
            )

            data_text = f"**Region:** `{data['region']}`\n"
            data_text += f"**Build Config:** `{data['build_config']}`\n"
            data_text += f"**CDN Config:** `{data['cdn_config']}`\n"
            data_text += f"**Build:** `{data['build']}`\n"
            data_text += f"**Version:** `{data['build_text']}`\n"
            data_text += f"**Product Config:** `{data['product_config'] if data['product_config'] != "" else "N/A"}`\n"
            data_text += f"**Encrypted:** `{encrypted}`"

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

        try:
            await self.distribute_embeds(self.cdn_auto_refresh.current_loop == 0)
            monitor = self.bot.get_cog("MonitorCog")
            await monitor.distribute_notifications()
        except Exception as exc:
            logger.critical("Error occurred when distributing embeds", exc_info=True)

            await self.notify_owner_of_exception(exc)
            return

        self.last_update = time.time()
        self.last_update_formatted = get_discord_timestamp(relative=True)

    # DISCORD LISTENERS

    @commands.Cog.listener(name="on_command_error")
    @commands.Cog.listener(name="on_application_command_error")
    async def handle_command_error(
        self,
        ctx: discord.ApplicationContext,
        exception: Union[
            commands.CommandOnCooldown,
            commands.NotOwner,
            discord.CheckFailure,
            discord.ApplicationCommandError,
        ],
    ):
        delete_after = DELETE_AFTER

        if isinstance(exception, commands.CommandOnCooldown):
            timestamp = get_discord_timestamp(
                round(time.time() + exception.retry_after), relative=True
            )
            message = f"This command is on cooldown. Try again {timestamp}"
            delete_after = int(exception.retry_after)
        elif isinstance(exception, commands.NotOwner) or isinstance(
            exception, discord.CheckFailure
        ):
            message = f"You do not have permission to use this command."
        else:
            message = "I have encountered an error handling your command. The Titans have been notified."
            logger.error(
                f"Logging application command error in guild {ctx.guild_id}.",
                exc_info=True,
            )
            await self.bot.notify_owner_of_command_exception(ctx, exception)  # type: ignore

        await ctx.respond(message, ephemeral=True, delete_after=delete_after)

    @commands.Cog.listener(name="on_unknown_application_command")
    async def handle_unk_command(self, ctx: discord.ApplicationContext):
        message = "Unknown command. Please try again in a few minutes."
        await ctx.respond(message, ephemeral=True, delete_after=DELETE_AFTER)

    # DISCORD COMMANDS

    @discord.slash_command(
        name="cdndata",
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
    async def cdn_data(self, ctx: discord.ApplicationContext):
        """Returns a paginator with the currently cached CDN data."""
        logger.debug("Generating paginator to display CDN data...")
        paginator = self.build_paginator_for_current_build_data()
        await paginator.respond(ctx.interaction, ephemeral=True)

    @discord.slash_command(
        name="branches",
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
    @commands.cooldown(1, COOLDOWN, commands.BucketType.user)
    async def cdn_branches(self, ctx: discord.ApplicationContext):
        """Returns all observable branches."""
        message = f"## These are all the branches I can watch for you:\n```\n"
        for product in self.cdn_cache.CONFIG.PRODUCTS:
            message += f"{product.name} : {product}\n"

        message += "```"

        await ctx.interaction.response.send_message(
            message, ephemeral=True, delete_after=DELETE_AFTER
        )

    watchlist_commands = discord.SlashCommandGroup(
        name="watchlist",
        description="Watchlist commands",
        contexts={discord.InteractionContextType.guild},
    )

    @watchlist_commands.command(
        name="add",
        checks=__ADMIN_CHECKS,
        input_type=str,
        min_length=3,
        max_length=500,
    )
    @commands.cooldown(1, COOLDOWN, commands.BucketType.guild)
    async def cdn_add_to_watchlist(self, ctx: discord.ApplicationContext, branch: str):
        """Add a branch to the watchlist. Add multiple branches by separating them with a comma."""
        branch = branch.lower()
        branch = branch.replace(" ", "")
        if DELIMITER in branch:
            bad_branches = []
            good_branches = []
            branches = branch.split(DELIMITER)
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
                cmdlink = self.get_command_link("branches")
                help_string = help_string.format(cmdlink=cmdlink)

                message += f"```\n\n{help_string}"

                if len(good_branches) > 0:
                    message += (
                        "\n\nThe following branches were added succesfully:\n```\n"
                    )
                    message += "\n".join(good_branches)
                    message += "```"

                await ctx.interaction.response.send_message(
                    message, ephemeral=True, delete_after=DELETE_AFTER
                )
                return False
            else:
                message = "The following branches were successfully added to the watchlist:\n```\n"
                message += "\n".join(good_branches)
                message += "```"
                await ctx.interaction.response.send_message(
                    message, ephemeral=True, delete_after=DELETE_AFTER
                )
                return True
        else:
            success, error = self.guild_cfg.add_to_guild_watchlist(ctx.guild_id, branch)  # type: ignore
            if success != True:
                message = f"{error}\n\n"

                help_string = self.cdn_cache.CONFIG.errors.VIEW_VALID_BRANCHES
                cmdlink = self.get_command_link("branches")
                help_string = help_string.format(cmdlink=cmdlink)

                message += help_string

                await ctx.interaction.response.send_message(
                    message, ephemeral=True, delete_after=DELETE_AFTER
                )
                return False

            await ctx.interaction.response.send_message(
                f"`{branch}` successfully added to watchlist.",
                ephemeral=True,
                delete_after=DELETE_AFTER,
            )

    @watchlist_commands.command(
        name="remove",
        checks=__ADMIN_CHECKS,
        input_type=str,
        min_length=3,
        max_length=500,
    )
    @commands.cooldown(1, COOLDOWN, commands.BucketType.guild)
    async def cdn_remove_from_watchlist(
        self, ctx: discord.ApplicationContext, branch: str
    ):
        """Remove specific branches from this guild's watchlist."""
        success, error = self.guild_cfg.remove_from_guild_watchlist(ctx.guild_id, branch)  # type: ignore
        if success != True:
            message = f"{error}\n\n"

            help_string = self.cdn_cache.CONFIG.errors.VIEW_VALID_BRANCHES
            cmdlink = self.get_command_link("branches")
            help_string = help_string.format(cmdlink=cmdlink)

            message += help_string

            await ctx.interaction.response.send_message(
                message, ephemeral=True, delete_after=DELETE_AFTER
            )
            return False
        else:
            await ctx.interaction.response.send_message(
                f"`{branch}` successfully removed from watchlist.",
                ephemeral=True,
                delete_after=DELETE_AFTER,
            )

    @watchlist_commands.command(name="view")
    @commands.cooldown(1, COOLDOWN, commands.BucketType.user)
    async def cdn_watchlist(self, ctx: discord.ApplicationContext):
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
            message, ephemeral=True, delete_after=DELETE_AFTER
        )

    @watchlist_commands.command(name="edit")
    @commands.cooldown(1, COOLDOWN, commands.BucketType.guild)
    async def cdn_edit_watchlist(
        self, ctx: discord.ApplicationContext, game: SUPPORTED_GAMES
    ):
        """Returns a graphical editor for your guild's watchlist"""

        if True:
            await ctx.respond(
                "The watchlist editor UI is currently disabled. Please try again later or use the `/watchlist add` and `/watchlist remove` commands to edit your watchlist.",
                ephemeral=True,
                delete_after=DELETE_AFTER,
            )
            return

        watchlist = self.guild_cfg.get_guild_watchlist(ctx.guild_id)
        menu = WatchlistUI.create_menu(watchlist, game, WatchlistMenuType.GUILD)
        if menu is None:
            await ctx.respond(
                "An error occurred while generating the watchlist editor.",
                ephemeral=True,
                delete_after=DELETE_AFTER,
            )
            return

        message = f"""# {game.name} Watchlist Editor
Changes are saved when you click out of the menu.
"""

        await ctx.respond(message, view=menu, ephemeral=True, delete_after=DELETE_AFTER)

    channel_commands = discord.SlashCommandGroup(
        name="channel",
        description="Notification channel commands",
        contexts={discord.InteractionContextType.guild},
    )

    @channel_commands.command(
        name="set",
        checks=__ADMIN_CHECKS,
    )
    @commands.cooldown(1, COOLDOWN, commands.BucketType.guild)
    async def cdn_set_channel(
        self,
        ctx: discord.ApplicationContext,
        game: Optional[SUPPORTED_GAMES] = SUPPORTED_GAMES.Warcraft,
    ):
        """Sets the current channel as the notification channel for the given game. Defaults to Warcraft."""
        channel = ctx.channel_id
        guild = ctx.guild_id

        self.guild_cfg.set_notification_channel(guild, channel, game)  # type: ignore

        await ctx.interaction.response.send_message(
            f"{game.name} notification channel set!",
            ephemeral=True,
            delete_after=DELETE_AFTER,
        )

    @channel_commands.command(name="get")
    @commands.cooldown(1, COOLDOWN, commands.BucketType.user)
    async def cdn_get_channel(
        self,
        ctx: discord.ApplicationContext,
        game: Optional[SUPPORTED_GAMES] = SUPPORTED_GAMES.Warcraft,
    ):
        """Returns the current notification channel for the given game. Defaults to Warcraft."""
        guild = ctx.guild_id
        channel = self.guild_cfg.get_notification_channel(guild, game)  # type: ignore

        if channel:
            await ctx.interaction.response.send_message(
                f"This server's {game.name} notification channel is set to <#{channel}>",
                ephemeral=True,
                delete_after=DELETE_AFTER,
            )
        else:
            cmdlink = self.get_command_link("set", self.channel_commands)
            await ctx.interaction.response.send_message(
                f"This server does not have a notification channel set, try {cmdlink} to set your notification channel!",
                ephemeral=True,
                delete_after=DELETE_AFTER,
            )

    @discord.slash_command(name="lastupdate")
    @commands.cooldown(1, COOLDOWN, commands.BucketType.user)
    async def cdn_last_update(self, ctx: discord.ApplicationContext):
        """Returns the last time the bot checked for an update."""
        await ctx.interaction.response.send_message(
            f"Last update: {self.last_update_formatted}.",
            ephemeral=True,
            delete_after=DELETE_AFTER,
        )

    dm_commands = discord.SlashCommandGroup(
        name="dm",
        description="DM notification commands",
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

    @dm_commands.command(
        name="subscribe",
        input_type=str,
        min_length=3,
        max_length=500,
    )
    @commands.cooldown(1, COOLDOWN, commands.BucketType.user)
    async def user_subscribe(self, ctx: discord.ApplicationContext, branch: str):
        """Subscribe to build updates via DM for the given branch."""

        message = ""
        user_id = ctx.author.id
        branch = branch.lower()
        with self.user_cfg as config:
            if DELIMITER in branch:  # batch adding
                branches = branch.split(",")
                message = "Successfully subscribed to the following branches:\n```diff"
                for _branch in branches:
                    success, result = config.subscribe(user_id, _branch)
                    if not success:
                        message += f"\n- ERROR > {_branch}: {result}"
                    else:
                        message += f"\n+ {_branch} added successfully."

                message += "```"
                await ctx.interaction.response.send_message(
                    message, ephemeral=True, delete_after=DELETE_AFTER
                )
            else:  # single adding
                success, result = config.subscribe(user_id, branch)
                if not success:
                    message = f"Unable to subscribe to branch `{branch}`: `{result}`"
                else:
                    message = f"Successfully subscribed to branch `{branch}`!"

                await ctx.interaction.response.send_message(
                    message, ephemeral=True, delete_after=DELETE_AFTER
                )

    @dm_commands.command(
        name="unsubscribe",
        input_type=str,
        min_length=3,
        max_length=500,
    )
    @commands.cooldown(1, COOLDOWN, commands.BucketType.user)
    async def user_unsubscribe(self, ctx: discord.ApplicationContext, branch: str):
        """Unsubscribe from build updates via DM for the given branch."""

        message = ""
        user_id = ctx.author.id
        branch = branch.lower()
        with self.user_cfg as config:
            if DELIMITER in branch:  # batch removal
                branches = branch.split(",")
                message = "No longer watching the following branches:\n```diff"
                for _branch in branches:
                    success, result = config.unsubscribe(user_id, _branch)
                    if not success:
                        message += f"\n+ ERROR > {_branch}: {result}"
                    else:
                        message += f"\n- {_branch} successfully removed."

                message += "```"
                await ctx.interaction.response.send_message(
                    message, ephemeral=True, delete_after=DELETE_AFTER
                )
            else:  # single removal
                success, result = config.unsubscribe(user_id, branch)
                if not success:
                    message = (
                        f"Unable to unsubscribe from branch `{branch}`: `{result}`"
                    )
                else:
                    message = f"Successfully unsubscribed from branch `{branch}`!"

                await ctx.interaction.response.send_message(
                    message, ephemeral=True, delete_after=DELETE_AFTER
                )

    @dm_commands.command(name="edit")
    @commands.cooldown(1, COOLDOWN, commands.BucketType.user)
    async def user_edit_subscribed(
        self, ctx: discord.ApplicationContext, game: SUPPORTED_GAMES
    ):
        """Returns a graphical editor for your personal watchlist."""
        if not SUPPORTED_GAMES.has_key[game]:
            await ctx.respond(
                f"Game `{game}` is not supported.",
                ephemeral=True,
                delete_after=DELETE_AFTER,
            )
            return

        with self.user_cfg as config:
            watchlist = config.get_watchlist(ctx.author.id)

        menu = WatchlistUI.create_menu(watchlist, game, WatchlistMenuType.USER)
        if menu is None:
            await ctx.respond(
                "An error occurred while generating the watchlist editor.",
                ephemeral=True,
                delete_after=DELETE_AFTER,
            )
            return

        message = f"""# {game.name} Watchlist Editor
Changes are saved when you click out of the menu.
"""

        await ctx.respond(message, view=menu, ephemeral=True, delete_after=DELETE_AFTER)

    @dm_commands.command(name="view")
    @commands.cooldown(1, COOLDOWN, commands.BucketType.user)
    async def user_subscribed(self, ctx: discord.ApplicationContext):
        """View all branches you're receiving DM updates for."""
        user_id = ctx.author.id
        with self.user_cfg as config:
            watchlist = config.get_watchlist(user_id)

        if watchlist is None or len(watchlist) == 0:
            cmdlink = self.get_command_link("subscribe")
            message = f"You are not currently subscribed to any branches. Subscribe to a branch using {cmdlink}."
        else:
            products = self.live_cfg.get_all_products()
            message = (
                "Here's a list of all branches you're receiving DM updates for:\n```"
            )
            for branch in watchlist:
                message += f"\n{branch} : {products[branch]['public_name']}"

            message += "```"

        await ctx.interaction.response.send_message(
            message, ephemeral=True, delete_after=DELETE_AFTER
        )


def setup(bot: discord.Bot):
    bot.add_cog(CDNCog(bot))
