import logging
import os
import sys
import traceback
import discord

from discord.ext import commands
from discord.ext.commands import CommandNotFound

import utils.constant


class Constant(utils.constant.Constant):
    EXTENSIONS = [
        "dispander",
        "discord_emoji_ranking",
        "cogs.get_system_info",
        "cogs.message_count",
        "cogs.download_messages_json",
        "cogs.mention_to_reaction_users",
        "cogs.logging_voice_states",
        "cogs.notify_when_sent",
    ]

    TOKEN = os.environ["DISCORD_BOT_TOKEN"]


def init_logger(name: str):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    console = logging.StreamHandler(stream=sys.stdout)
    console.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(module)s %(filename)s(%(lineno)d) %(funcName)s: %(message)s"
    )
    console.setFormatter(formatter)
    logger.addHandler(console)


class DiscordBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="/", intents=intents)

        for cog in Constant.EXTENSIONS:
            self.load_extension(cog)
        init_logger(__name__)
        init_logger("cogs")
        init_logger("discord_emoji_ranking")
        init_logger("discord_ext_commands_coghelper")
        self._logger = logging.getLogger(__name__)

    async def on_ready(self):
        self._logger.debug(
            f"DiscordBot.on_ready: bot={self.user}, guilds={self.guilds}"
        )

    async def on_command_error(self, context, exception):
        orig_error = getattr(exception, "original", exception)
        error_msg = "".join(
            traceback.TracebackException.from_exception(orig_error).format()
        )
        self._logger.error(error_msg)
        if not isinstance(exception, CommandNotFound):
            await context.send(
                "unintentional error by the developer, please check the server logs."
            )


if __name__ == "__main__":
    bot = DiscordBot()
    bot.run(Constant.TOKEN)
