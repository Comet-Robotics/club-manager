from django.urls import path
from . import views

urlpatterns = [
    path('sign-in/', views.sign_in, name='sign_in'),
    path('create-profile/<int:student_id>/', views.create_profile, name='create-profile'),
    path('lookup-user/', views.lookup_user, name='lookup-user'),
]