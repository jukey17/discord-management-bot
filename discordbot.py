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
        return

    result = re.match(split_id_pattern, arg)
    if not result:
        return

    await ctx.send('channel={0}, message={1}'.format(result.group(1), result.group(2)))


bot.run(token)
