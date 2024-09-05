from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils.translation import gettext_lazy as _

# Create your models here.

class Product(models.Model):
    """
    A Product is an object representing a purchasable item. This is separate from the Term object so that we could reuse this for other usecases like merchandise.
    """
    name = models.CharField(max_length=100)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    amount_cents = models.IntegerField(validators=[MinValueValidator(0)])

    # -1 means unlimited purchases per user. 0 means no purchases allowed (maybe if we want to disable purchases). Any other positive number is the maximum number of purchases allowed
    max_purchases = models.IntegerField(validators=[MinValueValidator(-1)])

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
  product = models.OneToOneField(Product, on_delete=models.CASCADE)

  def __str__(self):
    return self.name


class Payment(models.Model):
  """
  A Payment is an object representing a payment made by a user for a product.
  """
  class Methods(models.TextChoices):
    square = 'square', _('Square Online Payment')
    cash = 'cash', _('In-Person Cash Payment')
    other = 'other', _('Other Payment Method')
    paypal = 'paypal', _('PayPal Payment (LEGACY - DO NOT USE FOR NEW PAYMENTS)')
    venmo = 'venmo', _('Venmo Payment (LEGACY - DO NOT USE FOR NEW PAYMENTS)')
    cashapp = 'cashapp', _('Cash App Payment (LEGACY - DO NOT USE FOR NEW PAYMENTS)')

  user = models.OneToOneField('auth.User', on_delete=models.CASCADE)
  product = models.OneToOneField(Product, on_delete=models.CASCADE)
  created_at = models.DateTimeField(auto_now_add=True)
  updated_at = models.DateTimeField(auto_now=True)
  verified_by = models.OneToOneField('auth.User', on_delete=models.CASCADE, related_name='verified_by')
  notes = models.TextField()
  metadata = models.JSONField()
  method = models.CharField(choices=Methods, default=Methods.other)

  def __str__(self):
    return f"{self.user.username} - {self.product.name}"
