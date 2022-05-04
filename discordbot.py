import contextlib
import copy
import csv
import datetime
import io
import json
import os
import re
import traceback
import gspread

import discord
from discord import (
    User,
    ChannelType,
    Intents,
    Guild,
    Message,
    Emoji,
    PartialEmoji,
)
from discord.abc import GuildChannel
from discord.ext import commands
from google.oauth2 import service_account

intents = Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="/", intents=intents)
token = os.environ["DISCORD_BOT_TOKEN"]

scopes = ["https://www.googleapis.com/auth/spreadsheets"]
credentials_file = os.environ["GOOGLE_CREDENTIALS_FILE"]
credentials = service_account.Credentials.from_service_account_file(
    os.environ["GOOGLE_CREDENTIALS_FILE"],
    scopes=["https://www.googleapis.com/auth/spreadsheets"],
)
gspread_client = gspread.authorize(credentials)


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


def parse_args(args):
    parsed = {}
    for arg in args:
        result = re.match(r"(.*)=(.*)", arg)
        if result is None:
            parsed[arg] = "True"
        else:
            parsed[result.group(1)] = result.group(2)

    return parsed


def parse_before_after(args: dict):
    before: datetime.datetime = None
    after: datetime.datetime = None
    if "before" in args:
        before = (
            datetime.datetime.strptime(args["before"], "%Y-%m-%d")
            .astimezone(datetime.timezone.utc)
            .replace(tzinfo=None)
        )
    if "after" in args:
        after = (
            datetime.datetime.strptime(args["after"], "%Y-%m-%d")
            .astimezone(datetime.timezone.utc)
            .replace(tzinfo=None)
        )

    if after is not None and before is not None and after > before:
        raise ValueError("before must be a future than after.")

    return before, after


def parse_json(obj):
    if isinstance(obj, datetime.datetime):
        return obj.isoformat(" ")
    else:
        str(obj)


async def find_channel(guild: Guild, message_id: int) -> (GuildChannel, Message):
    message = None
    result = None
    for channel in guild.channels:
        if channel.type != ChannelType.text:
            continue
        try:
            message = await channel.fetch_message(message_id)
        except Exception as e:
            print(f"channel={channel.name}, exception={e}")
        if message is not None:
            result = channel
            break
    return result, message


async def find_no_reaction_users(message: Message, candidates: list) -> list:
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


async def find_reaction_users(message: Message, ignore_ids: list, emoji: str) -> list:
    target = None
    for reaction in message.reactions:
        if isinstance(reaction.emoji, Emoji) and reaction.emoji.name in emoji:
            target = reaction
            break
        if isinstance(reaction.emoji, PartialEmoji):
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
    return [user async for user in target.users() if user.id not in ignore_ids]


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


async def manage_mention_to_reaction_users(ctx, args):
    print("manage mode")

    if "ignore_list" in args:
        sheet_id = os.environ["IGNORE_LIST_SHEET_ID"]
        workbook = gspread_client.open_by_key(sheet_id)
        worksheet = workbook.worksheet(str(ctx.guild.id))
        ignore_ids = worksheet.col_values(1)
        ignore_users = [ctx.guild.get_member(int(user_id)) for user_id in ignore_ids]

        if "download" in args:
            filename = f"ignore_list_{ctx.guild.id}.json"
            print(
                f"download ignore_list: sheet_id={sheet_id}, guild={ctx.guild.id}-> {filename}"
            )
            ignore_dict = [
                dict(id=user.id, name=user.name, display_name=user.display_name)
                for user in ignore_users
            ]
            with contextlib.closing(io.StringIO()) as buffer:
                json.dump(
                    ignore_dict,
                    buffer,
                    default=parse_json,
                    indent=2,
                    ensure_ascii=False,
                )
                buffer.seek(0)
                await ctx.send(file=discord.File(buffer, filename))

        if "append" in args:
            append_id = args["append"]
            print(
                f"append ignore_list: sheet_id={sheet_id}, guild={ctx.guild.id}, user={append_id}"
            )
            if ctx.guild.get_member(int(append_id)) is None:
                await ctx.send(f"not found user: id={append_id}")
                return

            ignore_ids.append(append_id)
            update_cells = worksheet.range(f"A1:A{len(ignore_ids)}")
            for i, cell in enumerate(update_cells):
                cell.value = ignore_ids[i]
            worksheet.update_cells(update_cells)
            await ctx.send("completed append ignore_list!")

        if "remove" in args:
            remove_id = args["remove"]
            print(
                f"remove ignore_list: sheet_id={sheet_id}, guild={ctx.guild.id}, user={remove_id}"
            )
            if remove_id not in ignore_ids:
                await ctx.send(f"not contains ignore_list: user_id={remove_id}")
                return
            ignore_ids.remove(remove_id)
            ignore_ids.append("")
            update_cells = worksheet.range(f"A1:A{len(ignore_ids)}")
            for i, cell in enumerate(update_cells):
                cell.value = ignore_ids[i]
            worksheet.update_cells(update_cells)
            await ctx.send("completed remove ignore_list!")

        if "show" in args:
            print(f"show ignore_list: sheet_id={sheet_id}, guild={ctx.guild.id}")
            await ctx.send(
                "\n".join([f"{user.display_name} {user.id}" for user in ignore_users])
            )


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
    print(
        f"{ctx.command} executor={ctx.author}, channel={ctx.channel}, time={datetime.datetime.now()}"
    )

    if ctx.author.bot:
        await ctx.send("this is bot")
        return

    async with ctx.typing():
        parsed = parse_args(args)

        if "manage" in parsed:
            await manage_mention_to_reaction_users(ctx, parsed)
            return

        if "message" not in parsed:
            await ctx.send("message parameter must be set.")
            return

        if "reaction" not in parsed:
            await ctx.send("reaction parameter must be set.")
            return

        try:
            message_id = int(parsed["message"])
        except Exception as e:
            print(e)
            await ctx.send(f"can not parse message_id. {args}")
            return

        print(f"fetch message: {message_id}")
        channel, message = await find_channel(ctx.guild, message_id)

        if channel is None:
            await ctx.send(f"not found channel, message_id={message_id}")
            return

        if message is None:
            await ctx.send(f"not found message, id={message_id}")
            return

        if "ignore_list" in parsed and parsed["ignore_list"].lower() == "false":
            ignore_ids = []
            print("skip ignore_list")
        else:
            sheet_id = os.environ["IGNORE_LIST_SHEET_ID"]
            workbook = gspread_client.open_by_key(sheet_id)
            worksheet = workbook.worksheet(str(ctx.guild.id))
            ignore_ids = worksheet.col_values(1)
            ignore_ids = [int(ignore_id) for ignore_id in ignore_ids]
            print(f"read ignore_list: {ignore_ids}")

        if parsed["reaction"].lower() == "none":
            targets = [
                member
                for member in channel.members
                if not member.bot
                and member.id != message.author.id
                and member.id not in ignore_ids
            ]
            print(
                f"find no reaction users: target={[member.display_name for member in targets]}"
            )
            result = await find_no_reaction_users(message, targets)
        else:
            emoji = parsed["reaction"]
            print(f"find reaction users: target={emoji}")
            result = await find_reaction_users(message, ignore_ids, emoji)

        if len(result) > 0:
            output_text = ", ".join([member.mention for member in result])
        else:
            output_text = "none!"

    print(f"send: {output_text}")
    await ctx.send(output_text)


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
    print(f"command executor={ctx.author}, time={datetime.datetime.now()}")
    if ctx.author.bot:
        await ctx.send("this is bot")
        return

    print(f"check arguments, {args}")
    if len(args) < 1:
        await ctx.send(
            "format is /download_messages_json channel={channel_id} before={YYYY-mm-dd} after={YYYY-mm-dd})"
        )
        return

    async with ctx.typing():
        parsed = parse_args(args)
        if "channel" not in parsed:
            await ctx.send("channel parameter must be set.")
            return

        try:
            channel_id = int(parsed["channel"])
        except Exception as e:
            print(e)
            await ctx.send("can not parse channel_id.")
            return

        print(f"fetch channel: {channel_id}")

        channel = ctx.guild.get_channel(channel_id)

        if channel is None:
            await ctx.send(f"not found channel, id={channel_id}")
            return

        if channel.type != ChannelType.text:
            await ctx.send(f"{channel.name} is not TextChannel: type={channel.type}")
            return

        try:
            before, after = parse_before_after(parsed)
        except Exception as e:
            print(e)
            await ctx.send(f"can not parse before/after: {e}")
            return

        print(f"read messages from history, after={after} before={before}")
        jst_timezone = datetime.timezone(datetime.timedelta(hours=+9), "JST")
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
                message['edited_at'] = message.edited_at.astimezone(jst_timezone)
            outputs.append(message_dict)

        filename = "messages.json"
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
            outputs = [
                f"#{channel.name}",
                after.strftime("%Y-%m-%d") + " ~ " + before.strftime("%Y-%m-%d"),
            ]
            await ctx.send("\n".join(outputs), file=discord.File(buffer, filename))


bot.run(token)
