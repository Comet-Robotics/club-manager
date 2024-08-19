from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

# Register your models here.
from .models import UserIdentification, Attendance, Event, Reservation

class UserIDInline(admin.StackedInline):
    model = UserIdentification
    can_delete = False
    verbose_name_plural = "User Identification"
    
class UserAdmin(BaseUserAdmin):
    inlines = [UserIDInline]

admin.site.unregister(User)
admin.site.register(User, UserAdmin)
admin.site.register(UserIdentification)
admin.site.register(Attendance)
admin.site.register(Reservation)
admin.site.register(Event)

