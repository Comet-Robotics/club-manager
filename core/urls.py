from django.urls import path
from . import views

urlpatterns = [
    path('profile/', views.profile_view, name='profile'),
    path('.well-known/apple-developer-merchantid-domain-association', views.apple_merchant_id, name='apple_merchant_id'),
]