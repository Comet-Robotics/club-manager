from asgiref.sync import sync_to_async
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clubManager.settings')

import django
import discord
django.setup()

from posters.models import Campaign
from core.models import User, UserProfile

bot = discord.Bot()

@bot.event
async def on_ready():
    print(f"{bot.user} is ready and online!")

@bot.slash_command(description="Link your Discord account to your Comet Robotics account")
@discord.option(name="net_id", description="Your UT Dallas Net ID", required=True, min_length=9, max_length=9)
async def link(
    ctx: discord.ApplicationContext, 
    net_id: str
):
    await ctx.respond("Processing...", ephemeral=True)

    author_id = ctx.author.id

    # TODO: Implement this lol

    if not (net_id[:3].isalpha() and net_id[3:].isdigit()):
        await ctx.respond("Invalid NetID format!")
        return

    def get_user():
        try:
            return User.objects.get(username=net_id)
        except:
            return None
    user = await sync_to_async(get_user)()

    if user is None:
        await ctx.respond("NetID not found!")
        return

    def get_profile():
        try:
            return UserProfile.objects.get_or_create(user=user)[0]
        except Exception as e:
            return None
    profile = await sync_to_async(get_profile)()

    if not profile:
        await ctx.respond("Unhandled error: ProfileNotFound")
        return

    if profile.discord_id:
        await ctx.respond("That Net ID is already linked to a different Discord account. Ping an officer if this looks wrong.", ephemeral=True)
        return

    def is_discord_linked():
        try:
            return UserProfile.objects.get(discord_id=author_id) is not None
        except:
            return False
    discord_id_is_linked = await sync_to_async(is_discord_linked)()

    if discord_id_is_linked:
        await ctx.respond("This Discord account is already linked to a Comet Robotics account. Ping an officer if this looks wrong.", ephemeral=True)
        return

    email = f"{net_id}@utdallas.edu"
    await ctx.respond(f"Sending email to {email}...", ephemeral=True)

    # TODO: send email

    embed = discord.Embed(
        title="Email sent!",
        description=f"Check your email (`{email}`) and click the link to connect your Discord account to your Comet Robotics account.",  
        color=discord.Colour.red(),
    )

    await ctx.respond(":tada:", embed=embed, ephemeral=True)

    # TODO: move linking
    profile.discord_id = ctx.author.id
    await sync_to_async(profile.save)()
    await ctx.respond("linked...", ephemeral=True)


bot.run(os.getenv("DISCORD_TOKEN"))

# TODO: need a way to either start this alongside the django server, or create a separate systemd service for it
# now that i think about it, running along side django might be weird because the web server (gunicorn?) does some stuff with threads and i don't know if that means we end up running N instances of the bot or not. separate service might be easier idk
