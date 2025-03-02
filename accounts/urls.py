from django.urls import path
from . import views

urlpatterns = [
    path(
        "link/<uuid:uuid>", views.LinkSocialView.as_view(), name="link_social"
    ),
    path("link_success", views.LinkSuccessView.as_view(), name="link_success"),
]
