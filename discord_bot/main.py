import os
# from ..clubManager.settings import *
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clubManager.settings')
import django
import discord
# django.setup()

bot = discord.Bot()

@bot.event
async def on_ready():
    print(f"{bot.user} is ready and online!")

@bot.slash_command(description="Link your Discord account to your Comet Robotics account")
async def link(ctx: discord.ApplicationContext, net_id: discord.Option(str, description="Your UT Dallas Net ID", required=True, min_length=9, max_length=9)):
    ctx.respond("Processing...", ephemeral=True)

    # TODO: Implement this lol

    net_id_is_in_db = True

    if not net_id_is_in_db:
        return

    net_id_is_linked = False

    if net_id_is_linked:
        await ctx.respond("That Net ID is already linked to a Discord account. Ping an officer if this looks wrong.", ephemeral=True)
        return

    discord_id_is_linked = False
    
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

 
bot.run(os.getenv("DISCORD_TOKEN"))

# TODO: need a way to either start this alongside the django server, or create a separate systemd service for it
# now that i think about it, running along side django might be weird because the web server (gunicorn?) does some stuff with threads and i don't know if that means we end up running N instances of the bot or not. separate service might be easier idk