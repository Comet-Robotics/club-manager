from django.urls import path
from . import views

urlpatterns = [
    path("<int:event_id>/sign-in/", views.sign_in, name="sign_in"),
    path(
        "<int:event_id>/pass-sign-in/<int:user_id>",
        views.pass_sign_in,
        name="pass_sign_in",
    ),
    path(
        "<int:event_id>/pass-link/<int:user_id>/<int:student_id>/",
        views.pass_link,
        name="pass_link",
    ),
    path(
        "create-profile/<int:student_id>/",
        views.create_profile,
        name="create-profile",
    ),
    path("<int:event_id>/lookup-user/", views.lookup_user, name="lookup-user"),
    path(
        "<int:event_id>/lookup-user/<int:student_id>/",
        views.lookup_user,
        name="lookup-user",
    ),
    path("<int:event_id>/rsvp/", views.rsvp, name="rsvp"),
    path("<int:event_id>/report/", views.report, name="report"),
]
