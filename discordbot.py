from discord.ext import commands
import copy
import os
import re
import traceback

bot = commands.Bot(command_prefix='/')
token = os.environ['DISCORD_BOT_TOKEN']

split_id_pattern = r"(\d+) (\d+)"


class ReactionInfo:
    def __init__(self, reaction, user):
        self.reaction = reaction
        self.user = user

@bot.event
async def on_command_error(ctx, error):
    orig_error = getattr(error, "original", error)
    error_msg = ''.join(traceback.TracebackException.from_exception(orig_error).format())
    await ctx.send(error_msg)


@bot.command()
async def reaction_info(ctx, arg):
    if ctx.author.bot:
        await ctx.send('this is bot')
        return

    result = re.match(split_id_pattern, arg)
    if not result:
        await ctx.send("please format is /reaction_info {channel_id} {message_id}")
        return

    channel_id = int(result.group(1))
    message_id = int(result.group(2))

    guild = ctx.guild
    channel = guild.get_channel(channel_id)
    message = await channel.fetch_message(message_id)
    await ctx.send(f'channel={channel.name}, message={message.content}')

    members = copy.copy(guild.members)
    for member in guild.members:
        for reaction in message.reactions:
            async for user in reaction.users():
                if member.id == user.id:
                    members.remove(member)
                    await ctx.send(f'reaction={reaction}, user={user}')

    for member in members:
        await ctx.send(f'no reaction={member}')

@bot.command()
async def get_message_count(ctx, arg):
    if ctx.author.bot:
        await ctx.send('this is bot')
        return

    async for entry in ctx.guild.audit_logs(limit=None, user=ctx.author):
        await ctx.send(f'entry={entry}')

bot.run(token)
