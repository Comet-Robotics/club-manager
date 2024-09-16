from django.contrib import admin

from common.admin import SearchFields

# Register your models here.

from .models import Product, Payment, Term

class PaymentAdmin(admin.ModelAdmin):
    exclude = ["completed_at", "metadata"]
    readonly_fields = ["created_at", "updated_at"]
    autocomplete_fields = ["user", "verified_by"]

admin.site.register(Product, search_fields=["name"])
admin.site.register(Term, search_fields=["name"] + SearchFields.PRODUCT)
admin.site.register(Payment, PaymentAdmin, search_fields=["method"] + SearchFields.USER + SearchFields.PRODUCT)
