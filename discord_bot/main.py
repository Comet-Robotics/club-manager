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

@bot.slash_command(name="please", description="A simple hello command")
async def please(ctx: discord.ApplicationContext):
    embed = discord.Embed(
        title="My Amazing Embed",
        description="Embeds are super easy, barely an inconvenience.",
        color=discord.Colour.blurple(), # Pycord provides a class with default colors you can choose from
    )
    embed.add_field(name="A Normal Field", value="A really nice field with some information. **The description as well as the fields support markdown!**")

    embed.add_field(name="Inline Field 1", value="Inline Field 1", inline=True)
    embed.add_field(name="Inline Field 2", value="Inline Field 2", inline=True)
    embed.add_field(name="Inline Field 3", value="Inline Field 3", inline=True)
 
    embed.set_footer(text="Footer! No markdown here.") # footers can have icons too
    embed.set_author(name="Pycord Team", icon_url="https://example.com/link-to-my-image.png")
    embed.set_thumbnail(url="https://example.com/link-to-my-thumbnail.png")
    embed.set_image(url="https://example.com/link-to-my-banner.png")
 
    await ctx.respond("Hello! Here's a cool embed.", embed=embed, ephemeral=True)
 
bot.run(os.getenv("DISCORD_TOKEN"))

# TODO: need a way to either start this alongside the django server, or create a separate systemd service for it
# now that i think about it, running along side django might be weird because the web server (gunicorn?) does some stuff with threads and i don't know if that means we end up running N instances of the bot or not. separate service might be easier idk