import functools
import discord
from clubManager import settings
import asyncio

intents = discord.Intents.default()
intents.members = True
intents.presences = True
intents.message_content = True

__all__ = ["get_client", "add_member_role"]

client = discord.Client(intents=intents)
logged_in = False


async def login():
    global logged_in, client
    await client.start(settings.DISCORD_TOKEN)
    await client.wait_until_ready()  # TODO: hangs
    logged_in = True


async def get_client():
    global logged_in, client
    if not logged_in:
        await login()
    return client


async def add_member_role(dcord: discord.Client | discord.Bot, member_id: int | str):
    guild = dcord.get_guild(settings.DISCORD_SERVER_ID)
    member_role = guild.get_role(settings.DISCORD_MEMBER_ROLE_ID)
    member = guild.get_member(int(member_id))
    if member:
        await member.add_roles(member_role)
    else:
        print(f"could not find member with id {member_id}")
