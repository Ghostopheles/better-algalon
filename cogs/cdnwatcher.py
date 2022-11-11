import discord.ui as ui
import discord
import logging
import httpx
import time
import json
import sys
import os

from discord.ext import bridge, commands, tasks

START_LOOPS = True

FETCH_INTERVAL = 5

logger = logging.getLogger("discord.cdnwatcher")

class CDNUi(ui.View):
    def __init__(self, ctx:bridge.BridgeApplicationContext | bridge.BridgeContext=None, watcher=None, utility=False):
        super().__init__()
        self.watcher = watcher
        self.ctx = ctx
        self.utility = utility
        self.guild_id = self.ctx.guild_id

        if self.utility != True:
            self.create_select_menu()

    def create_select_menu(self):
        placeholder = "Edit watchlist..."
        min_values = 0
        max_values = len(self.watcher.PRODUCTS)
        options = []
        disabled = False

        for branch, name in self.watcher.PRODUCTS.items():
            default = branch in self.watcher.watchlist[str(self.guild_id)]

            option = discord.SelectOption(label=name, value=branch, default=default)
            options.append(option)

        branch_select_menu = ui.Select(
            placeholder=placeholder,
            min_values=min_values,
            max_values=max_values,
            options=options,
            disabled=disabled,
        )
        self.branch_menu = branch_select_menu

        async def update_watchlist(interaction: discord.Interaction):
            selected_branches = branch_select_menu.values

            for value in self.watcher.PRODUCTS.keys():
                if value in selected_branches and value not in self.watcher.watchlist[str(self.guild_id)]:
                    self.watcher.add_to_watchlist(value)
                elif value in self.watcher.watchlist[str(self.guild_id)] and value not in selected_branches:
                    self.watcher.remove_from_watchlist(value)
            
            await interaction.response.defer()

            return True

        branch_select_menu.callback = update_watchlist
        self.add_item(branch_select_menu)


class CDNWatcher():
    SELF_PATH = os.path.dirname(os.path.realpath(__file__))
    CDN_URL = "http://us.patch.battle.net:1119/"
    PRODUCTS = {
        "wow": "Retail",
        "wowt": "Retail PTR",
        "wow_beta": "Beta",
        "wow_classic": "WotLK Classic",
        "wow_classic_ptr": "WotLK Classic PTR",
        "wow_classic_beta": "Classic Beta",
        "wow_classic_era": "Classic Era",
        "wow_classic_era_ptr": "Classic Era PTR",
        "wowz": "Submission",
        "wowlivetest": "Live Test",
        "wowdev": "Internal"
    }
    PLATFORM = sys.platform
    
    def __init__(self):
        self.cache_path = os.path.join(self.SELF_PATH, "cache")
        self.data_path = os.path.join(self.cache_path, "cdn.json")

        load_watchlist = True

        if not os.path.exists(self.cache_path):
            os.mkdir(self.cache_path)
            self.init_json()
        
        if load_watchlist:
            self.watchlist, self.channels = self.load_watchlist()
            self.save_watchlist()
        else:
            self.watchlist = ["wow", "wowt", "wow_beta"]
            self.save_watchlist()

    def init_json(self):
        with open(self.data_path, "w") as file:
            template = {
                "buildInfo": {},
                "watchlist": {857764832542851092: ["wow", "wowt", "wow_beta"]},
                "last_updated_by": self.PLATFORM,
                "last_updated_at": time.time()
            }

            json.dump(template, file, indent=4)

    def init_watchlist(self, key:int):
        self.add_to_watchlist("wow", key)

    def add_to_watchlist(self, branch:str, guild_id:int):
        if branch not in self.PRODUCTS.keys():
            return "Branch is not a valid product"
        else:
            if guild_id in self.watchlist.keys():
                if branch in self.watchlist[guild_id]:
                    return "Branch is already on the watchlist"
                else:
                    self.watchlist[guild_id].append(branch)
                    self.save_watchlist()
                    return True
            else:
                self.watchlist[guild_id] = [branch]
                self.save_watchlist()
                return True
    
    def remove_from_watchlist(self, branch:str, guild_id:int):
        if guild_id in self.watchlist.keys():
            if branch not in self.watchlist[guild_id]:
                raise ValueError("Argument 'branch' is not on the watchlist.")
            else:
                self.watchlist.remove(branch)
                self.save_watchlist()
        else:
            return False

    def load_watchlist(self):
        logger.debug("Loading existing watchlist from file...")
        with open(self.data_path, "r") as file:
            f = json.load(file)
            if not "last_updated_by" in f:
                f["last_updated_by"] = self.PLATFORM

            if not "last_updated_at" in f:
                f["last_updated_at"] = time.time()

            if not "channels" in f:
                f["channels"] = {}

            return f["watchlist"], f["channels"]

    def save_watchlist(self):
        logger.info("Saving configuration...")
        
        with open(self.data_path, "r+") as file:
            f = json.load(file)
            f["watchlist"] = self.watchlist
            f["channels"] = self.channels
            f["last_updated_by"] = self.PLATFORM
            f["last_updated_at"] = time.time()

            file.seek(0)
            json.dump(f, file, indent=4)
            file.truncate()

    def set_channel(self, channel_id:int, guild_id:int):
        logger.info(f"Setting notification channel for {guild_id} to {channel_id}.")
        self.channels[str(guild_id)] = channel_id
        self.save_watchlist()

    def get_channel(self, guild_id:int):
        logger.info(f"Getting notification channel for {guild_id}.")
        if str(guild_id) in self.channels.keys():
            return self.channels[str(guild_id)]
        else:
            return False

    def compare_builds(self, branch:str, newBuild:dict) -> bool:
        """
        Compares two build strings.

        Returns `True` if the build is new, else `False`.
        """
        with open(self.data_path, "r") as file:
            f = json.load(file)

            if f["last_updated_by"] != self.PLATFORM and (time.time() - f["last_updated_at"]) < (FETCH_INTERVAL* 60):
                logger.info("Skipping build comparison, data is outdated")
                return False

            if branch in f["buildInfo"]:
                if f["buildInfo"][branch] != newBuild:
                    return True
                else:
                    return False
            else:
                f["buildInfo"][branch] = newBuild
                return True

    def save_build_data(self, branch:str, data:dict):
        with open(self.data_path, "r+") as file:
            f = json.load(file)
            f["buildInfo"][branch] = data

            file.seek(0)
            json.dump(f, file, indent=4)
            file.truncate()

    def load_build_data(self, branch:str):
        with open(self.data_path, "r") as file:
            f = json.load(file)
            if branch in f["buildInfo"]:
                return f["buildInfo"][branch]
            else:
                f["buildInfo"][branch] = {
                    "region": "us",
                    "build": "",
                    "build_text": "untracked"
                }
                return False

    async def fetch_cdn(self):
        logger.debug("Fetching CDN data...")
        async with httpx.AsyncClient() as client:
            new_data = []
            for branch in self.PRODUCTS:
                try:
                    logger.debug(f"Grabbing data for branch: {branch}")
                    url = self.CDN_URL + branch + "/versions"

                    res = await client.get(url)
                    logger.debug(f"Parsing CDN response")
                    data = self.parse_response(res.text)

                    if data:
                        logger.debug(f"Comparing build data for {branch}")
                        is_new = self.compare_builds(branch, data)

                        if is_new:
                            output_data = data.copy()

                            old_data = self.load_build_data(branch)

                            if old_data:
                                output_data["old"] = old_data
                            
                            output_data["branch"] = branch
                            new_data.append(output_data)

                        logger.debug(f"Saving build data for {branch}")
                        self.save_build_data(branch, data)
                    else:
                        return False
                except httpx.ReadTimeout as exc:
                    logger.error(f"Timeout error during CDN check for {branch}")
                    return exc

            return new_data

    def parse_response(self, response:str) -> dict:
        try:
            data = response.split("\n")[2].split("|")
            region = data[0]
            build_number = data[4]
            build_text = data[5].replace(build_number, "")[:-1]

            output = {
                "region": region,
                "build": build_number,
                "build_text": build_text
            }

            return output
        except IndexError as exc:
            logger.error("Encountered an error parsing API response...")
            logger.error(exc)

            return False


class CDNCogWatcher(commands.Cog):
    def __init__(self, bot:bridge.Bot):
        self.bot = bot
        self.cdn_watcher = CDNWatcher()
        self.last_updated = 0

        if START_LOOPS:
            self.cdn_auto_refresh.start()

    async def notify_owner_of_exception(self, error):
        owner = await self.bot.fetch_user(self.bot.owner_id)
        chan = await owner.create_dm()

        message = f"I've encountered an error! Help!\n{error}"

        await chan.send(message)

    def get_date(self, relative=False):
        current_time = int(time.time())
        if relative:
            return f"<t:{current_time}:R>"
        else:
            return f"<t:{current_time}:f>"

    def build_embed(self, data:dict, guild_id:int):
        embed = discord.Embed(
                color=discord.Color.blue(),
                title="wow.tools builds page",
                description=f"{self.get_date()} **|** {self.get_date(relative=True)}",
                url="https://wow.tools/builds/"
            )

        embed.set_author(
                name="Blizzard CDN Update",
                icon_url="https://bnetcmsus-a.akamaihd.net/cms/gallery/D2TTHKAPW9BH1534981363136.png"
            )

        embed.set_footer(text="Data provided by the prestigious Algalon 2.0.")

        
        value_string = ""

        for ver in data:
            branch = ver["branch"]

            if str(guild_id) not in self.cdn_watcher.watchlist.keys():
                logger.error(f"Guild ({guild_id}) not on watchlist, adding default entry [\"wow\"].")
                self.cdn_watcher.init_watchlist(guild_id)
                return False

            if branch not in self.cdn_watcher.watchlist[str(guild_id)]:
                continue

            if "old" in ver:
                build_text_old = ver["old"]["build_text"]
                build_old = ver["old"]["build"]
            else:
                build_text_old = "untracked"
                build_old = "0.0.0"
            
            build_text = ver["build_text"]
            build = ver["build"]

            public_name = self.cdn_watcher.PRODUCTS[branch]

            build_text = f"**{build_text}**" if build_text != build_text_old else build_text
            build = f"**{build}**" if build != build_old else build

            value_string += f'`{public_name} ({branch})`: {build_text_old}.{build_old} --> {build_text}.{build}\n'

        if value_string == "":
            return False

        embed.add_field(
            name="Branch Updates",
            value=value_string,
            inline=False
        )

        return embed

    async def distribute_embed(self):
        logger.debug("Building CDN update embed")
        new_data = await self.cdn_watcher.fetch_cdn()

        if new_data:
            if isinstance(new_data, httpx.ReadTimeout):
                logger.error(new_data)
                self.notify_owner_of_exception(new_data)
                return False
            
            logger.info("New CDN data found! Creating posts...")

            for guild in self.bot.guilds:
                try:
                    if str(guild.id) in self.cdn_watcher.channels.keys():
                        cdn_channel = await guild.fetch_channel(self.cdn_watcher.channels[str(guild.id)])
                    else:
                        logger.error(f"Guild {guild.id} has not chosen a channel for notifications, skipping...")
                except:
                    logger.error(f"Error fetching channel for guild {guild.id}.")
                    continue

                embed = self.build_embed(new_data, guild.id)

                if embed:
                    await cdn_channel.send(embed=embed)

        else:
            logger.info("No CDN changes found.")

    @tasks.loop(minutes=FETCH_INTERVAL, reconnect=True)
    async def cdn_auto_refresh(self):
        await self.bot.wait_until_ready()

        logger.info("Checking for CDN updates...")

        await self.distribute_embed()
            
        self.last_updated = time.time()

    async def cdn_refresh(self, ctx:bridge.BridgeApplicationContext | bridge.BridgeContext):
        new_data = await self.distribute_embed(True)

        if new_data:
            await ctx.interaction.response.send_message(embed=new_data)
        else:
            await ctx.interaction.response.send_message("No changes found.", ephemeral=True, delete_after=300)

    @bridge.bridge_command(name="cdnaddtowatchlist")
    @commands.has_permissions(administrator=True)
    async def cdn_add_to_watchlist(self, ctx:bridge.BridgeApplicationContext | bridge.BridgeContext, branch:str):
        added = self.cdn_watcher.add_to_watchlist(branch, ctx.guild_id)
        if added != True:
            message = f"{added}\n\n**Valid branches:**\n```\n"

            for product, name in self.cdn_watcher.PRODUCTS.items():
                message += f"{product} : {name}\n"

            message += "```"

            await ctx.interaction.response.send_message(message, ephemeral=True, delete_after=300)
            return False
            
        await ctx.interaction.response.send_message(f"`{branch}` successfully added to watchlist.", ephemeral=True, delete_after=300)

    @bridge.bridge_command(name="cdnremovefromwatchlist")
    @commands.has_permissions(administrator=True)
    async def cdn_remove_from_watchlist(self, ctx:bridge.BridgeApplicationContext | bridge.BridgeContext, branch:str):
        try:
            self.cdn_watcher.remove_from_watchlist(branch, ctx.guild_id)
        except ValueError:
            message = "Invalid branch argument, please try again.\n\n**Valid branches:**\n```\n"

            for product in self.cdn_watcher.watchlist:
                message += f"{product}\n"

            message += "```"

            await ctx.interaction.response.send_message(message, ephemeral=True, delete_after=300)
            return False
            
        await ctx.interaction.response.send_message(f"`{branch}` successfully removed from watchlist.", ephemeral=True, delete_after=300)
        
    @bridge.bridge_command(name="cdnwatchlist")
    @commands.has_permissions(administrator=True)
    async def cdn_watchlist(self, ctx:bridge.BridgeApplicationContext | bridge.BridgeContext):
        message = "**These are the branches I'm currently observing:**\n```\n"

        if ctx.guild_id in self.cdn_watcher.watchlist.keys():
            for product in self.cdn_watcher.watchlist:
                message += f"{product}\n"
            
            message += "```"

            await ctx.interaction.response.send_message(message, ephemeral=True, delete_after=300)
        else:
            error_msg = "Your server does not have a watchlist, I'll create one for you with the Retail WoW branch as default, use `/cdnedit` to edit your new watchlist!"
            self.cdn_watcher.init_watchlist(str(ctx.guild_id))

            await ctx.interaction.response.send_message(error_msg, ephemeral=True, delete_after=300)

    @bridge.bridge_command(name="cdnedit")
    @commands.has_permissions(administrator=True)
    async def cdn_edit(self, ctx:bridge.BridgeApplicationContext | bridge.BridgeContext):
        if ctx.guild_id not in self.cdn_watcher.watchlist.keys():
            error_msg = "Your server does not have a watchlist, I'll create one for you with the Retail WoW branch as default, use this command again to edit your new watchlist!"
            self.cdn_watcher.init_watchlist(str(ctx.guild_id))

            await ctx.interaction.response.send_message(error_msg, ephemeral=True, delete_after=300)
        else:
            view = CDNUi(ctx=ctx, watcher=self.cdn_watcher)
            message = "Edit the branches you are currently watching using the menu below.\nTo save your changes, just click out of the menu."

            await ctx.interaction.response.send_message(message, view=view, ephemeral=True, delete_after=300)

    @bridge.bridge_command(name="cdnsetchannel")
    @commands.has_permissions(administrator=True)
    async def cdn_set_channel(self, ctx:bridge.BridgeApplicationContext | bridge.BridgeContext):
        channel = ctx.channel_id
        guild = ctx.guild_id
        
        self.cdn_watcher.set_channel(channel, guild)

        await ctx.interaction.response.send_message("Channel successfully set!", ephemeral=True, delete_after=300)

    @bridge.bridge_command(name="cdngetchannel")
    @commands.has_permissions(administrator=True)
    async def cdn_get_channel(self, ctx:bridge.BridgeApplicationContext | bridge.BridgeContext):
        guild = ctx.guild_id

        channel = self.cdn_watcher.get_channel(guild)

        if channel:
            await ctx.interaction.response.send_message(f"This server's notification channel is set to <#{channel}>", ephemeral=True, delete_after=300)
        else:
            await ctx.interaction.response.send_message(f"This server does not have a notification channel set, try `/cdnsetchannel` to set your notification channel!", ephemeral=True, delete_after=300)
    


def setup(bot):
    bot.add_cog(CDNCogWatcher(bot))