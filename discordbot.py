import contextlib
import copy
import csv
import datetime
import io
import json
import os
import re
import traceback

import discord
from discord import ChannelType, Intents
from discord import User
from discord.ext import commands

intents = Intents.default()
intents.members = True
bot = commands.Bot(command_prefix='/', intents=intents)
token = os.environ['DISCORD_BOT_TOKEN']


class MessageCounter:
    def __init__(self, user: User):
        self.user = user
        self.counter = 0

    def try_increment(self, user: User):
        if self.user.id != user.id:
            return False
        self.counter += 1
        return True


def parse_args(args):
    parsed = {}
    for arg in args:
        result = re.match(r"(.*)=(.*)", arg)
        if result is None:
            parsed[arg] = 'True'
        else:
            parsed[result.group(1)] = result.group(2)

    return parsed


def parse_json(obj):
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    else:
        str(obj)


async def find_channel(guild, message_id):
    message = None
    result = None
    for channel in guild.channels:
        if channel.type != ChannelType.text:
            continue
        try:
            message = await channel.fetch_message(message_id)
        except Exception as e:
            print(f'channel={channel.name}, exception={e}')
        if message is not None:
            result = channel
            break
    return result, message


@bot.event
async def on_command_error(ctx, error):
    orig_error = getattr(error, "original", error)
    error_msg = ''.join(traceback.TracebackException.from_exception(orig_error).format())
    await ctx.send(error_msg)


@bot.command()
async def reaction_info(ctx, *args):
    print(f'check author is bot: author={ctx.author}')
    if ctx.author.bot:
        await ctx.send('this is bot')
        return

    print(f'check arguments: {args}')
    if len(args) < 1:
        await ctx.send('command format is /reaction_info message={message_id}')
        return

    parsed = parse_args(args)

    if 'message' not in parsed:
        await ctx.send('not found message_id')
        return

    message_id = int(parsed['message'])
    print(f'fetch message: {message_id}')
    channel, message = await find_channel(ctx.guild, message_id)
    message = await channel.fetch_message(message_id)

    if channel is None:
        await ctx.send(f'not found channel, message_id={message_id}')
        return

    if message is None:
        await ctx.send(f'not found message, id={message_id}')
        return

    if 'bot' in parsed:
        members = copy.copy(ctx.guild.members)
    else:
        members = [member for member in ctx.guild.members if not member.bot]
    no_reaction_members = copy.copy(members)

    for reaction in message.reactions:
        users = [user async for user in reaction.users()]
        print(f'count reaction: {reaction}')
        for member in members:
            for user in users:
                if member.id == user.id:
                    if member in members:
                        if member in no_reaction_members:
                            no_reaction_members.remove(member)

    print('output result')
    result = [f'"{channel.name} - {message.content}" reactions']
    for reaction in message.reactions:
        users = []
        async for user in reaction.users():
            users.append(user.name)
        result.append(f'{reaction}: ' + ', '.join(users))
    if len(no_reaction_members) > 0:
        result.append('no reaction=' + ', '.join([member.name for member in no_reaction_members]))

    await ctx.send('\n'.join(result))


@bot.command()
async def message_count(ctx, *args):
    print(f'check author is bot: author={ctx.author}')
    if ctx.author.bot:
        await ctx.send('this is bot')
        return

    print(f'check arguments, {args}')
    if len(args) < 1:
        await ctx.send('command format is /message_count channel={channel_id} '
                       'options...(before={YYYY-mm-dd} after={YYYY-mm-dd})')
        return

    parsed = parse_args(args)

    if 'channel' not in parsed:
        await ctx.send('not found channel_id')
        return

    channel_id = int(parsed['channel'])
    print(f'fetch channel: {channel_id}')
    channel = ctx.guild.get_channel(channel_id)

    if channel is None:
        await ctx.send(f'not found channel, id={channel_id}')
        return

    if channel.type != ChannelType.text:
        await ctx.send(f'not TextChannel, channel={channel.name}, type={channel.type}')
        return

    members = [member for member in ctx.guild.members if not member.bot]
    message_counters = [MessageCounter(member) for member in members]

    before = datetime.datetime.strptime(parsed['before'], '%Y-%m-%d')
    after = datetime.datetime.strptime(parsed['after'], '%Y-%m-%d')
    print(f'count from history, after={after} before={before}')
    async for message in channel.history(limit=None, before=before, after=after):
        for counter in message_counters:
            counter.try_increment(message.author)

    filename = 'message_counter.csv'
    print(f'create {filename} buffer')
    with contextlib.closing(io.StringIO()) as buffer:
        writer = csv.writer(buffer)
        writer.writerow(['name', 'count'])
        for counter in message_counters:
            writer.writerow([counter.user.display_name, counter.counter])

        print(f'send {filename}')
        buffer.seek(0)
        await ctx.send(file=discord.File(buffer, filename))


@bot.command()
async def download_messages_json(ctx, *args):
    print(f'check author is bot: author={ctx.author}')
    if ctx.author.bot:
        await ctx.send('this is bot')
        return

    print(f'check arguments, {args}')
    if len(args) < 1:
        await ctx.send('command format is /message_count channel={channel_id} '
                       'options...(before={YYYY-mm-dd} after={YYYY-mm-dd})')
        return

    parsed = parse_args(args)

    if 'channel' not in parsed:
        await ctx.send('not found channel_id')
        return

    channel_id = int(parsed['channel'])
    print(f'fetch channel: {channel_id}')
    channel = ctx.guild.get_channel(channel_id)

    if channel is None:
        await ctx.send(f'not found channel, id={channel_id}')
        return

    if channel.type != ChannelType.text:
        await ctx.send(f'not TextChannel, channel={channel.name}, type={channel.type}')
        return

    before = datetime.datetime.strptime(parsed['before'], '%Y-%m-%d')
    after = datetime.datetime.strptime(parsed['after'], '%Y-%m-%d')
    print(f'read messages from history, after={after} before={before}')
    outputs = []
    async for message in channel.history(limit=None, before=before, after=after):
        message_dict = dict(id=message.id, author=message.author.name, display_name=message.author.display_name,
                            created_at=message.created_at, edited_at=message.edited_at, message=message.content)
        outputs.append(message_dict)

    filename = 'messages.json'
    print(f'create {filename} buffer')
    with contextlib.closing(io.StringIO()) as buffer:
        json.dump(outputs, buffer, default=parse_json, indent=2, ensure_ascii=False)

        print(f'send {filename}')
        buffer.seek(0)
        await ctx.send(file=discord.File(buffer, filename))


bot.run(token)
