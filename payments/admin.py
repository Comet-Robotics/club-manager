from django.contrib import admin

# Register your models here.

from .models import Product, Payment, Term

admin.site.register(Product)
admin.site.register(Payment)
admin.site.register(Term)