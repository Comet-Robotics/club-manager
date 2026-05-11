from __future__ import annotations

from typing_extensions import deprecated
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from computedfields.models import ComputedFieldsModel, computed

from common.utils import validate_staff

# Create your models here.


class Product(models.Model):
    """
    A Product is an object representing a purchasable item. This is separate from the Term object so that we could reuse this for other usecases like merchandise.
    """

    name = models.CharField(max_length=100)
    description = models.TextField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    amount_cents = models.IntegerField(validators=[MinValueValidator(0)])
    image = models.ImageField(upload_to="product_images/", null=True, blank=True)

    # -1 means unlimited purchases per user. 0 means no user is allowed to purchase (maybe if we want to disable purchases). Any other positive number is the maximum number of purchases allowed per user. So setting this to 1 means that a user can only pay for this product once.
    max_purchases_per_user = models.IntegerField(validators=[MinValueValidator(-1)])

    def __str__(self):
        return self.name


class Term(models.Model):
    """
    A Term is an object representing a term in a school year. This is used to help track member dues for each semester. A Term is associated with a Product which would hold the member dues amount for that term. A user has 'paid dues' for a term if they have a Payment object associated with that term's Product.
    """

    name = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    product: Product = models.OneToOneField(Product, on_delete=models.CASCADE)

    @staticmethod
    @deprecated("Use one of the undeprecated term query utilities (get_active_terms, get_active_term_with_earliest_end_date, get_active_term_with_latest_start_date) which have explicit handling for term overlaps instead")
    def get_current_term() -> "Term" | None:
        # TODO: this needs to return a QuerySet instead of a single object and/or throw if the query returns multiple objects
        return Term.objects.filter(start_date__lte=models.functions.Now(), end_date__gte=models.functions.Now()).first()


    @staticmethod
    def get_active_terms() -> models.QuerySet["Term"]:
        """
        Use this to answer "is this user a member today?"

        Returns a QuerySet of all active terms (terms whose start_date is in the past and end_date is in the future).

        During an overlap period, this returns both the expiring term and the renewing term.

        Suggested use-cases:
        - determining whether a user is allowed to participate as a current member
        - Discord member role sync
        - event check-in membership validity
        - current member exports
        - voter eligibility checks before applying attendance requirements
        """
        return Term.objects.filter(start_date__lte=models.functions.Now(), end_date__gte=models.functions.Now())


    @staticmethod
    def get_active_term_with_earliest_end_date() -> "Term" | None:
        """
        Use this when older-term rules should continue to govern until the older term expires.

        Returns the active term with the earliest end date.

        Example: Given a Spring 2026 term for 2025-12-01 to 2026-08-31, and a Fall 2026 term for 2026-05-01 to 2027-01-31, this function will return different results depending on the current date. 

        - In Spring 2026: returns Spring 2026 term, since that is the only active term.
        - During Spring 2026 and Fall 2026 overlap period: returns Spring 2026 term. While both Spring 2026 and Fall 2026 terms are active, the Spring 2026 term wins as it has the earliest end date.
        - In Fall 2026 but after the overlap period: returns Fall 2026 term, since that is the only active term.

        Suggested use-cases:
        - generating election voting rosters tied to the expiring academic term, where the renewing term should not replace the older term yet
        - checking eligibility for processes that intentionally remain attached to the soonest-expiring active term during an overlap period

        Gotchas:
        - Do not use this to answer "is this user a member today?" For that, check whether the user has paid for any term returned by `get_active_terms()`.
        - Do not use this to choose which dues product a renewing member should be prompted to buy. For that, use `get_active_term_with_latest_start_date()`.
        """
        return Term.objects.filter(start_date__lte=models.functions.Now(), end_date__gte=models.functions.Now()).order_by("end_date").first()

    @staticmethod
    def get_active_term_with_latest_start_date() -> "Term" | None:
        """
        Use this to answer "which active dues term should this user pay for now?"

        Returns the active term with the latest start date.

        Example: Given a Spring 2026 term for 2025-12-01 to 2026-08-31, and a Fall 2026 term for 2026-05-01 to 2027-01-31, this function will return different results depending on the current date. 

        - In Spring 2026: returns Spring 2026 term, since that is the only active term.
        - During Spring 2026 and Fall 2026 overlap period: returns Fall 2026 term
        - In Fall 2026 but after the overlap period: returns Fall 2026 term

        Recommended use-cases:
        - Selecting a term for member due payment - it is most advantageous to select the term with the latest start date since in theory, this allows the user to remain a member for a longer period of time. If you joined the club in May 2026, why pay dues for the Spring 2026 term when you can pay for the Fall 2026 term and be counted as a member for the remainder of the Spring 2026 term, and the entirety of the Fall 2026 term?
        - membership renewal warnings displayed on event check-ins during an overlap period: a Spring-only member should be warned to pay Fall dues, while a Fall member should not be warned

        Gotchas:
        - Do not use this by itself to answer "is this user a member today?" For that, check whether the user has paid for any term returned by `get_active_terms()`.
        """
        return Term.objects.filter(start_date__lte=models.functions.Now(), end_date__gte=models.functions.Now()).order_by("-start_date").first()

    def __str__(self):
        return self.name


class Payment(ComputedFieldsModel):
    """
    A Payment is an object representing a payment made by a user for a product. A Payment is 'successful' if one of the following conditions is met:
      - completed_at is set to a datetime that represents the time the payment was completed. This field is intended for tracking completion of 'programmatic' payments, like those made via Square's API.
      - verified_by is set to a user who can attest to the completion of the payment. This will usually be done by an officer in the admin panel, usually in the case of payments that aren't via Square like in-person cash payments.

    There are no (normal) cases where these 2 fields should be set at the same time.

    We include the amount_cents field to track the amount of this payment in cents. This is calculated by summing the amount of each PurchasedProduct associated with this payment, and then including Square fees (if applicable).
    """

    class Method(models.TextChoices):
        square_api = "square_api", _("Credit Card/Debit Card (Online)")
        cash = "cash", _("In-Person Cash Payment")
        other = "other", _("Other Payment Method")
        paypal = "paypal", _("PayPal Payment (LEGACY - DO NOT USE FOR NEW PAYMENTS)")
        venmo = "venmo", _("Venmo Payment (LEGACY - DO NOT USE FOR NEW PAYMENTS)")
        cashapp = "cashapp", _("Cash App Payment (LEGACY - DO NOT USE FOR NEW PAYMENTS)")

    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=False)

    amount_cents = models.IntegerField(validators=[MinValueValidator(0)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    verified_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="verified_by", null=True, blank=True, validators=[validate_staff]
    )

    notes = models.TextField(null=True, blank=True)
    method = models.CharField(choices=Method, default=Method.other)

    # excluded from admin panel
    completed_at = models.DateTimeField(null=True)
    metadata = models.JSONField(null=True)

    @computed(models.BooleanField(), depends=[("self", ["verified_by", "completed_at"])])
    def is_successful(self):
        return bool(self.verified_by or self.completed_at)

    def __str__(self):
        return f"{self.user.username} - {','.join(self.purchased_products.values_list('product__name', flat=True))}"


class PurchasedProduct(models.Model):
    """
    A PurchasedProduct is an object representing a product that a user has purchased.
    """

    product: Product = models.ForeignKey(Product, on_delete=models.CASCADE, null=False)
    quantity = models.IntegerField(default=1, validators=[MinValueValidator(1)], null=False)
    payment: Payment = models.ForeignKey(
        Payment, on_delete=models.CASCADE, related_name="purchased_products", null=False
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.product.name} ({self.quantity}), payment {self.payment.id}, user {self.payment.user}"
