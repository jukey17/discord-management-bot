import logging
from typing import Dict

import discord.ext.commands.context

import utils.misc

logger = logging.getLogger(__name__)


class ArgumentError(Exception):
    def __init__(self, **kwargs):
        self.wrong_map = kwargs


class CogBase:
    def __init__(self, bot):
        self.bot = bot

    async def execute(self, ctx: discord.ext.commands.context.Context, args):
        logger.debug(
            f"{ctx.command} executor={ctx.author}, guild={ctx.guild}, channel={ctx.channel}, args={args}"
        )

        if ctx.author.bot:
            logger.warning("this is bot.")
            return

        async with ctx.typing():
            try:
                self._parse_args(utils.misc.parse_args(args))
            except ArgumentError as ae:
                await self._send_exception(ctx, ae)
            else:
                await self._execute(ctx)

    @staticmethod
    async def _send_exception(
        ctx: discord.ext.commands.context.Context, exception: ArgumentError
    ):
        title = "引数が間違っています"
        description = f"{ctx.message.content}"
        embed = discord.Embed(title=title, description=description)
        for key, value in exception.wrong_map.items():
            embed.add_field(name=key, value=value)
        await ctx.send(embed=embed)

    def _parse_args(self, args: Dict[str, str]):
        return NotImplementedError("this method is must be override.")

    async def _execute(self, ctx: discord.ext.commands.context.Context):
        return NotImplementedError("this method is must be override.")
