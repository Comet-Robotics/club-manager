from asgiref.sync import sync_to_async
import os


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "clubManager.settings")
from clubManager import settings

import django
import discord
from discord.ext import pages

django.setup()

from django.core.mail import send_mail
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from accounts.models import AccountLink
from core.models import User, UserProfile
from common.asyncutils import *
from common.utils import is_valid_net_id
from django.utils import timezone
from events.models import Attendance
from payments.models import Term
from datetime import datetime, time as dttime
import io
import subprocess
import socket
import random
import requests
from operator import itemgetter

LIST = [
    "Madina Halal Grill",
    "Zenna Thai & Japanese",
    "Zio Al's Pizza & Pasta",
    "Fat ni BBQ",
    "Cafe Brazil",
    "Biryaniify",
    "Bulldog Katsu",
    "LA Burger",
    "Torchy's Tacos",
    "Fuzzy's Tacos",
    "Velvet Taco",
    "Taco Bell",
    "Jimmy John's",
    "Chipotle",
    "Panera",
    "Potbelly",
    "Sky Rocket Burger",
    "Teriyaki Sensei",
    "Freebirds",
    "Unbelievabowl",
    "Pei Wei",
    "Masala Wok",
    "Little Greek",
    "Liberty Burger",
    "The Mango's Plano",
    "Bambu Thai",
    "Hawaiian Bros",
    "The String Bean",
    "Something new",
]

intents = discord.Intents.default()
intents.members = True
intents.presences = True
intents.message_content = True

bot = discord.Bot(intents=intents)

# -------- Utility methods --------


async def get_user_attendances(user_profile: UserProfile):
    def get_attendances():
        return sorted(Attendance.objects.filter(user=user_profile.user), key=lambda a: a.event.event_date, reverse=True)

    return await sync_to_async(get_attendances)()


async def respond_user_attendances(interaction: discord.Interaction, user_profile: UserProfile):
    attendances = await get_user_attendances(user_profile)

    def get_attended_events():
        return [a.event for a in attendances]

    events = await sync_to_async(get_attended_events)()
    ev_date_mapped = sorted(
        {
            date: list(filter(lambda e: date == e.event_date.date(), events))
            for date in set(map(lambda e: e.event_date.date(), events))
        }.items(),
        key=itemgetter(0),
        reverse=True,
    )
    attendance_strs = list(
        map(
            lambda de: (
                discord.utils.format_dt(datetime.combine(de[0], dttime.min), style="D")
                + "\n"
                + "\n".join(
                    map(lambda e: f"- **{e.event_name}**", sorted(de[1], key=lambda x: x.event_date, reverse=False))
                )
            ),
            ev_date_mapped,
        )
    )
    page_size = 8
    attendance_strs_paginated = [attendance_strs[i : i + page_size] for i in range(0, len(attendance_strs), page_size)]

    def make_embed(desc: str, **kwargs):
        return discord.Embed(
            title=f"{user_profile.user.get_short_name()}'s Attendances",
            color=discord.Color.blurple(),
            description=desc,
            **kwargs,
        )

    if not len(attendance_strs_paginated):
        await interaction.respond(embed=make_embed("No attendances found!"), ephemeral=True)
        return

    attendance_embeds = [
        make_embed(
            "\n\n".join(ls),
            footer=discord.EmbedFooter(
                text=f"Total: {len(events)}\nDays attended: {len(attendance_strs)}"
            ),  # TODO: weekly streak
        )
        for ls in attendance_strs_paginated
    ]
    paginator = pages.Paginator(attendance_embeds)
    await paginator.respond(interaction, ephemeral=True)


async def get_current_member_discord_ids():
    def run():
        current_term = Term.get_current_term()
        profiles = UserProfile.objects.exclude(discord_id__isnull=True)
        valid_ids: list[int] = []
        for profile in profiles:
            if profile.is_member(current_term)[1]:
                if profile.discord_id is not None:
                    valid_ids.append(int(profile.discord_id))
        return valid_ids

    return await sync_to_async(run)()


# -------- Bot commands --------


@bot.event
async def on_ready():
    print(f"{bot.user} is ready and online!")


@bot.slash_command(description="Link your Discord account to your Comet Robotics account")
@discord.option(name="net_id", description="Your UT Dallas Net ID", required=True, min_length=9, max_length=9)
async def link(ctx: discord.ApplicationContext, net_id: str):
    await ctx.respond("Processing...", ephemeral=True, delete_after=3.0)

    author_id = ctx.author.id
    author_name = ctx.author.name

    net_id = net_id.lower()
    if not is_valid_net_id(net_id):
        await ctx.respond("Invalid Net ID format!", ephemeral=True, delete_after=3.0)
        return

    user = await get_user_async(username=net_id)

    if user is None:
        # await ctx.respond("Your Net ID was not found in our database. If you're sure it's correct, use the `/create` command to create a new account with that Net ID.", ephemeral=True, delete_after=3.0)
        await ctx.respond(
            "Your Net ID was not found in our database. Contact an officer to get an account set up.",
            ephemeral=True,
            delete_after=3.0,
        )  # TODO
        return

    profile = await get_or_create_profile_async(user=user)

    if not profile:
        # Hopefully never happens
        await ctx.respond("Unhandled error: ProfileNotFound. Ping an officer for assistance!")
        return

    if profile.discord_id:
        if profile.discord_id == str(author_id):
            await ctx.respond("That Net ID is already linked to your account!", ephemeral=True)
        else:
            await ctx.respond(
                "That Net ID is already linked to a different Discord account. Ping an officer if this looks wrong.",
                ephemeral=True,
            )
        return

    discord_id_is_linked = (await get_profile_async(discord_id=author_id)) is not None

    if discord_id_is_linked:
        await ctx.respond(
            "Your Discord account is already linked to a Comet Robotics account. Ping an officer if this looks wrong.",
            ephemeral=True,
        )
        return

    # NetID has been validated, generate the AccountLink and send the email!

    def create_account_link():
        return AccountLink.objects.create(user=user, link_type="discord", social_id=str(author_id))

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
Net ID: {net_id}

If the above information is correct, click on the below link to connect your Discord account to your Comet Robotics account.

https://portal.cometrobotics.org/accounts/link/{account_link.uuid}

If the name is incorrect, reply to this email and we'll get back to you. If this was not you, you can safely ignore this email.

Thanks!
""",
            "cometrobotics@utdallas.edu",
            [email],
            fail_silently=False,
            html_message=f"""
<h2>Hello {user.first_name},</h2>

<p>You have requested to link your Discord account with your Comet Robotics account.</p>

<p>Full Name: {user.first_name} {user.last_name}<br>
Discord Name: {author_name}<br>
Net ID: {net_id}</p>


<p>If the above information is correct, click the button below or the link to connect your Discord account to your Comet Robotics account.</p>

<a href="https://portal.cometrobotics.org/accounts/link/{account_link.uuid}"><button style="border: solid #950000 3px;padding: 1em; border-radius: 10px; background-color:#bf1e2e; color: white;"><strong>Link Account</strong></button></a>

<br><br><a href="https://portal.cometrobotics.org/accounts/link/{account_link.uuid}">https://portal.cometrobotics.org/accounts/link/{account_link.uuid}</a>

<p>If the name is incorrect, reply to this email and we'll get back to you. If this was not you, you can safely ignore this email.</p>

<p>Thanks!</p>
""",
        )

    await sync_to_async(send_the_email)()

    embed = discord.Embed(
        title="Email sent!",
        description=f"Check your email (`{email}`) and click the link to connect your Discord account to your Comet Robotics account.",
        color=discord.Color.red(),
    )

    await ctx.respond(":tada:", embed=embed, ephemeral=True)


@bot.slash_command(description="View your Comet Robotics profile")
async def profile(ctx: discord.ApplicationContext):
    user = ctx.author
    user_profile: UserProfile | None = await get_profile_async(discord_id=str(user.id))
    if user_profile is None:
        await ctx.respond(
            "You don't have a linked Comet Robotics account. Use the `/link` command to connect your Comet Robotics account to your Discord account.",
            ephemeral=True,
        )
        return

    def get_basic_info(user_profile: UserProfile):
        return f"""
**Full Name:** {user_profile.user.first_name} {user_profile.user.last_name}
**Net ID:** {user_profile.user.username}
**Gender:** {UserProfile.GenderChoice(user_profile.gender).label if user_profile.gender else "Not specified"}
"""

    basic_info = await sync_to_async(get_basic_info)(user_profile)

    # Membership Status
    def get_membership_status(user_profile: UserProfile):
        current_term, current_payment = user_profile.is_member()
        body = "**Current Membership:** " + (
            "Not a member" if not current_payment else f"Active for {current_term.name}"
        )

        past_terms: list[Term] = Term.objects.filter(end_date__lte=timezone.now())
        future_terms: list[Term] = Term.objects.filter(start_date__gte=timezone.now()).exclude(pk=current_term.pk)

        paid_future_terms = [term for term in future_terms if user_profile.is_member(term)[1]]
        if len(paid_future_terms) > 0:
            body += f"\n**Dues paid for future term(s)**: {', '.join([t.name for t in paid_future_terms])}"

        paid_past_terms = [term.name for term in past_terms if user_profile.is_member(term)[1]]
        past_terms_info = ", ".join(paid_past_terms) if len(paid_past_terms) > 0 else "No past memberships"

        body += f"\n**Past Memberships:** {past_terms_info}"

        return (
            body,
            f"https://portal.cometrobotics.org/payments/{current_term.product.id}/pay" if not current_payment else None,
            current_term.name,
        )

    membership_status, due_paying_url, term_name = await sync_to_async(get_membership_status)(user_profile)

    embed = discord.Embed(title="Your Comet Robotics Profile", color=discord.Color.red())
    embed.add_field(name="Basic Info", value=basic_info, inline=False)
    embed.add_field(name="Membership Status", value=membership_status, inline=False)

    await ctx.respond(embed=embed, ephemeral=True, view=ProfileActionsView(term_name, due_paying_url, user_profile))


class ProfileActionsView(discord.ui.View):
    def __init__(self, term_name: str, due_paying_url: str | None, user_profile: UserProfile) -> None:
        super().__init__()
        self.user_profile = user_profile
        self.add_item(
            discord.ui.Button(
                label=f"Pay Dues for {term_name}" if due_paying_url else f"Dues paid for {term_name} :)",
                url=due_paying_url or "https://cometrobotics.org",
                disabled=not due_paying_url,
            )
        )

        # # TODO: Implement interaction for gender
        # discord_gender = [discord.SelectOption(label=str(obj._name_), value=str(obj)) for obj in UserProfile.GenderChoice]
        # self.add_item(discord.ui.Select(placeholder="Edit Gender...", options=discord_gender))

    @discord.ui.button(label="View Attendances", style=discord.ButtonStyle.primary)
    async def view_attendances(self, button, interaction: discord.Interaction):
        await respond_user_attendances(interaction, self.user_profile)

    @discord.ui.button(label="Edit Profile (WIP)", style=discord.ButtonStyle.primary, disabled=True)
    async def edit_profile(self, button, interaction: discord.Interaction):
        await interaction.response.send_modal(ProfileEditView(user_profile=self.user_profile))


class ProfileEditView(discord.ui.Modal):
    def __init__(self, user_profile: UserProfile, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs, title="Edit Profile")

        self.user_profile = user_profile

        self.first_name = discord.ui.InputText(
            label="First Name", value=user_profile.user.first_name, required=True, style=discord.InputTextStyle.short
        )
        self.last_name = discord.ui.InputText(
            label="Last Name", value=user_profile.user.last_name, required=True, style=discord.InputTextStyle.short
        )

        # People should not be able to change name without talking to us - Colin
        # self.add_item(self.first_name)
        # self.add_item(self.last_name)

    async def callback(self, interaction: discord.Interaction):
        making_new_profile = self.user_profile is None

        def run():
            if making_new_profile:
                user, created_user = User.objects.get_or_create(username=self.net_id.value)
                self.user_profile = UserProfile.objects.create(user=user)

            if self.user_profile:
                self.user_profile.user.first_name = self.first_name.value or ""
                self.user_profile.user.last_name = self.last_name.value or ""
                self.user_profile.user.save()

        await interaction.response.defer(ephemeral=True)
        await sync_to_async(run)()


@bot.slash_command(description="View your meeting attendances")
async def attendances(ctx: discord.ApplicationContext):
    user = ctx.author
    user_profile: UserProfile | None = await get_profile_async(discord_id=str(user.id))
    if user_profile is None:
        await ctx.respond(
            "You don't have a linked Comet Robotics account. Use the `/link` command to connect your Comet Robotics account to your Discord account.",
            ephemeral=True,
        )
        return

    await respond_user_attendances(ctx.interaction, user_profile)


# TODO: /create - should send a confirmation email before creating account (extra impl for /accounts/link endpoint?)


@bot.slash_command(description="Get the current version of the bot")
async def version(ctx: discord.ApplicationContext):
    """
    Returns the current version of the bot.

    NOTE: This command should only be accessible to org leaders (people with the Team Lead, Project Manager, or Officer roles). This needs to be configured manually in Discord server settings > Integrations.
    """
    try:
        commit_hash = subprocess.check_output(["git", "rev-parse", "HEAD"]).strip().decode("utf-8")
        commit_message = subprocess.check_output(["git", "log", "-1", "--pretty=%B"]).strip().decode("utf-8")
        hostname = socket.gethostname()

        embed = discord.Embed(title="Bot Version Information", color=discord.Color.red())
        embed.add_field(name="Commit Hash", value=commit_hash, inline=False)
        embed.add_field(name="Commit Message", value=commit_message, inline=False)
        embed.add_field(name="Hostname", value=hostname, inline=False)

        await ctx.respond(embed=embed, ephemeral=True)
    except Exception as e:
        await ctx.respond(f"An error occurred while fetching version information: {str(e)}", ephemeral=True)


@bot.slash_command(description="Pay your member dues to become a Comet Robotics member")
async def pay(ctx: discord.ApplicationContext):
    def get_payment_links():
        try:
            user = UserProfile.objects.get(discord_id=str(ctx.author.id))
        except:
            return None
        active_terms = Term.objects.filter(end_date__gte=timezone.now())
        if not active_terms:
            # ctx.respond("No active terms available for payment.",  ephemeral=True)  # TODO: move to separate func to await
            pass

        payment_links = [
            (
                f"[Pay for {term.name}](https://portal.cometrobotics.org/payments/{term.product.id}/pay/)"
                + (" (you've already paid this term's dues)" if user.is_member(term)[1] else "")
            )
            for term in active_terms
        ]
        return "\n".join(payment_links)

    payment_links = await sync_to_async(get_payment_links)()

    if payment_links is None:
        await ctx.respond(
            "You're not linked yet! Use `/link` with your NetID to link your Discord account to your Comet Robotics account, then try again.",
            ephemeral=True,
        )
        return

    embed = discord.Embed(title="Become a Comet Robotics Member", description=payment_links, color=discord.Color.red())
    embed.set_footer(text="Click on the links to pay for the respective terms.")

    await ctx.respond(embed=embed, ephemeral=True)


async def add_role_unchecked(member_id: int | str):
    print("method execute")
    guild = bot.get_guild(settings.DISCORD_SERVER_ID)
    member_role = guild.get_role(settings.DISCORD_MEMBER_ROLE_ID)
    member = guild.get_member(int(member_id))
    if member:
        await member.add_roles(member_role)
    else:
        print(f"could not find member with id {member_id}")


@bot.event
async def on_member_join(member: discord.Member):
    def is_profile_valid():
        profile = UserProfile.objects.filter(discord_id=str(member.id)).first()
        return profile and profile.is_member()[1]

    profile_valid = await sync_to_async(is_profile_valid)()
    if profile_valid:
        await add_role_unchecked(member.id)


# TODO: signals don't work in here
# @receiver(post_save, sender=UserProfile)
# async def update_roles_profile_signal(sender, instance: UserProfile, created, **kwargs):
#     if (discord_id:=instance.discord_id) and instance.is_member()[1]:
#         await add_role_unchecked(discord_id)

# @receiver(post_save, sender=Payment)
# async def update_roles_payment_signal(sender, instance: Payment, created, **kwargs):
#     if (discord_id:=instance.user.userprofile.discord_id) and instance.user.userprofile.is_member()[1]:
#         await add_role_unchecked(discord_id)


@bot.slash_command(description="Give member roles to paid members")
async def givememberroles(ctx: discord.ApplicationContext):
    guild = bot.get_guild(settings.DISCORD_SERVER_ID)
    member_role = guild.get_role(settings.DISCORD_MEMBER_ROLE_ID)

    message = await ctx.respond("Processing...")

    ids_to_add = await get_current_member_discord_ids()
    for discord_id in ids_to_add:
        member = guild.get_member(discord_id)
        await member.add_roles(member_role)

    await message.edit_original_response(
        content=f"Member role addition success! Added member role to {len(ids_to_add)} users."
    )


@bot.slash_command(description="Purge member roles from non-paying members")
async def purgememberroles(ctx: discord.ApplicationContext):
    guild = bot.get_guild(settings.DISCORD_SERVER_ID)
    member_role = guild.get_role(settings.DISCORD_MEMBER_ROLE_ID)

    message = await ctx.respond("Processing...")

    removed_count = 0
    discord_members = guild.members
    valid_members = await get_current_member_discord_ids()
    for discord_member in discord_members:
        if discord_member.id not in valid_members:
            removed_count += 1
            await discord_member.remove_roles(member_role)

    await message.edit_original_response(
        content=f"Member role purge success! Removed member role for {removed_count} users."
    )


class ListView(discord.ui.View):
    @discord.ui.button(label="I'm Feeling Lucky!", style=discord.ButtonStyle.primary, emoji="🎲")
    async def button_callback(self, button, interaction):
        randomChoice = random.choice(LIST)
        await interaction.response.send_message(randomChoice, ephemeral=True, delete_after=10.0)


@bot.slash_command(description="View THE LIST")
async def thelist(ctx: discord.ApplicationContext):
    embed = discord.Embed(title="The List", description="\n".join(LIST), color=discord.Color.red())

    await ctx.respond(embed=embed, view=ListView(), ephemeral=True, delete_after=60.0)


@bot.slash_command(description="View the printers")  # TODO: change to the Makerspace
async def camera(ctx: discord.ApplicationContext):
    message = await ctx.respond("Processing...", ephemeral=True)

    valid_members = await get_current_member_discord_ids()
    if ctx.author.id not in valid_members:
        await message.edit_original_response(content=f"You are not registered as a member of Comet Robotics!")
    else:
        # url = "http://eric1:8080/stream" # TODO: probably /snapshot instead of /stream
        url = "http://192.168.1.64:8080/snapshot"
        img = discord.File(io.BytesIO(requests.get(url).content), "stream.jpg")
        await message.edit_original_response(content="", file=img)


bot.run(settings.DISCORD_TOKEN)
