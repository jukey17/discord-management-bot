import contextlib
import csv
import datetime
import io
from abc import ABC
from typing import Optional

import discord
import discord.ext

from commands.command import CommandBase
from utils.misc import get_before_after_jst


class _MessageCounter:
    def __init__(self, user: discord.User, channel: discord.abc.GuildChannel):
        self.user = user
        self.channel = channel
        self.count = 0

    def __str__(self):
        return f"user=[{self.user}], channel=[{self.channel}], count={self.count}"

    def try_increment(self, user: discord.User):
        if self.user.id != user.id:
            return False
        self.count += 1
        return True


class _MessageCountResult:
    def __init__(self, user: discord.User):
        self.user = user
        self.result_map = {}

    def __str__(self):
        return f"{self.to_dict()}"

    def add(self, channel: discord.abc.GuildChannel, count: int):
        self.result_map[channel] = count

    def to_dict(self):
        output = {"user": self.user.display_name}
        for channel, count in self.result_map.items():
            output[channel.name] = count
        return output


class MessageCountCommand(CommandBase, ABC):
    def __init__(self):
        CommandBase.__init__(self)
        self._channel_ids: Optional[list] = None
        self._before: Optional[datetime.datetime] = None
        self._after: Optional[datetime.datetime] = None

    def _parse_args(self, args: dict):
        self._channel_ids = [
            int(channel_id) for channel_id in args["channel"].split(",")
        ]
        self._before, self._after = get_before_after_jst(args)

    async def _prepare(self, ctx: discord.ext.commands.context.Context):
        pass

    async def _execute(self, ctx: discord.ext.commands.context.Context):
        before: Optional[datetime.datetime] = None
        if self._before is not None:
            before = self._before.astimezone(datetime.timezone.utc).replace(tzinfo=None)

        after: Optional[datetime.datetime] = None
        if self._after is not None:
            after = self._after.astimezone(datetime.timezone.utc).replace(tzinfo=None)

        before_str = "None" if before is None else self._before.strftime("%Y-%m-%d")
        after_str = "None" if after is None else self._after.strftime("%Y-%m-%d")

        channels = [
            ctx.guild.get_channel(channel_id) for channel_id in self._channel_ids
        ]
        result_map = {}
        for channel_id in self._channel_ids:
            channel = ctx.guild.get_channel(channel_id)
            if channel is None:
                raise ValueError(f"not found channel: id={channel_id}")
            if not isinstance(channel, discord.TextChannel):
                raise TypeError(f"{type(channel)} is not TextChannel")

            print(
                f"{channel.name} count from history, after={after_str} before={before_str}"
            )
            message_counters = await self._count_messages(
                ctx.guild, channel, before, after
            )
            result_map[channel] = message_counters

        results = self._convert_to_message_count_result(result_map)

        filename = f"message_count_{after_str}_{before_str}.csv"
        print(f"create {filename} buffer")
        with contextlib.closing(io.StringIO()) as buffer:
            fieldnames = ["user"]
            fieldnames.extend([key.name for key in result_map.keys()])

            writer = csv.DictWriter(buffer, fieldnames)
            writer.writeheader()

            for user_id, result in results.items():
                writer.writerow(result.to_dict())
            buffer.seek(0)

            print(f"send {filename}")
            channel_names = ",".join([f"#{channel.name}" for channel in channels])
            outputs = [f"{[channel_names]}", f"{after_str} ~ {before_str}"]
            await ctx.send("\n".join(outputs), file=discord.File(buffer, filename))

    @staticmethod
    async def _count_messages(
        guild: discord.Guild,
        channel: discord.TextChannel,
        before: datetime.datetime,
        after: datetime.datetime,
    ):
        message_counters = [
            _MessageCounter(member, channel)
            for member in guild.members
            if not member.bot
        ]

        async for message in channel.history(limit=None, before=before, after=after):
            for counter in message_counters:
                counter.try_increment(message.author)

        return message_counters

    @staticmethod
    def _convert_to_message_count_result(counter_map: dict):
        results = {}
        for channel, message_counters in counter_map.items():
            for counter in message_counters:
                if counter.user.id not in results:
                    results[counter.user.id] = _MessageCountResult(counter.user)
                results[counter.user.id].add(channel, counter.count)

        return results
