import contextlib
import datetime
import io
import json
from typing import Optional, Dict

import discord
import discord.ext

import utils.misc
import utils.discord
from cogs.cog import CogBase
from cogs.constant import Constant


class DownloadMessageJson(discord.ext.commands.Cog, CogBase):
    def __init__(self, bot):
        CogBase.__init__(self)
        self.bot = bot
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

        print(f"read messages from history, after={after_str} before={before_str}")
        outputs = []
        async for message in channel.history(limit=None, before=before, after=after):
            message_dict = dict(
                id=message.id,
                author=message.author.name,
                display_name=message.author.display_name,
                created_at=message.created_at.astimezone(Constant.JST),
                message=message.content,
            )
            if message.edited_at is not None:
                message_dict["edited_at"] = message.edited_at.astimezone(Constant.JST)
            outputs.append(message_dict)

        filename = f"{channel.id}_{after_str}_{before_str}_messages.json"
        print(f"create {filename} buffer")
        with contextlib.closing(io.StringIO()) as buffer:
            json.dump(
                outputs,
                buffer,
                default=utils.misc.parse_json,
                indent=2,
                ensure_ascii=False,
            )
            buffer.seek(0)
            print(f"send {filename}")
            outputs = [f"#{channel.name}", f"{after_str} ~ {before_str}"]
            await ctx.send("\n".join(outputs), file=discord.File(buffer, filename))


def setup(bot):
    return bot.add_cog(DownloadMessageJson(bot))
