import contextlib
import copy
import csv
import datetime
import io
import json
import os
import pathlib
import re
import traceback

import discord
from discord import User, ChannelType, Intents, Guild, Message, File
from discord.abc import GuildChannel
from discord.ext import commands

intents = Intents.default()
intents.members = True
bot = commands.Bot(command_prefix='/', intents=intents)
token = os.environ['DISCORD_BOT_TOKEN']


class MessageCounter:
    def __init__(self, user: User, channel: GuildChannel):
        self.user = user
        self.channel = channel
        self.count = 0

    def __str__(self):
        return f'user=[{self.user}], channel=[{self.channel}], count={self.count}'

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
        return f'{self.to_dict()}'

    def add(self, channel: GuildChannel, count: int):
        self.result_map[channel] = count

    def to_dict(self):
        output = {'user': self.user.display_name}
        for channel, count in self.result_map.items():
            output[channel.name] = count
        return output


def parse_args(args):
    parsed = {}
    for arg in args:
        result = re.match(r"(.*)=(.*)", arg)
        if result is None:
            parsed[arg] = 'True'
        else:
            parsed[result.group(1)] = result.group(2)

    return parsed


def parse_before_after(args: dict):
    before = None
    after = None
    if 'before' in args:
        before = datetime.datetime.strptime(args['before'], '%Y-%m-%d')
    if 'after' in args:
        after = datetime.datetime.strptime(args['after'], '%Y-%m-%d')

    if after is not None and before is not None and after > before:
        raise ValueError('before must be a future than after.')

    return before, after


def parse_json(obj):
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
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
            print(f'channel={channel.name}, exception={e}')
        if message is not None:
            result = channel
            break
    return result, message


async def count_messages(guild: Guild, channel_id: int, before: datetime.datetime, after: datetime.datetime):
    print(f'fetch channel: {channel_id}')
    channel = guild.get_channel(channel_id)

    if channel is None:
        raise ValueError(f'not found channel: id={channel_id}')

    if channel.type != ChannelType.text:
        raise TypeError(f'{channel.name} is not TextChannel: type={channel.type}')

    message_counters = [MessageCounter(member, channel) for member in guild.members if not member.bot]

    print(f'count from history, after={after} before={before}')
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


async def manage_mention_no_reaction_users(ctx, args):
    print('manage mode')

    if 'ignore_list' in args:
        path = pathlib.Path(f'./.ignore_list/{ctx.guild.id}')
        path.mkdir(parents=True, exist_ok=True)
        path.touch(exist_ok=True)

        if 'download' in args:
            print(f'download ignore_list: {path}')
            with open(path, 'r') as file:
                await ctx.send(file=File(file, f'ignore_list_{ctx.guild.id}'))

        if 'upload' in args:
            print(f'upload ignore_list: {path}')
            try:
                with open(path, 'w') as file:
                    ctx.message.attachments[0].save(file)
            except Exception as e:
                print(e)
                await ctx.send(f'failed upload ignore_list: {e}')

            await ctx.send('completed upload ignore_list!')

        if 'append' in args:
            print(f'append ignore_list: {path}')
            try:
                with open(path, 'a') as file:
                    file.write(args['append'] + '\n')
            except Exception as e:
                print(e)
                await ctx.send(f'failed append ignore_list: {e}')

            await ctx.send('completed append ignore_list!')

        if 'remove' in args:
            print(f'remove ignore_list: {path}')
            try:
                with open(path, 'w') as file:
                    ignore_list = file.readlines()
                    ignore_list.remove(args['remove'])
            except Exception as e:
                print(e)
                await ctx.send(f'failed remove ignore_list: {e}')

            await ctx.send('completed remove ignore_list!')


@bot.event
async def on_command_error(ctx, error):
    orig_error = getattr(error, "original", error)
    error_msg = ''.join(traceback.TracebackException.from_exception(orig_error).format())
    await ctx.send(error_msg)


@bot.command()
async def mention_no_reaction_users(ctx, *args):
    print(f'{ctx.command} executor={ctx.author}, channel={ctx.channel}, time={datetime.datetime.now()}')

    dir_path = pathlib.Path(f'./.ignore_list')
    dir_path.mkdir(parents=True, exist_ok=True)

    if ctx.author.bot:
        await ctx.send('this is bot')
        return

    async with ctx.typing():
        parsed = parse_args(args)

        if 'manage' in parsed:
            await manage_mention_no_reaction_users(ctx, parsed)
            return

        if 'message' not in parsed:
            await ctx.send('message parameter must be set.')
            return

        try:
            message_id = int(parsed['message'])
        except Exception as e:
            print(e)
            await ctx.send(f'can not parse message_id. {args}')
            return

        print(f'fetch message: {message_id}')
        channel, message = await find_channel(ctx.guild, message_id)

        if channel is None:
            await ctx.send(f'not found channel, message_id={message_id}')
            return

        if message is None:
            await ctx.send(f'not found message, id={message_id}')
            return

        path = pathlib.Path(f'./.ignore_list/{ctx.guild.id}')
        path.touch(exist_ok=True)
        with open(path, 'r') as file:
            ignore_ids = [int(line) for line in file.readlines()]
            print(f'read ignore_list: {ignore_ids}')

        no_reaction_members = [member for member in channel.members if not member.bot and member.id not in ignore_ids]
        print(f'target users: {[member.id for member in no_reaction_members]}')

        for reaction in message.reactions:
            users = [user async for user in reaction.users()]
            print(f'count reaction: {reaction}')
            for member in ctx.guild.members:
                if member not in no_reaction_members:
                    continue
                for user in users:
                    if member.id == user.id:
                        no_reaction_members.remove(member)

        if len(no_reaction_members) > 0:
            result = 'no reaction: ' + ', '.join([member.mention for member in no_reaction_members])
        else:
            result = 'all member reaction!'

    print(f'send: {result}')
    await ctx.send(result)


@bot.command()
async def reaction_info(ctx, *args):
    print(f'command executor={ctx.author}, time={datetime.datetime.now()}')
    if ctx.author.bot:
        await ctx.send('this is bot')
        return

    print(f'check arguments: {args}')
    if len(args) < 1:
        await ctx.send('command format is /reaction_info message={message_id}')
        return

    async with ctx.typing():
        parsed = parse_args(args)

        if 'message' not in parsed:
            await ctx.send('message parameter must be set.')
            return

        try:
            message_id = int(parsed['message'])
        except Exception as e:
            print(e)
            await ctx.send(f'can not parse message_id. {args}')
            return

        print(f'fetch message: {message_id}')
        channel, message = await find_channel(ctx.guild, message_id)

        if channel is None:
            await ctx.send(f'not found channel, message_id={message_id}')
            return

        if message is None:
            await ctx.send(f'not found message, id={message_id}')
            return

        if 'bot' in parsed:
            members = ctx.guild.members
        else:
            members = [member for member in ctx.guild.members if not member.bot]
        no_reaction_members = copy.copy(members)

        for reaction in message.reactions:
            users = [user async for user in reaction.users()]
            print(f'count reaction: {reaction}')
            for member in members:
                if member not in no_reaction_members:
                    continue
                for user in users:
                    if member.id == user.id:
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
    print(f'command executor={ctx.author}, time={datetime.datetime.now()}')
    if ctx.author.bot:
        await ctx.send('this is bot')
        return

    print(f'check arguments, {args}')
    if len(args) < 1:
        await ctx.send('format is /message_count channel={channel_id} before={YYYY-mm-dd} after={YYYY-mm-dd}')
        return

    async with ctx.typing():
        parsed = parse_args(args)

        if 'channel' in parsed and 'channels' in parsed:
            await ctx.send('cannot pass both channel and channels parameter to /message_count.')
            return

        if 'channel' not in parsed and 'channels' not in parsed:
            await ctx.send('channel or channels parameter must be set.')
            return

        channel_ids = []
        try:
            if 'channel' in parsed:
                channel_ids.append(int(parsed['channel']))
            if 'channels' in parsed:
                channel_ids.extend([int(channel_id) for channel_id in parsed['channels'].split(',')])
        except Exception as e:
            print(e)
            await ctx.send(f'can not parse channel_id/channel_ids: {e}')
            return

        print(f'parse channel_ids, {channel_ids}')

        try:
            before, after = parse_before_after(parsed)
        except Exception as e:
            print(e)
            await ctx.send(f'can not parse before/after: {e}')
            return

        result_map = {}
        for channel_id in channel_ids:
            try:
                channel, message_counters = await count_messages(ctx.guild, channel_id, before, after)
            except Exception as e:
                await ctx.send(f'cannot count messages: {e}')
                return
            result_map[channel] = message_counters
        results = convert_to_message_count_result(result_map)

        filename = 'number_of_messages_in_channels.csv'
        print(f'create {filename} buffer')
        with contextlib.closing(io.StringIO()) as buffer:
            fieldnames = ['user']
            fieldnames.extend([key.name for key in result_map.keys()])
            writer = csv.DictWriter(buffer, fieldnames)
            writer.writeheader()
            for user_id, result in results.items():
                writer.writerow(result.to_dict())
            buffer.seek(0)

            print(f'send {filename}')
            await ctx.send(file=discord.File(buffer, filename))


@bot.command()
async def download_messages_json(ctx, *args):
    print(f'command executor={ctx.author}, time={datetime.datetime.now()}')
    if ctx.author.bot:
        await ctx.send('this is bot')
        return

    print(f'check arguments, {args}')
    if len(args) < 1:
        await ctx.send('format is /download_messages_json channel={channel_id} before={YYYY-mm-dd} after={YYYY-mm-dd})')
        return

    async with ctx.typing():
        parsed = parse_args(args)
        if 'channel' not in parsed:
            await ctx.send('channel parameter must be set.')
            return

        try:
            channel_id = int(parsed['channel'])
        except Exception as e:
            print(e)
            await ctx.send('can not parse channel_id.')
            return

        print(f'fetch channel: {channel_id}')
        channel = ctx.guild.get_channel(channel_id)

        if channel is None:
            await ctx.send(f'not found channel, id={channel_id}')
            return

        if channel.type != ChannelType.text:
            await ctx.send(f'{channel.name} is not TextChannel: type={channel.type}')
            return

        try:
            before, after = parse_before_after(parsed)
        except Exception as e:
            print(e)
            await ctx.send(f'can not parse before/after: {e}')
            return

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
            buffer.seek(0)
            print(f'send {filename}')
            outputs = [f'#{channel.name}', after.strftime('%Y-%m-%d') + ' ~ ' + before.strftime('%Y-%m-%d')]
            await ctx.send('\n'.join(outputs), file=discord.File(buffer, filename))


bot.run(token)
