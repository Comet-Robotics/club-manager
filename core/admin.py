from django.contrib import admin

# Register your models here.
from core.models import UserProfile

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = "User Profile"
# registered in events.admin
