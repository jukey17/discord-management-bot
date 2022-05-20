import datetime
import logging
from typing import Dict

import discord.ext.commands.context

import utils.misc

logger = logging.getLogger(__name__)


class CogBase:
    def __init__(self):
        pass

    async def execute(self, ctx: discord.ext.commands.context.Context, args):
        logger.debug(
            f"{ctx.command} executor={ctx.author}, guild={ctx.guild}, channel={ctx.channel}, args={args}"
        )

        if ctx.author.bot:
            logger.warning("this is bot.")
            return

        async with ctx.typing():
            self._parse_args(utils.misc.parse_args(args))
            await self._execute(ctx)

    def _parse_args(self, args: Dict[str, str]):
        return NotImplementedError("this method is must be override.")

    async def _execute(self, ctx: discord.ext.commands.context.Context):
        return NotImplementedError("this method is must be override.")
