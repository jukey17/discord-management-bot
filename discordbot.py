from discord.ext import commands
import os
import re
import traceback

bot = commands.Bot(command_prefix='/')
token = os.environ['DISCORD_BOT_TOKEN']

split_id_pattern = '(\d+)-(\d+)'


@bot.event
async def on_command_error(ctx, error):
    orig_error = getattr(error, "original", error)
    error_msg = ''.join(traceback.TracebackException.from_exception(orig_error).format())
    await ctx.send(error_msg)


@bot.command()
async def ping(ctx):
    await ctx.send('pong')


@bot.command()
async def reaction_info(ctx, arg):
    if ctx.author.bot:
        await ctx.send('this is bot')
        return

    result = re.match(split_id_pattern, arg)
    if not result:
        await ctx.send("{channel_id}-{message_id}")
        return

    channel_id = int(result.group(1))
    message_id = int(result.group(2))
    await ctx.send('channel={0}, message={1}'.format(channel_id, message_id))

    # channels = [x for x in ctx.guild.text_channels if x.id == channel_id]
    # if len(channels) == 0:
    #     await ctx.send(f'not found channel={channel_id}')
    #     return
    # channel = channels[0]
    channel = ctx.guild.get_channel(channel_id)
    message = await channel.fetch_message(message_id)
    await ctx.send(f'channel={channel.name}, message={message.content}')


bot.run(token)
