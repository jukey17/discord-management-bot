import datetime
from enum import Enum
from typing import List, Optional, Dict

import discord.ext

import cogs.constant
import utils.discord
import utils.misc
from cogs.cog import CogBase


class _SortOrder(Enum):
    ASCENDING = 1
    DESCENDING = 2

    @classmethod
    def parse(cls, value: str):
        return _SortOrder.DESCENDING if value == "descending" else _SortOrder.ASCENDING


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


class _Constant(cogs.constant.Constant):
    DEFAULT_RANK: int = 10


class EmojiCount(discord.ext.commands.Cog, CogBase):
    def __init__(self, bot):
        CogBase.__init__(self)
        self.bot = bot
        self._channel_ids: List[int]
        self._before: Optional[datetime.datetime] = None
        self._after: Optional[datetime.datetime] = None
        self._order = _SortOrder.ASCENDING
        self._rank = _Constant.DEFAULT_RANK
        self._bot = False

    @discord.ext.commands.command()
    async def emoji_count(self, ctx, *args):
        await self.execute(ctx, args)

    def _parse_args(self, args: Dict[str, str]):
        self._channel_ids = utils.misc.get_array(
            args, "channel", ",", lambda value: int(value), []
        )
        self._before, self._after = utils.misc.get_before_after_jst(args)
        self._order = _SortOrder.parse(args.get("order", ""))
        self._rank = int(args.get("rank", _Constant.DEFAULT_RANK))
        self._bot = utils.misc.get_boolean(args, "bot", False)

    async def _execute(self, ctx: discord.ext.commands.context.Context):
        before = utils.discord.convert_to_utc_naive_datetime(self._before)
        after = utils.discord.convert_to_utc_naive_datetime(self._after)

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
            except discord.Forbidden as e:
                # BOTに権限がないケースはログを出力して続行
                print(f"exception={e}, channel={channel}")
            else:
                for message in messages:
                    for counter in counters:
                        # メッセージ内に使われているかのカウント
                        if counter.emoji.name in message.content:
                            # BOTを弾く
                            if self._bot or not message.author.bot:
                                counter.increment(_EmojiCountType.MESSAGE_CONTENT)
                        # リアクションに使われているかのカウント
                        for reaction in message.reactions:
                            if not isinstance(reaction.emoji, discord.Emoji):
                                continue
                            if reaction.emoji.id != counter.emoji.id:
                                continue
                            # BOTを弾く
                            if not self._bot and all(
                                [user.bot async for user in reaction.users()]
                            ):
                                continue
                            counter.increment(_EmojiCountType.MESSAGE_REACTION)

        # ソートした上で要求された順位までの要素数に切り取る
        rank = max(1, min(self._rank, len(ctx.guild.emojis)))
        reverse = True if self._order == _SortOrder.DESCENDING else False
        sorted_counters = sorted(
            counters, key=lambda c: c.total_count, reverse=reverse
        )[0:rank]

        # Embed生成
        if self._order == _SortOrder.DESCENDING:
            title = f"カスタム絵文字 利用ランキング ベスト{rank}"
        else:
            title = f"カスタム絵文字 利用ランキング ワースト{rank}"
        before_str, after_str = utils.discord.get_before_after_str(
            self._before, self._after, ctx.guild, _Constant.JST
        )
        description = f"{after_str} ~ {before_str}"
        embed = discord.Embed(title=title, description=description)
        for index, counter in enumerate(sorted_counters):
            name = f"{index + 1}位 {counter.emoji} 合計: {counter.total_count}回"
            value = (
                f"メッセージ内: {counter.counts[_EmojiCountType.MESSAGE_CONTENT]}回 "
                f"リアクション: {counter.counts[_EmojiCountType.MESSAGE_REACTION]}回"
            )
            embed.add_field(name=name, value=value, inline=False)

        # 集計結果を送信
        await ctx.send(embed=embed)
        await ctx.send(" ".join([str(counter.emoji) for counter in sorted_counters]))


def setup(bot):
    return bot.add_cog(EmojiCount(bot))
