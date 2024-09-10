from django.urls import path
from . import views

urlpatterns = [
    path('link/<str:uuid>', views.LinkSocialView.as_view(), name='link_social'),
]