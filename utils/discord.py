import copy
import datetime
from typing import Optional

import discord
import discord.abc
from discord import Guild

from cogs.constant import Constant


async def find_channel(
    guild: discord.Guild, message_id: int
) -> (discord.abc.GuildChannel, discord.Message):
    message = None
    result = None
    for channel in guild.channels:
        if channel.type != discord.ChannelType.text:
            continue
        try:
            message = await channel.fetch_message(message_id)
        except discord.NotFound:
            pass
        except discord.Forbidden:
            pass
        except discord.HTTPException as e:
            raise e
        if message is not None:
            result = channel
            break
    return result, message


async def find_no_reaction_users(message: discord.Message, candidates: list) -> list:
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


async def find_reaction_users(message: discord.Message, emoji: str) -> list:
    target = None
    for reaction in message.reactions:
        if isinstance(reaction.emoji, discord.Emoji) and reaction.emoji.name in emoji:
            target = reaction
            break
        if isinstance(reaction.emoji, discord.PartialEmoji):
            if reaction.emoji.id is None:
                continue
            if reaction.emoji.name in emoji:
                target = reaction
                break
        if isinstance(reaction.emoji, str) and reaction.emoji == emoji:
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
    guild: Guild,
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
