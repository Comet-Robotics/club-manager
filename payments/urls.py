from django.urls import path
from . import views

urlpatterns = [
    path('<int:product_id>/pay/', views.choose_user, name='choose_user'),
    path('<int:product_id>/pay/<int:user_id>/', views.payment_form, name='payment_form'),
    path('<int:product_id>/pay/<int:user_id>/process-payment/', views.process_payment, name='process_payment'),
]