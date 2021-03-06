import os
import platform
import socket
import sys
from typing import Dict

import discord
from discord.ext.commands import command, Cog, Bot, Context

from discord_ext_commands_coghelper import CogHelper


class GetSystemInfo(Cog, CogHelper):
    def __init__(self, bot: Bot):
        CogHelper.__init__(self, bot)

    @command()
    async def get_system_info(self, ctx, *args):
        await self.execute(ctx, args)

    def _parse_args(self, ctx: Context, args: Dict[str, str]):
        pass

    async def _execute(self, ctx: Context):
        title = "/get_system_info"
        description = f"bot={self.bot.user}"
        embed = discord.Embed(title=title, description=description)
        embed.add_field(
            name="platform.platform()", value=platform.platform(), inline=False
        )
        embed.add_field(name="sys.version", value=sys.version, inline=False)
        host = socket.gethostname()
        embed.add_field(name="socket.gethostname()", value=host, inline=False)
        ipaddress = socket.gethostbyname(host)
        embed.add_field(
            name=f"socket.gethostbyname({host})", value=ipaddress, inline=False
        )
        pid = os.getpid()
        embed.add_field(name="os.getpid()", value=str(pid), inline=False)
        await ctx.send(embed=embed)


def setup(bot: Bot):
    return bot.add_cog(GetSystemInfo(bot))
