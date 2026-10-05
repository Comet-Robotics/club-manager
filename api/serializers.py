from django.contrib.auth.models import Group, User
from payments.models import Product, PurchasedProduct
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from events.models import Event


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ["url", "id", "username", "email", "groups", "first_name", "last_name"]
        extra_kwargs = {
            # The DB enforces uniqueness on LOWER(BTRIM(username)) (migration 0030), but
            # DRF's auto-generated UniqueValidator is an exact match, so a case-variant
            # duplicate would pass validation and 500 on the index. Check iexact so the
            # API returns 400 like it did before the index existed.
            "username": {"validators": [UniqueValidator(queryset=User.objects.all(), lookup="iexact")]},
        }


class ProductSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Product
        fields = ["id", "name", "description", "amount_cents", "max_purchases_per_user", "image"]


class PurchasedProductSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = PurchasedProduct
        fields = ["id", "product", "quantity"]

    product = ProductSerializer(read_only=True)


class EventSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Event
        fields = ["id", "event_name", "event_date", "url", "combat_event"]
