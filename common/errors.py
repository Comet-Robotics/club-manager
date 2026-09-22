"""
Error handlers that show the reporter a Sentry event ID.

Django's built-in handlers render a bare page with no context, which leaves a user
reporting a problem with nothing to quote and a developer with no way to find the
matching issue. These handlers render the same templates with the ID of the event
Sentry just captured, so "it broke, here's the code" is enough to go on.

The templates are deliberately standalone -- they don't extend the portal base, which
reads ServerSettings from the database. A 500 page that needs a working database is a
500 page that fails to render.
"""

import sentry_sdk
from django.http import HttpRequest, HttpResponse
from django.template import loader


def _render(request: HttpRequest, template_name: str, status: int) -> HttpResponse:
    """Render an error template with the current Sentry event ID attached."""
    # Returns the last event this process sent, which for an unhandled exception is the
    # one that triggered this handler. None when Sentry is disabled, in which case the
    # templates just omit the reference code.
    context = {"sentry_event_id": sentry_sdk.last_event_id()}

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
