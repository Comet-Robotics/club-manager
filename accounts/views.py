from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from .models import AccountLink
from core.models import UserProfile
import discord
from clubManager import settings
import requests

client = discord.Client()
logged_into_discord = False

class LinkSocialView(View):
    template_name = 'link_social.html'

    def get(self, request, uuid):
        global logged_into_discord
        account_link = get_object_or_404(AccountLink, uuid=uuid)
        user = account_link.user
        link_type = account_link.link_type
        social_id = account_link.social_id
        pfp = None
        username = None
        if link_type == 'discord':
            discord_id = int(account_link.social_id)
            socialUser = get_discord_user(discord_id, settings.DISCORD_TOKEN)
            if socialUser:
                username = socialUser['username']
                if 'avatar' in socialUser:
                    pfp = f"https://cdn.discordapp.com/avatars/{discord_id}/{socialUser['avatar']}.png"
        return render(request, self.template_name, {'user': user, 'link_type': link_type, 'social_id': social_id, 'pfp': pfp, 'username': username})

    def post(self, request, uuid):
        account_link = get_object_or_404(AccountLink, uuid=uuid)
        user = account_link.user
        user_profile, created = UserProfile.objects.get_or_create(user=user)
        link_type = account_link.link_type
        if (link_type == 'discord'):
            user_profile.discord_id = account_link.social_id
            user_profile.save()
        account_link.delete()

        return redirect('link_success')

class LinkSuccessView(View):
    template_name = 'link_success.html'

    def get(self, request):
        return render(request, self.template_name)


def get_discord_user(user_id, bot_token) -> dict | None:
    url = f"https://discord.com/api/v10/users/{user_id}"
    headers = {
        "Authorization": f"Bot {bot_token}"
    }
    
    response = requests.get(url, headers=headers)
    
    if not response.status_code == 200:
        return None
    
    user_data = response.json()
    return user_data