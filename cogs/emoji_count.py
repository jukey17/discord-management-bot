import datetime
from enum import Enum
from typing import List, Optional

import discord.ext

from cogs.cog import CogBase
from utils.misc import get_before_after_jst


class _SortOrder(Enum):
    ASCENDING = 1
    DESCENDING = 2


class _EmojiCountType(Enum):
    MESSAGE_CONTENT = 1
    MESSAGE_REACTION = 2


class _EmojiCounter:
    def __init__(self, emoji: discord.Emoji):
        self.emoji = emoji
        self.counts = {t: 0 for t in _EmojiCountType}

    def increment(self, count_type: _EmojiCountType):
        self.counts[count_type] += 1

    @property
    def total_count(self):
        return sum(self.counts.values())


class EmojiCount(discord.ext.commands.Cog, CogBase):
    def __init__(self, bot):
        CogBase.__init__(self)
        self.bot = bot
        self._channel_ids: List[int]
        self._before: Optional[datetime.datetime] = None
        self._after: Optional[datetime.datetime] = None
        self._order = _SortOrder.ASCENDING
        self._rank = 10

    @discord.ext.commands.command()
    async def emoji_count(self, ctx, *args):
        await self.execute(ctx, args)

    def _parse_args(self, args: dict):
        self._channel_ids = (
            [int(channel_id) for channel_id in args["channel"].split(",")]
            if "channel" in args
            else []
        )
        self._before, self._after = get_before_after_jst(args)
        order = args.get("order", None)
        if order is not None:
            self._order = (
                _SortOrder.DESCENDING if order == "descending" else _SortOrder.ASCENDING
            )
        if "rank" in args:
            self._rank = int(args["rank"])

    async def _execute(self, ctx: discord.ext.commands.context.Context):
        before: Optional[datetime.datetime] = None
        if self._before is not None:
            before = self._before.astimezone(datetime.timezone.utc).replace(tzinfo=None)

        after: Optional[datetime.datetime] = None
        if self._after is not None:
            after = self._after.astimezone(datetime.timezone.utc).replace(tzinfo=None)

        if before is None:
            before_str = datetime.datetime.now().strftime("%Y/%m/%d")
        else:
            before_str = self._before.strftime("%Y/%m/%d")
        if after is None:
            jst = datetime.timezone(datetime.timedelta(hours=9), "JST")
            after_str = (
                ctx.guild.created_at.replace(tzinfo=datetime.timezone.utc)
                .astimezone(jst)
                .strftime("%Y/%m/%d")
            )
        else:
            after_str = self._after.strftime("%Y/%m/%d")

        channels = (
            [ctx.guild.get_channel(channel_id) for channel_id in self._channel_ids]
            if len(self._channel_ids) > 0
            else ctx.guild.channels
        )

        counters = [_EmojiCounter(emoji) for emoji in ctx.guild.emojis]
        for channel in channels:
            if channel is None:
                print("channel is None.")
                continue
            if not isinstance(channel, discord.TextChannel):
                print(f"{channel} is Not TextChannel")
                continue

            try:
                messages = [
                    message
                    async for message in channel.history(
                        limit=None, before=before, after=after
                    )
                ]
            except Exception as e:
                # BOTに権限がないケースなど
                print(f"exception={e}, channel={channel}")
            else:
                for message in messages:
                    for counter in counters:
                        # メッセージ内に使われているかのカウント
                        if counter.emoji.name in message.content:
                            counter.increment(_EmojiCountType.MESSAGE_CONTENT)
                        # リアクションに使われているかのカウント
                        for reaction in message.reactions:
                            if not isinstance(reaction.emoji, discord.Emoji):
                                continue
                            if reaction.emoji.id != counter.emoji.id:
                                continue
                            counter.increment(_EmojiCountType.MESSAGE_REACTION)

        rank = max(1, min(self._rank, len(ctx.guild.emojis)))
        reverse = True if self._order == _SortOrder.DESCENDING else False
        sorted_counters = sorted(
            counters, key=lambda c: c.total_count, reverse=reverse
        )[0:rank]

        if self._order == _SortOrder.DESCENDING:
            title = f"カスタム絵文字 ランキング ベスト{rank}"
        else:
            title = f"カスタム絵文字 ランキング ワースト{rank}"
        description = f"{after_str} ~ {before_str}"
        embed = discord.Embed(title=title, description=description)
        for index, counter in enumerate(sorted_counters):
            name = f"{index + 1}位 {counter.emoji} 合計: {counter.total_count}回"
            value = (
                f"メッセージ内: {counter.counts[_EmojiCountType.MESSAGE_CONTENT]}回 "
                f"リアクション: {counter.counts[_EmojiCountType.MESSAGE_REACTION]}回"
            )
            embed.add_field(name=name, value=value, inline=False)
        await ctx.send(embed=embed)
        await ctx.send(" ".join([str(counter.emoji) for counter in sorted_counters]))


def setup(bot):
    return bot.add_cog(EmojiCount(bot))
