from django.urls import path
from . import views

urlpatterns = [
    path('sign-in/', views.choose_user, name='choose_user'),
]