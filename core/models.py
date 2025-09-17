from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

from common.major import get_majors
from payments.models import PurchasedProduct, Term
from django.utils import timezone
from datetime import timedelta
from colorfield.fields import ColorField


class ServerSettings(models.Model):
    # only allows one instance of this model to exist: https://stackoverflow.com/a/69790968
    _singleton = models.BooleanField(default=True, editable=False, unique=True)
    organization_name = models.CharField(default="Your Organization")
    accent_color_hex = ColorField(default="#4BC0FF")
    logo = models.ImageField(upload_to="logos")

    class Meta:
        verbose_name = "server configuration"
        verbose_name_plural = "server configurations"


class Race(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Diet(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class UserProfile(models.Model):
    class GenderChoice(models.TextChoices):
        MALE = "M", _("Man")
        FEMALE = "F", _("Woman")
        NONBINARY = "N", _("Non-Binary")
        OTHER = "O", _("Other")

    class ShirtSize(models.TextChoices):
        XSMALL = "XS", _("XS")
        SMALL = "S", _("Small")
        MEDIUM = "M", _("Medium")
        LARGE = "L", _("Large")
        XLARGE = "XL", _("XL")
        XXLARGE = "XXL", _("2XL")
        XXXLARGE = "XXXL", _("3XL")

    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    gender = models.CharField(max_length=1, choices=GenderChoice.choices, null=True, blank=True)
    race = models.ManyToManyField(Race, blank=True)
    diet = models.ManyToManyField(Diet, blank=True)
    shirt = models.CharField(max_length=4, choices=ShirtSize.choices, null=True, blank=True)
    is_hispanic = models.BooleanField(null=True, blank=True, default=None)
    discord_id = models.CharField(max_length=200, null=True, blank=True, unique=True)
    major = models.CharField(
        choices=list(get_majors().items()) + [("unknown", "Unknown")], null=True, blank=True, default=None
    )  # NULL indicates major needs to be fetched
    is_utd_affiliate = models.BooleanField(
        null=False, blank=False, default=True
    )  # TODO: get rid of default=True and fix UserProfile creation with null field
    date_of_birth = models.DateField(null=True, blank=True)
    comet_card_serial_number = models.CharField(max_length=20, unique=True, null=True, blank=True)

    def is_minor(self):
        assert self.date_of_birth is not None
        return self.date_of_birth < timezone.now().date() - timedelta(weeks=52 * 18)

    def __str__(self):
        return self.user.first_name + "_" + self.user.last_name

    def get_membership_terms(self) -> list[tuple[Term, PurchasedProduct]]:
        """
        Returns a list of tuples containing (Term, PurchasedProduct) for all terms where the user was a member.
        The list is sorted by term start date in descending order (most recent first).
        """
        purchased_products = (
            PurchasedProduct.objects.filter(
                payment__user=self.user, payment__is_successful=True, product__term__isnull=False
            )
            .select_related("product__term")
            .order_by("-product__term__start_date")
        )

        return [(product.product.term, product) for product in purchased_products]

    def is_member(self, for_term: Term | None = None) -> tuple[Term, PurchasedProduct | None]:
        """
        Returns a tuple with the Term and PurchasedProduct object for the current member if the user is a member for the given term, or a tuple with the given Term and None if they are not a member.
        """
        if for_term:
            term = for_term
        else:
            term = Term.get_current_term()
            if not term:
                raise Exception("No current Term found.")

        purchased_product = PurchasedProduct.objects.filter(
            payment__user=self.user, product=term.product, payment__is_successful=True
        )

        return term, purchased_product.first()

    @staticmethod
    def create_extended_user(net_id, comet_card_serial_number, first, last):
        """Create a user with profile and comet card serial number"""
        user = UserProfile.create_basic_user(net_id, first, last)
        user_profile = user.userprofile
        user_profile.comet_card_serial_number = comet_card_serial_number
        user_profile.save()
        return user

    @staticmethod
    def create_basic_user(net_id, first, last):
        """Create a basic user with automatic UserProfile creation via signal"""
        return User.objects.create(username=net_id, first_name=first, last_name=last)

    @staticmethod
    def link_user(user_id, comet_card_serial_number):
        """Link an existing user to a comet card serial number"""
        user = User.objects.get(pk=user_id)
        user_profile = user.userprofile
        user_profile.comet_card_serial_number = comet_card_serial_number
        user_profile.save()
        return user_profile
