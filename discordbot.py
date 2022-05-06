import contextlib
import csv
import datetime
import io
import os
import traceback

import discord
from discord import (
    User,
    ChannelType,
    Intents,
    Guild,
)
from discord.abc import GuildChannel
from discord.ext import commands

from commands.download_messages_json import DownloadMessagesJsonCommand
from commands.mention_to_reaction_users import MentionToReactionUsersCommand
from utils.misc import parse_before_after, parse_args

intents = Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="/", intents=intents)
bot.load_extension('dispander')
token = os.environ["DISCORD_BOT_TOKEN"]
mention_to_reaction_users_command = MentionToReactionUsersCommand()
download_messages_json_command = DownloadMessagesJsonCommand()


class MessageCounter:
    def __init__(self, user: User, channel: GuildChannel):
        self.user = user
        self.channel = channel
        self.count = 0

    def __str__(self):
        return f"user=[{self.user}], channel=[{self.channel}], count={self.count}"

    def try_increment(self, user: User):
        if self.user.id != user.id:
            return False
        self.count += 1
        return True


class MessageCountResult:
    def __init__(self, user: User):
        self.user = user
        self.result_map = {}

    def __str__(self):
        return f"{self.to_dict()}"

    def add(self, channel: GuildChannel, count: int):
        self.result_map[channel] = count

    def to_dict(self):
        output = {"user": self.user.display_name}
        for channel, count in self.result_map.items():
            output[channel.name] = count
        return output


async def count_messages(
    guild: Guild,
    channel_id: int,
    before: datetime.datetime,
    after: datetime.datetime,
):
    print(f"fetch channel: {channel_id}")
    channel = guild.get_channel(channel_id)

    if channel is None:
        raise ValueError(f"not found channel: id={channel_id}")

    if channel.type != ChannelType.text:
        raise TypeError(f"{channel.name} is not TextChannel: type={channel.type}")

    message_counters = [
        MessageCounter(member, channel) for member in guild.members if not member.bot
    ]

    print(f"count from history, after={after} before={before}")
    async for message in channel.history(limit=None, before=before, after=after):
        for counter in message_counters:
            counter.try_increment(message.author)

    return channel, message_counters


def convert_to_message_count_result(counter_map: dict):
    results = {}
    for channel, message_counters in counter_map.items():
        for counter in message_counters:
            if counter.user.id not in results:
                results[counter.user.id] = MessageCountResult(counter.user)
            results[counter.user.id].add(channel, counter.count)

    return results


@bot.event
async def on_command_error(ctx, error):
    orig_error = getattr(error, "original", error)
    error_msg = "".join(
        traceback.TracebackException.from_exception(orig_error).format()
    )
    print(error_msg)
    await ctx.send(
        "unintentional error by the developer, please check the server logs."
    )


@bot.command()
async def mention_to_reaction_users(ctx, *args):
    await mention_to_reaction_users_command.execute(ctx, args)


@bot.command()
async def message_count(ctx, *args):
    print(f"command executor={ctx.author}, time={datetime.datetime.now()}")
    if ctx.author.bot:
        await ctx.send("this is bot")
        return

    print(f"check arguments, {args}")
    if len(args) < 1:
        await ctx.send(
            "format is /message_count channel={channel_id} before={YYYY-mm-dd} after={YYYY-mm-dd}"
        )
        return

    async with ctx.typing():
        parsed = parse_args(args)

        if "channel" in parsed and "channels" in parsed:
            await ctx.send(
                "cannot pass both channel and channels parameter to /message_count."
            )
            return

        if "channel" not in parsed and "channels" not in parsed:
            await ctx.send("channel or channels parameter must be set.")
            return

        channel_ids = []
        try:
            if "channel" in parsed:
                channel_ids.append(int(parsed["channel"]))
            if "channels" in parsed:
                channel_ids.extend(
                    [int(channel_id) for channel_id in parsed["channels"].split(",")]
                )
        except Exception as e:
            print(e)
            await ctx.send(f"can not parse channel_id/channel_ids: {e}")
            return

        print(f"parse channel_ids, {channel_ids}")

        try:
            before, after = parse_before_after(parsed)
        except Exception as e:
            print(e)
            await ctx.send(f"can not parse before/after: {e}")
            return

        result_map = {}
        for channel_id in channel_ids:
            try:
                channel, message_counters = await count_messages(
                    ctx.guild, channel_id, before, after
                )
            except Exception as e:
                await ctx.send(f"cannot count messages: {e}")
                return
            result_map[channel] = message_counters
        results = convert_to_message_count_result(result_map)

        filename = "number_of_messages_in_channels.csv"
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
            await ctx.send(file=discord.File(buffer, filename))


@bot.command()
async def download_messages_json(ctx, *args):
    await download_messages_json_command.execute(ctx, args)

bot.run(token)
