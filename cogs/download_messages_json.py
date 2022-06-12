import contextlib
import datetime
import io
import json
import logging
from typing import Optional, Dict

import discord
from discord import ChannelType
from discord.ext.commands import Context, Bot, command
from discord_ext_commands_coghelper import (
    CogHelper,
    ArgumentError,
    ChannelNotFoundError,
    ChannelTypeError,
    get_before_after,
)

from cogs.constant import Constant
from utils.discord import convert_to_utc_naive_datetime, get_before_after_str
from utils.misc import parse_json

logger = logging.getLogger(__name__)


class DownloadMessageJson(discord.ext.commands.Cog, CogHelper):
    def __init__(self, bot: Bot):
        CogHelper.__init__(self, bot)
        self._channel_id: Optional[int] = None
        self._before: Optional[datetime.datetime] = None
        self._after: Optional[datetime.datetime] = None

    @command()
    async def download_messages_json(self, ctx, *args):
        await self.execute(ctx, args)

    def _parse_args(self, ctx: Context, args: Dict[str, str]):
        if "channel" not in args:
            raise ArgumentError(ctx, channel="チャンネルIDを必ず設定してください")

        self._channel_id = int(args.get("channel", None))
        self._before, self._after = get_before_after(
            ctx, args, Constant.DATE_FORMAT, Constant.JST
        )

    async def _execute(self, ctx: Context):
        channel = ctx.guild.get_channel(self._channel_id)
        if channel is None:
            raise ChannelNotFoundError(ctx, self._channel_id)
        if not isinstance(channel, discord.TextChannel):
            raise ChannelTypeError(ctx, channel, ChannelType.text)

        before = convert_to_utc_naive_datetime(self._before)
        after = convert_to_utc_naive_datetime(self._after)
        before_str, after_str = get_before_after_str(
            self._before, self._after, ctx.guild, Constant.JST
        )

        logger.debug(
            f"read messages from {channel.name} history, after={after_str} before={before_str}"
        )
        results = []
        async for message in channel.history(limit=None, before=before, after=after):
            result = dict(
                id=message.id,
                author=message.author.name,
                display_name=message.author.display_name,
                created_at=message.created_at.astimezone(Constant.JST),
                message=message.content,
            )
            if message.edited_at is not None:
                result["edited_at"] = message.edited_at.astimezone(Constant.JST)
            results.append(result)

        filename = f"{channel.id}_messages_{after_str}_{before_str}.json".replace(
            "/", ""
        )
        logger.debug(f"create {filename}")
        with contextlib.closing(io.StringIO()) as buffer:
            json.dump(results, buffer, default=parse_json, indent=2, ensure_ascii=False)
            buffer.seek(0)
            logger.debug(f"send {filename}")
            title = "/download_messages_json"
            description = f"集計期間: {after_str} ~ {before_str}"
            embed = discord.Embed(title=title, description=description)
            embed.add_field(name=f"#{channel.name}", value=channel.id)
            await ctx.send(embed=embed, file=discord.File(buffer, filename))


def setup(bot: Bot):
    return bot.add_cog(DownloadMessageJson(bot))
