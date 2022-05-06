import datetime
from abc import ABCMeta, abstractmethod

import discord.ext.commands.context

from utils.misc import parse_args


class CommandBase:
    __metaclass__ = ABCMeta

    def __init__(self):
        pass

    async def execute(self, ctx, args):
        print(
            f"{ctx.command} executor={ctx.author}, channel={ctx.channel}, time={datetime.datetime.now()}"
        )

        if ctx.author.bot:
            await ctx.send("this is bot")
            return

        async with ctx.typing():
            parsed = parse_args(args)
            self._parse_args(parsed)

            await self._prepare(ctx)
            await self._execute(ctx)

    @abstractmethod
    def _parse_args(self, args: dict):
        pass

    @abstractmethod
    async def _prepare(self, ctx: discord.ext.commands.context.Context):
        pass

    @abstractmethod
    async def _execute(self, ctx: discord.ext.commands.context.Context):
        pass
