import os
import traceback
import discord

from discord.ext import commands

import utils.constant


class Constant(utils.constant.Constant):
    EXTENSIONS = [
        "dispander",
        "cogs.message_count",
        "cogs.emoji_count",
        "cogs.download_messages_json",
        "cogs.mention_to_reaction_users",
        "cogs.logging_voice_states",
    ]

    TOKEN = os.environ["DISCORD_BOT_TOKEN"]


class DiscordBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.voice_states = True
        super().__init__(command_prefix="/", intents=intents)

        for cog in Constant.EXTENSIONS:
            self.load_extension(cog)

    async def on_ready(self):
        print(f"DiscordBot.on_ready: bot={self.user}, guilds={self.guilds}")

    async def on_command_error(self, context, exception):
        orig_error = getattr(exception, "original", exception)
        error_msg = "".join(
            traceback.TracebackException.from_exception(orig_error).format()
        )
        print(error_msg)
        await context.send(
            "unintentional error by the developer, please check the server logs."
        )


if __name__ == "__main__":
    bot = DiscordBot()
    bot.run(Constant.TOKEN)
