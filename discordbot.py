import os
import traceback
import discord

from discord.ext import commands

from commands.download_messages_json import DownloadMessagesJsonCommand
from commands.mention_to_reaction_users import MentionToReactionUsersCommand
from commands.message_count import MessageCountCommand

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="/", intents=intents)
bot.load_extension("dispander")
token = os.environ["DISCORD_BOT_TOKEN"]

message_count_command = MessageCountCommand()
mention_to_reaction_users_command = MentionToReactionUsersCommand()
download_messages_json_command = DownloadMessagesJsonCommand()


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
    await message_count_command.execute(ctx, args)


@bot.command()
async def download_messages_json(ctx, *args):
    await download_messages_json_command.execute(ctx, args)


bot.run(token)
