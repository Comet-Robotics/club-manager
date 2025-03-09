from django.contrib import admin

# Register your models here.
from core.models import UserProfile, ServerSettings, Race

from common.admin import SearchFields


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = "User Profile"


# registered in events.admin

admin.site.register(UserProfile, search_fields=SearchFields.USER)

admin.site.register(ServerSettings)

admin.site.register(Race)
