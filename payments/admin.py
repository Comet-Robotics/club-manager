from django.contrib import admin

from common.admin import SearchFields
from more_admin_filters import MultiSelectDropdownFilter

# Register your models here.

from .models import Product, Payment, Term

class PaymentAdmin(admin.ModelAdmin):
    exclude = ["completed_at", "metadata"]
    readonly_fields = ["created_at", "updated_at"]
    autocomplete_fields = ["user", "verified_by"]
    list_filter = [
        "is_successful",
        ("user__userprofile__discord_id", admin.EmptyFieldListFilter),
        ("method", MultiSelectDropdownFilter),
    ]

admin.site.register(Product, search_fields=["name"])
admin.site.register(Term, search_fields=["name"] + SearchFields.PRODUCT)
admin.site.register(Payment, PaymentAdmin, search_fields=SearchFields.USER + SearchFields.PRODUCT)
