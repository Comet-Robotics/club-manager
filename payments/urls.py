from django.urls import path
from . import views

urlpatterns = [
    path('<int:payment_id>/success', views.PaymentSuccessView.as_view(), name='payment_success'),
    path('<int:product_id>/pay/', views.ChooseUserView.as_view(), name='choose_user'),
    path('<int:product_id>/pay/<int:user_id>/', views.product_payment, name='payment_form'),
    path('<int:product_id>/pay/<int:user_id>/process-payment/', views.process_square_payment, name='process_payment'),
]