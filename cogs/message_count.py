import contextlib
import csv
import datetime
import io
import logging
from typing import Optional, Dict, List

import discord
import discord.ext
from discord.ext.commands import Cog, command, Context, Bot
from discord_ext_commands_coghelper import (
    CogHelper,
    ArgumentError,
    ChannelNotFoundError,
    ChannelTypeError,
    get_list,
    get_before_after,
)

from cogs.constant import Constant
from utils.discord import convert_to_utc_naive_datetime, get_before_after_str

logger = logging.getLogger(__name__)


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


class MessageCount(Cog, CogHelper):
    def __init__(self, bot: Bot):
        CogHelper.__init__(self, bot)
        self._channel_ids: List[int]
        self._before: Optional[datetime.datetime] = None
        self._after: Optional[datetime.datetime] = None

    @command()
    async def message_count(self, ctx, *args):
        await self.execute(ctx, args)

    def _parse_args(self, ctx: Context, args: Dict[str, str]):
        if "channel" not in args:
            raise ArgumentError(ctx, channel="チャンネルIDを一つ以上必ず設定してください")

        self._channel_ids = get_list(args, "channel", ",", lambda value: int(value), [])
        self._before, self._after = get_before_after(
            ctx, args, Constant.DATE_FORMAT, Constant.JST
        )

    async def _execute(self, ctx: Context):
        before = convert_to_utc_naive_datetime(self._before)
        after = convert_to_utc_naive_datetime(self._after)
        before_str, after_str = get_before_after_str(
            self._before, self._after, ctx.guild, Constant.JST
        )

        result_map = {}
        for channel_id in self._channel_ids:
            channel = ctx.guild.get_channel(channel_id)
            if channel is None:
                raise ChannelNotFoundError(ctx, channel_id)
            if not isinstance(channel, discord.TextChannel):
                raise ChannelTypeError(ctx, channel, discord.ChannelType.text)

            logger.debug(
                f"{channel} count from history, after={after_str} before={before_str}"
            )
            message_counters = await self._count_messages(
                ctx.guild, channel, before, after
            )
            result_map[channel] = message_counters

        results = self._convert_to_message_count_result(result_map)

        filename = f"message_count_{after_str}_{before_str}.csv".replace("/", "")
        logger.debug(f"create {filename} buffer")
        with contextlib.closing(io.StringIO()) as buffer:
            fieldnames = ["user"]
            fieldnames.extend([key.name for key in result_map.keys()])

            writer = csv.DictWriter(buffer, fieldnames)
            writer.writeheader()

            for user_id, result in results.items():
                writer.writerow(result.to_dict())
            buffer.seek(0)

            logger.debug(f"send {filename}")

            title = "/message_count"
            description = f"集計期間: {after_str} ~ {before_str}"
            embed = discord.Embed(title=title, description=description)
            for channel in result_map.keys():
                embed.add_field(name=f"#{channel.name}", value=channel.id)
            await ctx.send(embed=embed, file=discord.File(buffer, filename))

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
    def _convert_to_message_count_result(
        counter_map: Dict[discord.TextChannel, List[_MessageCounter]]
    ):
        results = {}
        for channel, message_counters in counter_map.items():
            for counter in message_counters:
                if counter.user.id not in results:
                    results[counter.user.id] = _MessageCountResult(counter.user)
                results[counter.user.id].add(channel, counter.count)

        return results


def setup(bot: Bot):
    return bot.add_cog(MessageCount(bot))
