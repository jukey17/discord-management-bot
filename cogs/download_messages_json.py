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
            raise ValueError(f"not found channel, message_id={self._channel_id}")

        if channel.type != discord.ChannelType.text:
            raise TypeError(f"{channel.name} is not TextChannel: type={channel.type}")

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

        filename = f"{channel.id}_{after_str}_{before_str}_messages.json"
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
            texts = [f"#{channel.name}", f"{after_str} ~ {before_str}"]
            await ctx.send("\n".join(texts), file=discord.File(buffer, filename))


def setup(bot):
    return bot.add_cog(DownloadMessageJson(bot))
