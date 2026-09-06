from django.contrib.auth import login
from django.core.cache import cache
from django.db import transaction
from django.http import Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views import View
from .models import (
    AccountAlreadyExistsError,
    AccountLink,
    DiscordAccountAlreadyLinkedError,
    RegistrationAlreadySentError,
    RegistrationEmailError,
    UserStub,
)
from .discord import describe_discord_user, get_discord_user
from .forms import RegistrationCompletionForm, RegistrationRequestForm
from core.models import ServerSettings, UserProfile
from clubManager import settings
from core.utilities import get_layout_data


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

    def build_form(self, user_stub, data=None):
        # An unsaved User for the form to fill in. activate() is what actually creates the
        # account, so a submission that fails leaves nothing behind.
        arguments = () if data is None else (data,)
        return RegistrationCompletionForm(
            user_stub.build_user(), *arguments, has_pending_discord_id=bool(user_stub.pending_discord_id)
        )

    def page_context(self, user_stub, form):
        """
        Everything the page needs to be honest about what finishing it will do.

        The Net ID is shown because the link arrives by email and the reader has to be
        able to tell at a glance whose account this is. The Discord account is shown
        because `/link` takes any Net ID: if someone else started this registration, the
        page they land on is the last place they can refuse the link before it is made.
        """
        discord_user = describe_discord_user(user_stub.pending_discord_id) if user_stub.pending_discord_id else None
        return {
            "form": form,
            "settings": ServerSettings.objects.first(),
            "net_id": user_stub.net_id,
            "pending_discord_id": user_stub.pending_discord_id,
            # Named for _discord_card.html, which reads these straight off the context.
            "username": discord_user["username"] if discord_user else None,
            "profile_image": discord_user["profile_image"] if discord_user else None,
        }

    def get(self, request, user_registration_key):
        user_stub = self.get_user_stub(user_registration_key)
        return render(request, self.template_name, self.page_context(user_stub, self.build_form(user_stub)))

    def post(self, request, user_registration_key):
        activated = False
        with transaction.atomic():
            user_stub = self.get_user_stub(user_registration_key, lock=True)
            form = self.build_form(user_stub, request.POST)
            if form.is_valid():
                user = form.save(commit=False)
                try:
                    redirect_destination = user_stub.activate(
                        user, link_discord=form.cleaned_data.get("link_discord", True)
                    )
                    activated = True
                except AccountAlreadyExistsError:
                    form.add_error(None, "An account for this Net ID already exists. Try signing in instead.")
                except DiscordAccountAlreadyLinkedError:
                    form.add_error(
                        None, "That Discord account is already linked to another account. Contact an officer."
                    )

        if not activated:
            return render(request, self.template_name, self.page_context(user_stub, form))
        return redirect(redirect_destination or "registration_submitted")


class RegistrationSubmittedView(View):
    """Where a finished registration lands when it has nowhere else to go."""
class RegistrationRequestView(View):
    template_name = "registration_request.html"
    confirmation_message = (
        "If you are eligible to register, check your UTD email for a link to finish creating your account."
    )

    def render_form(self, request, form, **context):
        return render(
            request, self.template_name, {"form": form, "settings": ServerSettings.objects.first(), **context}
        )

    def get(self, request):
        return self.render_form(request, RegistrationRequestForm())

    @staticmethod
    def is_rate_limited(request, net_id):
        ip = request.META.get("REMOTE_ADDR", "unknown")
        keys = (f"registration-request:ip:{ip}", f"registration-request:netid:{net_id}")
        limits = (settings.REGISTRATION_REQUEST_IP_LIMIT, settings.REGISTRATION_REQUEST_NETID_LIMIT)
        for key, limit in zip(keys, limits):
            count = cache.get(key, 0)
            if count >= limit:
                return True
        for key in keys:
            cache.add(key, 0, settings.REGISTRATION_REQUEST_WINDOW_SECONDS)
            cache.incr(key)
        return False

    def post(self, request):
        form = RegistrationRequestForm(request.POST)
        if not form.is_valid():
            return self.render_form(request, form)
        net_id = form.cleaned_data["net_id"]
        if self.is_rate_limited(request, net_id):
            return self.render_form(request, RegistrationRequestForm(), success=self.confirmation_message)
        try:
            user_stub = UserStub.create(net_id, "")
            UserStub.notify(user_stub)
        except (RegistrationAlreadySentError, AccountAlreadyExistsError):
            pass
        except RegistrationEmailError:
            if "user_stub" in locals():
                user_stub.delete()
            return self.render_form(
                request, form, error="We could not send your registration email. Please try again later."
            )
        return self.render_form(request, RegistrationRequestForm(), success=self.confirmation_message)


    template_name = "registration_submitted.html"

    def get(self, request):
        return render(request, self.template_name, {"settings": ServerSettings.objects.first()})
