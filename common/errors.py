"""
Error handlers that show the reporter a Sentry event ID.

Django's built-in handlers render a bare page with no context, which leaves a user
reporting a problem with nothing to quote and a developer with no way to find the
matching issue. These handlers render the same templates with the ID of the event
Sentry just captured, so "it broke, here's the code" is enough to go on.

The pages reuse the public base template, which reads the organization's name and
accent colour off `settings`. That settings object is a transient, unsaved
ServerSettings rather than the database row: the database may be exactly what is
broken, and a query that fails or hangs turns a failed request into a failed error
page. The model's own defaults are what the pages fall back to.
"""

import sentry_sdk
from django.http import HttpRequest, HttpResponse
from django.template import loader

from core.models import ServerSettings

# The accent colour the error pages use. The organization's configured colour lives in
# the database row, which the error pages cannot read, so they use this instead.
ERROR_PAGE_ACCENT_COLOR_HEX = "#120F0E"


def _transient_server_settings() -> ServerSettings:
    """
    An unsaved ServerSettings carrying the branding the error pages need.

    Never saved and never queried, so the error pages render even when the database
    is what is broken. The organization's configured name and accent colour live in
    the database row, which this cannot read, so the pages fall back to the model's
    defaults, with the accent colour set to the site's own.
    """
    settings_obj = ServerSettings()
    settings_obj.accent_color_hex = ERROR_PAGE_ACCENT_COLOR_HEX
    return settings_obj


def _render(request: HttpRequest, template_name: str, status: int) -> HttpResponse:
    """Render an error template with the current Sentry event ID attached."""
    # Returns the last event this process sent, which for an unhandled exception is the
    # one that triggered this handler. None when Sentry is disabled, in which case the
    # templates just omit the reference code.
    context = {
        "sentry_event_id": sentry_sdk.last_event_id(),
        "settings": _transient_server_settings(),
    }

    # Rendered without the request on purpose: context processors hit the database and
    # the session, and anything they raise here would replace this page with an opaque
    # failure from deep inside Django.
    content = loader.get_template(template_name).render(context)
    return HttpResponse(content, status=status)


def bad_request(request: HttpRequest, exception: Exception, template_name: str = "400.html") -> HttpResponse:
    return _render(request, template_name, 400)


def permission_denied(request: HttpRequest, exception: Exception, template_name: str = "403.html") -> HttpResponse:
    return _render(request, template_name, 403)


def page_not_found(request: HttpRequest, exception: Exception, template_name: str = "404.html") -> HttpResponse:
    return _render(request, template_name, 404)


def server_error(request: HttpRequest, template_name: str = "500.html") -> HttpResponse:
    return _render(request, template_name, 500)
