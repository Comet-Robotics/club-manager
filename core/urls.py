from django.urls import path, re_path
from . import views


urlpatterns = [
    path("profile/", views.profile_view, name="profile"),
    path("server-settings/", views.server_settings_view, name="server_settings"),
    path("account/", views.account_view, name="account"),
    path(
        ".well-known/apple-developer-merchantid-domain-association", views.apple_merchant_id, name="apple_merchant_id"
    ),
    re_path("^_/*", views.spa_view, name="spa"),
    path("", views.index, name="index"),
    path("profile/fragments/attendance", views.AttendanceListView.as_view(), name="attendance_list"),
]
