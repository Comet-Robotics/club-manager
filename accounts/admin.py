from collections.abc import Callable, Sequence
from typing import Any
from django.contrib import admin
from django.http import HttpRequest
from .models import AccountLink


class AccountLinkAdmin(admin.ModelAdmin):
    readonly_fields = ["uuid", "date_created"]

    def get_fields(
        self, request: HttpRequest, obj: Any | None = ...
    ) -> Sequence[Callable[..., Any] | str]:
        fields = list(super().get_fields(request, obj))
        fields.remove("uuid")
        fields.remove("date_created")
        fields.insert(0, "date_created")
        fields.insert(0, "uuid")
        return fields


admin.site.register(AccountLink, AccountLinkAdmin)
