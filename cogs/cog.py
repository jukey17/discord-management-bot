import datetime

import discord.ext.commands.context

from utils.misc import parse_args


class CogBase:

    def __init__(self):
        pass

    async def execute(self, ctx: discord.ext.commands.context.Context, args):
        print(
            f"{ctx.command} executor={ctx.author}, channel={ctx.channel}, time={datetime.datetime.now()}"
        )

        if ctx.author.bot:
            print("this is bot.")
            return

        async with ctx.typing():
            self._parse_args(parse_args(args))
            await self._execute(ctx)

    def _parse_args(self, args: dict):
        return NotImplementedError("this method is must be override.")

    async def _execute(self, ctx: discord.ext.commands.context.Context):
        return NotImplementedError("this method is must be override.")