from typing import Any
from django.contrib import admin
from django.http import HttpRequest
from .models import AccountLink, UserStub


class AccountLinkAdmin(admin.ModelAdmin):
    readonly_fields = ["uuid", "date_created"]

    def get_fields(self, request: HttpRequest, obj: Any | None = None) -> Any:
        fields = list(super().get_fields(request, obj))
        fields.remove("uuid")
        fields.remove("date_created")
        fields.insert(0, "date_created")
        fields.insert(0, "uuid")
        return fields


admin.site.register(AccountLink, AccountLinkAdmin)


@admin.register(UserStub)
class UserStubAdmin(admin.ModelAdmin):
    list_display = ["net_id", "pending_discord_id", "expires_at"]
    search_fields = ["net_id", "pending_discord_id"]
    readonly_fields = ["user_registration_key"]
