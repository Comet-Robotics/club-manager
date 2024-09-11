from django.shortcuts import render, redirect
from django.views import View
from .models import AccountLink
from core.models import UserProfile
import discord
from clubManager import settings

client = discord.Client()
logged_into_discord = False

class LinkSocialView(View):
    template_name = 'link_social.html'

    async def get(self, request, uuid):
        global logged_into_discord
        account_link = AccountLink.objects.get(uuid=uuid)
        user = account_link.user
        link_type = account_link.link_type
        social_id = account_link.social_id
        pfp = None
        username = None
        if link_type == 'discord':
            if not logged_into_discord:
                await client.login(settings.DISCORD_TOKEN)
                logged_into_discord = True
            discord_id = int(account_link.social_id)
            user = await client.fetch_user(discord_id) 
            if user.avatar:
                pfp = user.avatar.url
            username = user.name
        return render(request, self.template_name, {'user': user, 'link_type': link_type, 'social_id': social_id, 'pfp': pfp, 'username': username})

    def post(self, request, uuid):
        account_link = AccountLink.objects.get(uuid=uuid)
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
