import discord
import discord.abc


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
        except Exception as e:
            print(f"channel={channel.name}, exception={e}")
        if message is not None:
            result = channel
            break
    return result, message
