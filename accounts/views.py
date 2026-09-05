from django.contrib.auth import login
from django.db import transaction
from django.http import Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views import View
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.forms import AuthenticationForm
from django.urls import reverse

from accounts.discord import get_discord_user
from .models import AccountAlreadyExistsError, AccountLink, DiscordAccountAlreadyLinkedError, UserStub
from .forms import RegistrationCompletionForm
from core.models import ServerSettings, UserProfile
from clubManager import settings
from core.utilities import get_layout_data
import requests
from typing import TypedDict


class CustomLoginView(LoginView):
    template_name = "registration/login.html"
    authentication_form = AuthenticationForm
    redirect_authenticated_user = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        layout_data = get_layout_data(self.request)
        context.update(layout_data)
        return context


class ClubLogoutView(LogoutView):
    """
    Log the user out and send them back to the sign in page with a notice.

    The notice rides along as a query parameter rather than as a message
    framework message, because logging out flushes the session and would take
    any queued message with it.
    """

    def get_success_url(self):
        return f"{reverse('login')}?logged_out=1"


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


class RegistrationCompleteView(View):
    template_name = "registration_complete.html"

    @staticmethod
    def get_user_stub(user_registration_key, *, lock=False):
        user_stubs = UserStub.objects.filter(pk=user_registration_key, expires_at__gt=timezone.now())
        if lock:
            user_stubs = user_stubs.select_for_update()
        user_stub = user_stubs.first()
        if user_stub is None:
            raise Http404("This registration link is invalid or has expired.")
        return user_stub

    def get(self, request, user_registration_key):
        user_stub = self.get_user_stub(user_registration_key)
        return render(
            request,
            self.template_name,
            {"form": RegistrationCompletionForm(user_stub.build_user()), "settings": ServerSettings.objects.first()},
        )

    def post(self, request, user_registration_key):
        activated = False
        with transaction.atomic():
            user_stub = self.get_user_stub(user_registration_key, lock=True)
            # An unsaved User for the form to fill in. activate() is what actually creates
            # the account, so a submission that fails here leaves nothing behind.
            form = RegistrationCompletionForm(user_stub.build_user(), request.POST)
            if form.is_valid():
                user = form.save(commit=False)
                try:
                    redirect_destination = user_stub.activate(user)
                    activated = True
                except AccountAlreadyExistsError:
                    form.add_error(None, "An account for this Net ID already exists. Try signing in instead.")
                except DiscordAccountAlreadyLinkedError:
                    form.add_error(
                        None, "That Discord account is already linked to another account. Contact an officer."
                    )

        if not activated:
            return render(
                request,
                self.template_name,
                {"form": form, "settings": ServerSettings.objects.first()},
            )
        login(request, user)
        return redirect(redirect_destination or "profile")
