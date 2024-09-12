from collections.abc import Callable, Sequence
from typing import Any
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.http import HttpRequest

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

class EventAdmin(admin.ModelAdmin):
    readonly_fields = ["id"]
    
    def get_fields(self, request: HttpRequest, obj: Any | None = ...) -> Sequence[Callable[..., Any] | str]:
        fields = list(super().get_fields(request, obj))
        fields.remove("id")
        fields.insert(0, "id")
        return fields

admin.site.unregister(User)
admin.site.register(User, UserAdmin)
admin.site.register(UserIdentification, search_fields=['student_id'] + SearchFields.USER)
admin.site.register(Attendance, autocomplete_fields=['user'], search_fields=SearchFields.USER + SearchFields.EVENT)
admin.site.register(Reservation, search_fields=SearchFields.USER + SearchFields.EVENT)
admin.site.register(Event, EventAdmin, search_fields=['event_name', 'id'])
