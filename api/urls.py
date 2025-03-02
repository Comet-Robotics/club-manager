from django.urls import include, path
from rest_framework import routers
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from . import views

router = routers.DefaultRouter()
router.register(r"users", views.UserViewSet, basename="user")
router.register(r"products", views.ProductViewSet, basename="product")
router.register(r"combatteams", views.CombatTeamViewSet, basename="combatteam")
router.register(r"combatrobots", views.CombatRobotViewSet, basename="combatrobot")
router.register(r"combatevents", views.CombatEventViewSet, basename="combatevent")
router.register(r"events", views.EventViewSet, basename="event")
router.register(r"waivers", views.WaiverViewSet, basename="waiver")

# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
urlpatterns = [
    path("", include(router.urls)),
    path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    path("csrf/", views.get_csrf, name="api-csrf"),
    path("auth/login/", views.LoginView.as_view(), name="api-login"),
    path("auth/logout/", views.LogoutView.as_view(), name="api-logout"),
    path("auth/session/", views.SessionView.as_view(), name="api-session"),
    path("auth/whoami/", views.WhoAmIView.as_view(), name="api-whoami"),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "schema/swagger-ui/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "schema/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
    path(
        "combatteams/<int:combatteam_id>/robots/",
        views.RobotsInTeamView.as_view(),
        name="robots-in-team",
    ),
    path(
        "combatevents/<int:combatevent_id>/robots/",
        views.RobotsInEventView.as_view(),
        name="robots-in-event",
    ),
]
