import contextlib
import datetime
import io
import json
from abc import ABC
from typing import Optional

import discord
import discord.ext

from commands.command import CommandBase
from utils.misc import get_before_after_jst, parse_json


class DownloadMessagesJsonCommand(CommandBase, ABC):
    def __init__(self):
        CommandBase.__init__(self)
        self._channel_ld: Optional[int] = None
        self._before: Optional[datetime.datetime] = None
        self._after: Optional[datetime.datetime] = None

    def _parse_args(self, args: dict):
        self._channel_ld = int(args.get("channel", None))
        self._before, self._after = get_before_after_jst(args)

    async def _prepare(self, ctx: discord.ext.commands.context.Context):
        pass

    async def _execute(self, ctx: discord.ext.commands.context.Context):
        channel = ctx.guild.get_channel(self._channel_ld)

        if channel is None:
            raise ValueError(f"not found channel, message_id={self._channel_ld}")

        if channel.type != discord.ChannelType.text:
            raise TypeError(f"{channel.name} is not TextChannel: type={channel.type}")

        before: Optional[datetime.datetime] = None
        if self._before is not None:
            before = self._before.astimezone(datetime.timezone.utc).replace(tzinfo=None)

        after: Optional[datetime.datetime] = None
        if self._after is not None:
            after = self._after.astimezone(datetime.timezone.utc).replace(tzinfo=None)

        before_str = "None" if before is None else self._before.strftime("%Y-%m-%d")
        after_str = "None" if after is None else self._after.strftime("%Y-%m-%d")

        jst_timezone = datetime.timezone(datetime.timedelta(hours=9), "JST")

        print(f"read messages from history, after={after_str} before={before_str}")
        outputs = []
        async for message in channel.history(limit=None, before=before, after=after):
            message_dict = dict(
                id=message.id,
                author=message.author.name,
                display_name=message.author.display_name,
                created_at=message.created_at.astimezone(jst_timezone),
                message=message.content,
            )
            if message.edited_at is not None:
                message_dict["edited_at"] = message.edited_at.astimezone(jst_timezone)
            outputs.append(message_dict)

        filename = f"{channel.id}_{after_str}_{before_str}_messages.json"
        print(f"create {filename} buffer")
        with contextlib.closing(io.StringIO()) as buffer:
            json.dump(
                outputs,
                buffer,
                default=parse_json,
                indent=2,
                ensure_ascii=False,
            )
            buffer.seek(0)
            print(f"send {filename}")
            outputs = [f"#{channel.name}", f"{after_str} ~ {before_str}"]
            await ctx.send("\n".join(outputs), file=discord.File(buffer, filename))
