from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from common.admin import SearchFields
from core.admin import UserProfileInline

# Register your models here.
from .models import UserIdentification, Attendance, Event, Reservation

class UserIDInline(admin.StackedInline):
    model = UserIdentification
    can_delete = False
    verbose_name_plural = "User Identification"

class UserAdmin(BaseUserAdmin):
    inlines = [UserIDInline, UserProfileInline]

admin.site.unregister(User)
admin.site.register(User, UserAdmin)
admin.site.register(UserIdentification, search_fields=['student_id'] + SearchFields.USER)
admin.site.register(Attendance, search_fields=SearchFields.USER + SearchFields.EVENT)
admin.site.register(Reservation, search_fields=SearchFields.USER + SearchFields.EVENT)
admin.site.register(Event, search_fields=['event_name', 'id'])
