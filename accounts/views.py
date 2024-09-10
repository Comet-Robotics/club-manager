from django.shortcuts import render, redirect
from django.views import View
from .models import AccountLink
from core.models import UserProfile


class LinkSocialView(View):
    template_name = 'link_social.html'

    def get(self, request, uuid):
        account_link = AccountLink.objects.get(uuid=uuid)
        user = account_link.user
        link_type = account_link.link_type
        social_id = account_link.social_id
        return render(request, self.template_name, {'user': user, 'link_type': link_type, 'social_id': social_id})

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
