from django.contrib import admin

# Register your models here.
from .models import Campaign, Poster

admin.site.register(Campaign)
admin.site.register(Poster)
