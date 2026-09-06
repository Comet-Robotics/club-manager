from django.db import IntegrityError, models, transaction
from django.contrib.auth.models import User
import uuid

from datetime import datetime, timedelta

from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.utils.http import url_has_allowed_host_and_scheme

from clubManager import settings
from core.models import ServerSettings, UserProfile
from django.db.models.query import QuerySet
from django.utils import timezone


class RegistrationError(Exception):
    """Base exception for a self-service account registration failure."""


class RegistrationAlreadySentError(RegistrationError):
    """A valid registration email has already been sent for this Net ID."""


class AccountAlreadyExistsError(RegistrationError):
    """The Net ID already belongs to a completed account."""


class DiscordAccountAlreadyLinkedError(RegistrationError):
    """The Discord account is already associated with another user."""


class RegistrationEmailError(RegistrationError):
    """The registration email could not be delivered."""


def get_registration_expiration() -> datetime:
    return timezone.now() + timedelta(hours=24)


def validate_after_registration_redirect_destination(value: str | None) -> None:
    """Allow only paths that remain on this site after registration."""
    if not value:
        return

    if not (value.startswith("/") and url_has_allowed_host_and_scheme(value, allowed_hosts=set(), require_https=True)):
        raise ValidationError("After-registration redirect destinations must be site-relative paths.")


class AccountLink(models.Model):
    SOCIAL_CHOICES = (("discord", "Discord"), ("other", "Other"))

    uuid = models.UUIDField("UUID", default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    date_created = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    link_type = models.CharField(max_length=200, choices=SOCIAL_CHOICES)
    social_id = models.CharField(max_length=200)

    def __str__(self):
        return f"{self.link_type} - {self.user.first_name} {self.user.last_name}"


class UserStub(models.Model):
    """
    Used when a user is in the middle of doing a self-service registration and has not completed the process yet. Users with an associated UserStub should not show up in any other part of the application other than the admin portal."""

    user_registration_key = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    after_registration_redirect_destination = models.TextField(
        blank=True, null=True, validators=[validate_after_registration_redirect_destination]
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    expires_at = models.DateTimeField(default=get_registration_expiration)

    @staticmethod
    def _get_deletion_candidates() -> QuerySet["UserStub"]:
        return UserStub.objects.filter(expires_at__lte=timezone.now(), user__is_active=False)

    @staticmethod
    def purge_deletion_candidates():
        with transaction.atomic():
            return User.objects.filter(pk__in=UserStub._get_deletion_candidates().values("user_id")).delete()

    @staticmethod
    def create(
        net_id: str,
        after_registration_redirect_destination: str | None,
        discord_user_id: str | None = None,
    ):
        validate_after_registration_redirect_destination(after_registration_redirect_destination)
        _ = UserStub.purge_deletion_candidates()
        with transaction.atomic():
            user, created = User.objects.get_or_create(username=net_id, defaults={"is_active": False})
            if not created:
                if UserStub.objects.filter(user=user, user__is_active=False).exists():
                    raise RegistrationAlreadySentError
                raise AccountAlreadyExistsError

            if discord_user_id is not None:
                profile, _ = UserProfile.objects.get_or_create(user=user)
                profile.discord_id = discord_user_id
                try:
                    with transaction.atomic():
                        profile.save()
                except IntegrityError as error:
                    raise DiscordAccountAlreadyLinkedError from error

            return UserStub.objects.create(
                user=user, after_registration_redirect_destination=after_registration_redirect_destination
            )

    def activate(self):
        after_registration_redirect_destination = self.after_registration_redirect_destination
        UserStub.objects.filter(pk=self.pk).delete()
        return after_registration_redirect_destination

    def get_registration_url(self):
        return f"{settings.PUBLIC_URL}/accounts/register/continue/{self.user_registration_key}"

    @staticmethod
    def notify(user_stub: "UserStub"):
        try:
            server_settings = ServerSettings.objects.first()
            if server_settings is None:
                raise Exception("Server settings not found")
            send_mail(
                f"Create your {server_settings.organization_name} account",
                f"""
Hey there!

Let's finish creating your {server_settings.organization_name} account! Just click this link to finish up: {user_stub.get_registration_url()}

This link expires at {user_stub.expires_at.strftime("%m-%d-%Y %H:%M:%S")}. To request a new one, click this link: {f"{settings.PUBLIC_URL}/accounts/register"}

If this was not you, you can safely ignore this email.

Thanks!
""",
                settings.EMAIL_FROM,
                [f"{user_stub.user.username}@utdallas.edu"],
                fail_silently=False,
                html_message=f"""
<h2>Hey there!</h2>

<p>Let's finish creating your {server_settings.organization_name} account! Click the button below or use the link to finish up.</p>

<a href="{user_stub.get_registration_url()}"><button style="border: solid #950000 3px;padding: 1em; border-radius: 10px; background-color:#bf1e2e; color: white;"><strong>Create Account</strong></button></a>

<br><br><a href="{user_stub.get_registration_url()}">{user_stub.get_registration_url()}</a>

<p>This link expires at {user_stub.expires_at.strftime("%m-%d-%Y %H:%M:%S")}. To request a new one, <a href="{settings.PUBLIC_URL}/accounts/register">click here</a>.</p>

<p>If this was not you, you can safely ignore this email.</p>

<p>Thanks!</p>
""",
            )
        except Exception as error:
            raise RegistrationEmailError from error
