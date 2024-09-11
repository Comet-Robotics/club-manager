from asgiref.sync import sync_to_async
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clubManager.settings')

import django
import discord
django.setup()

from django.core.mail import send_mail
from accounts.models import AccountLink
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
    await ctx.respond("Processing...", ephemeral=True, delete_after=3.0)

    author_id = ctx.author.id
    author_name = ctx.author.name

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
            import traceback
            traceback.print_exc(e)
            return None
    profile = await sync_to_async(get_profile)()

    if not profile:
        # Hopefully never happens
        await ctx.respond("Unhandled error: ProfileNotFound. Ping an officer for assistance!")
        return

    if profile.discord_id:
        if profile.discord_id == str(author_id):
            await ctx.respond("That Net ID is already linked to your account!", ephemeral=True)
        else:
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


    # NetID has been validated, generate the AccountLink and send the email!
    
    def create_account_link():
        return AccountLink.objects.create(user=user, link_type='discord', social_id=str(author_id))
    account_link = await sync_to_async(create_account_link)()

    email = f"{net_id}@utdallas.edu"
    await ctx.respond(f"Sending email to {email}...", ephemeral=True, delete_after=3.0)

    def send_the_email():
        send_mail(
            "Link your Discord to your Comet Robotics account",
f"""
Hello {user.first_name},

You have requested to link your Discord account with your Comet Robotics account.

Full Name: {user.first_name} {user.last_name}
Discord Name: {author_name}
NetID: {net_id}

If the above information is correct, click the button below:

-Button-

or click on this link: https://portal.cometrobotics.org/accounts/link/{account_link.uuid}

If the name is incorrect, contact an officer.

If this was not you, you can safely ignore this email.

Thanks!
""",
            "cometrobotics@utdallas.edu",
            [email],
            fail_silently=False,
        )
    await sync_to_async(send_the_email)()

    embed = discord.Embed(
        title="Email sent!",
        description=f"Check your email (`{email}`) and click the link to connect your Discord account to your Comet Robotics account.",  
        color=discord.Colour.red(),
    )

    await ctx.respond(":tada:", embed=embed, ephemeral=True)


bot.run(os.getenv("DISCORD_TOKEN"))

