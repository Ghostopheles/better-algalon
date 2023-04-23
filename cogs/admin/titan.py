import discord

from discord.ext import bridge, commands

# TODO:
# live testing
# toggleable feature flags
# performance stats?
# health
# uptime
# is debug?
# ???
# profit


class Titan(commands.Cog):
    def __init__(self, bot: bridge.Bot):
        self.bot = bot
        self.owner = bot.owner_id
        self.flags = self.bot.features.flags  # type: ignore

    def check_isOwner(self, ctx: discord.ApplicationContext):
        return ctx.author.id == self.owner

    async def send_message_to_owner(
        self,
        message,
        ctx: discord.ApplicationContext | bridge.BridgeApplicationContext | None = None,
        *args,
    ):
        """Sends a message to the owner!"""
        owner = await self.bot.fetch_user(self.bot.owner_id)  # type: ignore
        channel = await owner.create_dm()

        if isinstance(message, Exception):
            message = f"I've encountered an error! Help!\n```py\n{message}\n```\n"

        if ctx:
            message += f"CALLER: {ctx.author}\nGUILD: {ctx.guild.name} | {ctx.guild_id}"  # type: ignore

        if args:
            message += f"ARGS: ".join(args)

        await channel.send(message)

    @bridge.bridge_command(
        name="viewflags",
        # checks=[check_isOwner],
    )
    async def view_flags(self, ctx: bridge.BridgeApplicationContext):
        """View the current flags."""
        all_flags = self.flags.get_all_flags()

        message = f"Flags:\n```{all_flags}```"

        # for flag in all_flags:
        #    message += f"{flag.name}:{flag.value}\n"

        try:
            await ctx.interaction.response.send_message(
                message,
                ephemeral=True,
                delete_after=300,
            )
        except Exception as exc:
            await self.send_message_to_owner(exc, ctx)

    @bridge.bridge_command(
        name="viewdesyncedcommands",
        # checks=[check_isOwner],
    )
    async def view_desynced_commands(self, ctx: bridge.BridgeApplicationContext):
        """View all registered commands."""
        message = "Commands:\n```"

        commands = await self.bot.get_desynced_commands()
        if not commands:
            message = "No desynced commands found."
        else:
            for command in commands:
                name = command["cmd"]
                message += f"{name}\n"

            message += "```"

        await ctx.interaction.response.send_message(
            message, ephemeral=True, delete_after=300
        )


def setup(bot):
    bot.add_cog(Titan(bot))
