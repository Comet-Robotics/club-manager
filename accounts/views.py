from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from .models import AccountLink
from core.models import UserProfile
from clubManager import settings
import requests
from typing import TypedDict


class LinkSocialView(View):
    template_name = "link_social.html"

    def get(self, request, uuid):
        account_link = get_object_or_404(AccountLink, uuid=uuid)
        user = account_link.user
        link_type = account_link.link_type
        social_id = account_link.social_id
        profile_image = None
        username = None
        if link_type == "discord":
            discord_id = int(account_link.social_id)
            discord_user = get_discord_user(discord_id, settings.DISCORD_TOKEN)
            if discord_user:
                username = discord_user["username"]
                profile_image = discord_user["profile_image"]

        return render(
            request,
            self.template_name,
            {
                "user": user,
                "link_type": link_type,
                "social_id": social_id,
                "profile_image": profile_image,
                "username": username,
            },
        )

    def post(self, request, uuid):
        account_link = get_object_or_404(AccountLink, uuid=uuid)
        user = account_link.user
        user_profile, created = UserProfile.objects.get_or_create(user=user)
        link_type = account_link.link_type
        if link_type == "discord":
            user_profile.discord_id = account_link.social_id
            user_profile.save()
        account_link.delete()

        return redirect("link_success")


class LinkSuccessView(View):
    template_name = "link_success.html"

    def get(self, request):
        return render(request, self.template_name)


class DiscordUser(TypedDict):
    username: str
    discord_id: int
    profile_image: str


def get_discord_user(user_id: int, bot_token: str) -> DiscordUser | None:
    url = f"https://discord.com/api/v10/users/{user_id}"
    headers = {"Authorization": f"Bot {bot_token}"}

    response = requests.get(url, headers=headers)

    if not response.status_code == 200:
        return None

    user_data = response.json()

    discord_id = int(user_data["id"])
    discriminator = int(user_data["discriminator"]) or 0

    if "avatar" in user_data:
        profile_image = f"https://cdn.discordapp.com/avatars/{discord_id}/{user_data['avatar']}.png"
    else:
        discord_profile_image_index = ((discord_id >> 22) % 6) if discriminator == 0 else discriminator % 5
        profile_image = f"https://cdn.discordapp.com/embed/avatars/{discord_id}.png"

    return {"username": user_data["username"], "discord_id": discord_id, "profile_image": profile_image}
