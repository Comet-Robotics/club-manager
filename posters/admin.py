from django.contrib import admin

# Register your models here.
from .models import Campaign, Poster, Visit

admin.site.register(Campaign, search_fields=["campaign_name"])
admin.site.register(
    Poster, search_fields=["campaign__campaign_name", "location"]
)
admin.site.register(
    Visit,
    search_fields=["poster__campaign__campaign_name", "poster__location"],
)
