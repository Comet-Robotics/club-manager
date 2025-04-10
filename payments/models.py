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

    def get_current_term():
        return Term.objects.filter(start_date__lte=models.functions.Now(), end_date__gte=models.functions.Now()).first()

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


# class ProductOptionSet(models.Model):
#   # Ex: Size, Color
#   name = models.CharField(max_length=100)
#   description = models.TextField()

#   def __str__(self):
#     return f"{self.name}"


# class ProductOption(models.Model):
#     product = models.ForeignKey(Product, on_delete=models.CASCADE)
#     set = models.ForeignKey(ProductOptionSet, on_delete=models.CASCADE)

#     def __str__(self):
#         return f"{self.product.name} - {self.set.name}"

# class ProductOptionValue(models.Model):
#   # Ex: Size - Small, Color - Blue
#   name = models.CharField(max_length=100)
#   description = models.TextField()
#   set = models.ForeignKey(ProductOptionSet, on_delete=models.CASCADE)

#   def __str__(self):
#     return f"{self.set.name} - {self.name}"
