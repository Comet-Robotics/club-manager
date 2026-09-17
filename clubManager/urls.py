"""
URL configuration for clubManager project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

import os

from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from events.views import club_events_view

# Error pages that surface the Sentry event ID, so a user can quote a reference code
# that maps straight to the captured issue. See common/errors.py.
handler400 = "common.errors.bad_request"
handler403 = "common.errors.permission_denied"
handler404 = "common.errors.page_not_found"
handler500 = "common.errors.server_error"

urlpatterns = [
    path("posters/", include("posters.urls")),
    path("events/", include("events.urls")),
    path("payments/", include("payments.urls")),
    path("", include("core.urls")),
    path("projects/", include("projects.urls")),
    path("club/events/", club_events_view, name="club_events"),
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("accounts/", include("accounts.urls")),
    path("api/", include("api.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    from debug_toolbar.toolbar import debug_toolbar_urls

    urlpatterns += debug_toolbar_urls()

# Sentry is off under DEBUG, so confirming the wiring means exercising it on a real
# deployment. Opt in there with SENTRY_DEBUG_ENDPOINT, hit the route, then unset it.
if os.getenv("SENTRY_DEBUG_ENDPOINT"):
    from clubManager.observability import trigger_error

    urlpatterns.append(path("sentry-debug/", trigger_error))
