from django.shortcuts import render, redirect, get_object_or_404
from django.views import View

from accounts.discord import get_discord_user
from .models import AccountLink
from core.models import UserProfile
from clubManager import settings
from core.utilities import get_layout_data
import requests
from typing import TypedDict


class LinkSocialView(View):
    template_name = "link_social.html"

    def get(self, request, uuid):
        layout_data = get_layout_data(request)
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
                **layout_data,
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
        layout_data = get_layout_data(request)
        return render(request, self.template_name, {**layout_data})


