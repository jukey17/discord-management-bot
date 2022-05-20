import copy
import datetime
from typing import Optional, Union, List

import discord
import discord.abc

from cogs.constant import Constant


async def find_text_channel(
    guild: discord.Guild, message_id: int
) -> (Optional[discord.TextChannel], Optional[discord.Message]):
    for channel in guild.channels:
        if not isinstance(channel, discord.TextChannel):
            continue
        try:
            message = await channel.fetch_message(message_id)
        except (discord.NotFound, discord.Forbidden):
            pass
        except discord.HTTPException as e:
            raise e
        else:
            return channel, message
    return None, None


async def find_no_reaction_users(
    message: discord.Message, candidates: List[Union[discord.Member, discord.User]]
) -> List[Union[discord.Member, discord.User]]:
    result = copy.copy(candidates)
    for reaction in message.reactions:
        users = [user async for user in reaction.users()]
        for candidate in candidates:
            if candidate not in result:
                continue
            for user in users:
                if candidate.id == user.id:
                    result.remove(candidate)

    return result


async def find_reaction_users(
    message: discord.Message, emoji: str
) -> List[Union[discord.Member, discord.User]]:
    target = None
    for reaction in message.reactions:
        if isinstance(reaction.emoji, discord.Emoji):
            # カスタム絵文字は名前が含まれているか見る ※:{name}:の形式なはずなので
            if reaction.emoji.name not in emoji:
                continue
        if isinstance(reaction.emoji, discord.PartialEmoji):
            # Partial絵文字も名前が含まれているか見る
            if reaction.emoji.id is None:
                continue
            if reaction.emoji.name not in emoji:
                continue
        if isinstance(reaction.emoji, str):
            # Unicode絵文字は完全一致でOK
            if reaction.emoji != emoji:
                continue
        target = reaction
        break

    if target is None:
        return []
    return [user async for user in target.users()]


def convert_to_utc_naive_datetime(dt: datetime.datetime) -> Optional[datetime.datetime]:
    if dt is None:
        return None
    return dt.astimezone(datetime.timezone.utc).replace(tzinfo=None)


def get_before_after_str(
    before: datetime.datetime,
    after: datetime.datetime,
    guild: discord.Guild,
    tz: datetime.timezone,
) -> (str, str):
    if before is None:
        before_str = datetime.datetime.now(tz=tz).strftime(Constant.DATE_FORMAT)
    else:
        before_str = before.strftime(Constant.DATE_FORMAT)
    if after is None:
        after_str = (
            guild.created_at.replace(tzinfo=datetime.timezone.utc)
            .astimezone(Constant.JST)
            .strftime(Constant.DATE_FORMAT)
        )
    else:
        after_str = after.replace(tzinfo=tz).strftime(Constant.DATE_FORMAT)

    return before_str, after_str
