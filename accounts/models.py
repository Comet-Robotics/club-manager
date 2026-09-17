from django.db import IntegrityError, models, transaction
from django.contrib.auth.models import User
import uuid

from datetime import datetime, timedelta

from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.utils.html import escape

from accounts.discord import DiscordUser, describe_discord_user
from core.emails import send_templated_email
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


def describe_pending_discord_link(discord_id: str) -> str:
    """
    The line a registration email has to carry when the registration came from Discord.

    `/link` accepts any Net ID, so the person opening this email may never have touched
    Discord: without this line they get a plain "create your account" mail, finish the
    form, and silently hand the stranger who typed their Net ID a Discord account on
    theirs - and with it the member role. Naming the account and saying it can be refused
    is what makes that visible to the one person able to stop it.

    The Discord lookup is decoration. When it fails the ID alone still identifies the
    account well enough for an officer to act on.
    """
    discord_user: DiscordUser | None = describe_discord_user(discord_id)
    who = f"@{discord_user['username']} (ID {discord_id})" if discord_user else f"the account with ID {discord_id}"
    return (
        f"This registration was started from Discord by {who}. Finishing it will link that Discord "
        "account to your new account. If that isn't you, don't use this link and tell an officer."
    )


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
    Tracks a self-service registration that has been started but not finished.

    Deliberately does *not* create a `User` row. A `User` existing means "this is a
    real account", and the rest of the app relies on that: every query that lists or
    looks up users would otherwise need to learn to skip half-registered placeholders.
    The Net ID is held here instead, and the unique constraint on it is what reserves
    the name until the registration is either completed or expires.
    """

    user_registration_key = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    net_id = models.CharField(max_length=150, unique=True)
    pending_discord_id = models.CharField(max_length=200, null=True, blank=True, unique=True)
    after_registration_redirect_destination = models.TextField(
        blank=True, null=True, validators=[validate_after_registration_redirect_destination]
    )

    expires_at = models.DateTimeField(default=get_registration_expiration)

    def __str__(self):
        return f"registration for {self.net_id}"

    @staticmethod
    def _get_deletion_candidates() -> QuerySet["UserStub"]:
        return UserStub.objects.filter(expires_at__lte=timezone.now())

    @staticmethod
    def purge_deletion_candidates():
        """
        Drop expired registrations.

        This only ever deletes `UserStub` rows. `UserStub` holds no reference to
        `User` in either direction, so an abandoned registration cannot take an
        account - or the payments and reservations hanging off it - down with it.
        """
        with transaction.atomic():
            return UserStub._get_deletion_candidates().delete()

    @staticmethod
    def create(
        net_id: str,
        after_registration_redirect_destination: str | None,
        discord_user_id: str | None = None,
    ):
        validate_after_registration_redirect_destination(after_registration_redirect_destination)
        net_id = net_id.lower()
        _ = UserStub.purge_deletion_candidates()

        with transaction.atomic():
            if User.objects.filter(username=net_id).exists():
                raise AccountAlreadyExistsError

            if UserStub.objects.filter(net_id=net_id).exists():
                raise RegistrationAlreadySentError

            if discord_user_id is not None and UserProfile.objects.filter(discord_id=discord_user_id).exists():
                raise DiscordAccountAlreadyLinkedError

            try:
                with transaction.atomic():
                    return UserStub.objects.create(
                        net_id=net_id,
                        pending_discord_id=discord_user_id,
                        after_registration_redirect_destination=after_registration_redirect_destination,
                    )
            except IntegrityError as error:
                # Lost a race against a concurrent registration for the same Net ID or
                # Discord account. Work out which unique constraint gave way.
                if UserStub.objects.filter(net_id=net_id).exists():
                    raise RegistrationAlreadySentError from error
                raise DiscordAccountAlreadyLinkedError from error

    def build_user(self) -> User:
        """
        An unsaved `User` for this registration, for a form to fill in before `activate`.

        The account is active with no usable password, which is Django's idiom for "this
        account is fine, it just has no way to sign in with a password". Members do not log
        in to the web portal today: the account exists so the member can pay dues, link
        their Discord, and be checked in at events. `is_active=False` means *banned* by
        convention, and everything that grows to read the flag - a magic-link login most of
        all - would read every ordinary member as suspended.

        Nothing is written to the database until `activate` is called, so abandoning the
        form here leaves no trace.
        """
        user = User(username=self.net_id, is_active=True)
        user.set_unusable_password()
        return user

    def activate(self, user: User, *, link_discord: bool = True) -> str | None:
        """
        Turn this registration into a real account and return where to send the user next.

        `user` is the instance from `build_user` with names already set. Creating the
        `User` and dropping this stub happen in one transaction, so a Net ID is never held
        by both a stub and an account.

        `link_discord=False` is how the member declines the Discord account this
        registration was started from. Anyone can run `/link` against someone else's Net
        ID, so the Discord ID riding along on the stub is a claim by a stranger until the
        person reading their own email agrees to it. Declining still finishes the
        registration - the account is wanted, the link is not - so the stub goes either
        way and the rejected ID disappears with it.
        """
        if user.username != self.net_id:
            raise ValueError(f"Cannot activate the registration for {self.net_id} with a User for {user.username}.")

        with transaction.atomic():
            try:
                with transaction.atomic():
                    user.save()
            except IntegrityError as error:
                # Someone else claimed this Net ID while the form was open - the real
                # account wins, and this registration is now moot.
                raise AccountAlreadyExistsError from error

            if link_discord and self.pending_discord_id is not None:
                profile, _ = UserProfile.objects.get_or_create(user=user)
                profile.discord_id = self.pending_discord_id
                try:
                    with transaction.atomic():
                        profile.save()
                except IntegrityError as error:
                    raise DiscordAccountAlreadyLinkedError from error

            UserStub.objects.filter(pk=self.pk).delete()

        return self.after_registration_redirect_destination

    def email_address(self) -> str:
        return f"{self.net_id}@utdallas.edu"

    def get_registration_url(self):
        return f"{settings.PUBLIC_URL}/accounts/register/continue/{self.user_registration_key}"

    @staticmethod
    def notify(user_stub: "UserStub"):
        try:
            server_settings = ServerSettings.objects.first()
            if server_settings is None:
                raise Exception("Server settings not found")

            # Both paths below have to say which Net ID is being registered and, when the
            # registration came from Discord, whose Discord account is riding along on it.
            discord_disclosure = (
                describe_pending_discord_link(user_stub.pending_discord_id) if user_stub.pending_discord_id else None
            )

            if settings.FEATURE_FLAGS["NEW_TRANSACTIONAL_EMAIL_TEMPLATES"]:
                send_templated_email(
                    "email/messages/account_registration.html",
                    {
                        "net_id": user_stub.net_id,
                        "registration_url": user_stub.get_registration_url(),
                        "expires_at": user_stub.expires_at.strftime("%m-%d-%Y %H:%M:%S"),
                        "request_url": f"{settings.PUBLIC_URL}/accounts/register",
                        "discord_disclosure": discord_disclosure,
                    },
                    [user_stub.email_address()],
                )
                return

            discord_disclosure_text = f"\n{discord_disclosure}\n" if discord_disclosure else ""
            discord_disclosure_html = (
                f"<p><strong>{escape(discord_disclosure)}</strong></p>" if discord_disclosure else ""
            )

            send_mail(
                f"Create your {server_settings.organization_name} account",
                f"""
Hey there!

Let's finish your {server_settings.organization_name} registration! Just click this link to finish up: {user_stub.get_registration_url()}

This creates an account for the Net ID {user_stub.net_id}.
{discord_disclosure_text}
This link expires at {user_stub.expires_at.strftime("%m-%d-%Y %H:%M:%S")}. To request a new one, click this link: {f"{settings.PUBLIC_URL}/accounts/register"}

If this was not you, you can safely ignore this email.

Thanks!
""",
                settings.EMAIL_FROM,
                [user_stub.email_address()],
                fail_silently=False,
                html_message=f"""
<h2>Hey there!</h2>

<p>Let's finish your {server_settings.organization_name} registration! Click the button below or use the link to finish up.</p>

<p>This creates an account for the Net ID <strong>{user_stub.net_id}</strong>.</p>

{discord_disclosure_html}

<a href="{user_stub.get_registration_url()}"><button style="border: solid #950000 3px;padding: 1em; border-radius: 10px; background-color:#bf1e2e; color: white;"><strong>Finish Registering</strong></button></a>

<br><br><a href="{user_stub.get_registration_url()}">{user_stub.get_registration_url()}</a>

<p>This link expires at {user_stub.expires_at.strftime("%m-%d-%Y %H:%M:%S")}. To request a new one, <a href="{settings.PUBLIC_URL}/accounts/register">click here</a>.</p>

<p>If this was not you, you can safely ignore this email.</p>

<p>Thanks!</p>
""",
            )
        except Exception as error:
            raise RegistrationEmailError from error
