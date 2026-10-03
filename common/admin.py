from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from common.utils import normalize_username


class SearchFields:
    USER = ["user__username", "user__first_name", "user__last_name"]
    EVENT = ["event__event_name", "event__id"]
    PRODUCT = ["product__name"]
    PURCHASED_PRODUCT = ["purchased_products__product__name"]


class LowercaseUsernameAdminForm(UserCreationForm):
    """
    Report a duplicate Net ID as a form error instead of an IntegrityError.
    """

    def clean_username(self):
        username = normalize_username(self.cleaned_data.get("username", ""))

        if not username:
            return username

        existing = User.objects.filter(username__iexact=username)
        if self.instance.pk:
            existing = existing.exclude(pk=self.instance.pk)
        if existing.exists():
            raise ValidationError(
                "A user with this Net ID already exists. Edit that account instead of creating a second one."
            )
        return username


class LowercaseUsernameUserAdmin(UserAdmin):
    form = LowercaseUsernameAdminForm
    add_form = LowercaseUsernameAdminForm
