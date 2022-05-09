import os
import traceback
import discord

from discord.ext import commands

intents = discord.Intents.default()
intents.members = True
intents.voice_states = True
bot = commands.Bot(command_prefix="/", intents=intents)
bot.load_extension("dispander")
bot.load_extension("cogs.message_count")
bot.load_extension("cogs.emoji_count")
bot.load_extension("cogs.download_messages_json")
bot.load_extension("cogs.mention_to_reaction_users")
bot.load_extension("cogs.logging_voice_states")
token = os.environ["DISCORD_BOT_TOKEN"]


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


bot.run(token)
