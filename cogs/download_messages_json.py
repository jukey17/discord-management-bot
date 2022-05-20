import contextlib
import datetime
import io
import json
import logging
from typing import Optional, Dict

import discord
import discord.ext

import utils.misc
import utils.discord
from cogs.cog import CogBase
from cogs.constant import Constant

logger = logging.getLogger(__name__)


class DownloadMessageJson(discord.ext.commands.Cog, CogBase):
    def __init__(self, bot):
        CogBase.__init__(self, bot)
        self._channel_id: Optional[int] = None
        self._before: Optional[datetime.datetime] = None
        self._after: Optional[datetime.datetime] = None

    @discord.ext.commands.command()
    async def download_messages_json(self, ctx, *args):
        await self.execute(ctx, args)

    def _parse_args(self, args: Dict[str, str]):
        self._channel_id = int(args.get("channel", None))
        self._before, self._after = utils.misc.get_before_after_jst(args)

    async def _execute(self, ctx: discord.ext.commands.context.Context):
        channel = ctx.guild.get_channel(self._channel_id)
        if channel is None:
            logger.error(f"not found channel, channel_id={self._channel_id}")
            await ctx.send(
                f"チャンネルが見つかりませんでした。チャンネルID: `{self._channel_id}` が正しいか確認してください。"
            )
            return
        if not isinstance(channel, discord.TextChannel):
            logger.error(f"not discord.TextChannel, channel={channel}")
            await ctx.send(f"{channel} はテキストチャンネルではありません。")
            return

        before = utils.discord.convert_to_utc_naive_datetime(self._before)
        after = utils.discord.convert_to_utc_naive_datetime(self._after)
        before_str, after_str = utils.discord.get_before_after_str(
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
            json.dump(
                results,
                buffer,
                default=utils.misc.parse_json,
                indent=2,
                ensure_ascii=False,
            )
            buffer.seek(0)
            logger.debug(f"send {filename}")
            title = "/download_messages_json"
            description = f"集計期間: {after_str} ~ {before_str}"
            embed = discord.Embed(title=title, description=description)
            embed.add_field(name=f"#{channel.name}", value=channel.id)
            await ctx.send(embed=embed, file=discord.File(buffer, filename))


def setup(bot):
    return bot.add_cog(DownloadMessageJson(bot))
