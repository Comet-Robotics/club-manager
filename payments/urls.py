from django.urls import path
from . import views

urlpatterns = [
    path('sign-in/', views.choose_user, name='choose_user'),
    path('pay/', views.payment_form, name='payment_form'),
    path('pay/process-payment/', views.process_payment, name='process_payment'),
]