from django.shortcuts import render, get_object_or_404, redirect
from .forms import PaymentSignInForm
import configparser
from django.utils import timezone
import json
from square.client import Client
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.views import View
from payments.models import Payment, Product, PurchasedProduct
from math import ceil
from typing import TypedDict
from django.db import transaction


config = configparser.ConfigParser()
config.read("config.ini")

CONFIG_TYPE = config.get("DEFAULT", "environment").upper()

PAYMENT_FORM_URL = (
"https://web.squarecdn.com/v1/square.js"
if CONFIG_TYPE == "PRODUCTION"
else "https://sandbox.web.squarecdn.com/v1/square.js")

APPLICATION_ID = config.get(CONFIG_TYPE, "square_application_id")
LOCATION_ID = config.get(CONFIG_TYPE, "square_location_id")
ACCESS_TOKEN = config.get(CONFIG_TYPE, "square_access_token")

client = Client(
    access_token=ACCESS_TOKEN,
    environment=config.get("DEFAULT", "environment"),
)

location = client.locations.retrieve_location(location_id=LOCATION_ID).body["location"]
ACCOUNT_CURRENCY = location["currency"]
ACCOUNT_COUNTRY = location["country"]

def can_purchase_product(product, user):
    """
    Returns None if product can be purchased, otherwise returns a string messsage explaining why it can't be purchased
    """
    if product.max_purchases_per_user == -1:
        # Unlimited purchases
        return None
    elif product.max_purchases_per_user == 0:
      # No purchases allowed
      return "Payments are currently disabled for this object."
    else:
      # Purchases allowed, but need to check if user has reached max purchases
      
      # TODO: need to test this
  
      total_purchased = PurchasedProduct.objects.filter(
                  product=product,
                  payment__user=user,
                  payment__is_successful=True
              ).aggregate(total_quantity=Sum('quantity'))['total_quantity'] or 0
      
      allowed = total_purchased < product.max_purchases_per_user
      
      if allowed:
          return None
      else:
        return "You have reached the maximum number of purchases for this object."

class CostWithFee(TypedDict):
    product_amount_cents: int
    square_fee_cents: int
    total_payment_amount_cents: int


def calculate_cost_with_square_fee(amount_cents: int) -> CostWithFee:
  """
  Calculate the total amount in cents required to cover Square's transaction fees, ensuring the specified `amount_cents` is earned as net revenue without losses to Square fees.
  
  This function takes an input amount in cents and returns the total amount in cents needed to account for Square's fees. Square charges a fee of 30 cents plus 2.9% of the transaction amount. To ensure the full desired amount is received as revenue, the calculation involves adjusting the input amount using the formula: `(desired_amount + fixed_fee) / (1 - variable_fee)`. This approach accounts for the fixed 30-cent fee and the 2.9% variable fee. 
  
  For more details, refer to [Square's pricing documentation](https://developer.squareup.com/docs/payments-pricing#online-and-in-app-payments).
  """
  
  total_payment_amount_cents = ceil((amount_cents + 30) / (1 - 0.029))
  square_fee_cents = total_payment_amount_cents - amount_cents
  
  return CostWithFee(
        product_amount_cents=amount_cents,
        square_fee_cents=square_fee_cents,
        total_payment_amount_cents=total_payment_amount_cents
  )
  

class PaymentSuccessView(View):
    template_name = 'payment_success.html'

    def get(self, request, payment_id):
        payment = get_object_or_404(Payment, id=payment_id)
        return render(request, self.template_name, {'product_name': payment.purchased_products.first().product.name, 'payment': payment})

class ChooseUserView(View):
    template_name = 'choose_user.html'

    def get(self, request, product_id):
        product = get_object_or_404(Product, id=product_id)
        form = PaymentSignInForm()
        return render(request, self.template_name, {'form': form, 'product_name': product.name})

    def post(self, request, product_id):
        form = PaymentSignInForm(request.POST)
        product = get_object_or_404(Product, id=product_id)
        if form.is_valid():
            username = form.cleaned_data['username']
            payment_choice = form.cleaned_data['payment_method']
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                return render(request, self.template_name, {'form': form, 'message': 'User not found', 'product_name': product.name})
                
            message = can_purchase_product(product, user)
            if message:
                return render(request, self.template_name, {'form': form, 'message': message, 'product_name': product.name})
            else:
                if payment_choice == 'square_api':
                    return redirect('payment_form', product_id=product_id, user_id=user.id)
                elif payment_choice == 'cash':
                  with transaction.atomic():
                    payment = Payment(method=Payment.Method.cash, user=user, amount_cents=product.amount_cents)
                    payment.save()
                    purchased_product = PurchasedProduct(product=product, payment=payment)
                    purchased_product.save()
                  return redirect('payment_success', payment_id=purchased_product.payment.id)
                else:
                  raise Exception("Invalid payment choice")
        return render(request, self.template_name, {'form': form, 'product_name': product.name})

def product_payment(request, product_id, user_id):
    product = get_object_or_404(Product, id=product_id)
    fees = calculate_cost_with_square_fee(product.amount_cents)
    
    process_fee = fees["square_fee_cents"]
    total_cost = fees["total_payment_amount_cents"]
    
    
    return render(request, 'product_payment.html', {'product': product, 'user_id': user_id, 'process_fee': process_fee, 'total_cost': total_cost, 'APPLICATION_ID': APPLICATION_ID, 'LOCATION_ID': LOCATION_ID, 'ACCESS_TOKEN': ACCESS_TOKEN, 'PAYMENT_FORM_URL': PAYMENT_FORM_URL, 'ACCOUNT_CURRENCY': ACCOUNT_CURRENCY, 'ACCOUNT_COUNTRY': ACCOUNT_COUNTRY})

@csrf_exempt
def process_square_payment(request, product_id, user_id):
    if request.method == 'POST': 
        requestBody = json.loads(request.body)
        
        token = requestBody.get('token')
        idempotency_key = requestBody.get('idempotencyKey')
        
        product = get_object_or_404(Product, id=product_id)
        user = get_object_or_404(User, id=user_id)
        
        message = can_purchase_product(product, user)
        if message:
          return JsonResponse({'square_res': {'errors': [{'detail': message}]}}, safe=False)
        
        fees = calculate_cost_with_square_fee(product.amount_cents)
        
        with transaction.atomic():
          payment = Payment(method=Payment.Method.square_api, user=user, amount_cents=fees["total_payment_amount_cents"])
          payment.save()
          purchased_product = PurchasedProduct(product=product, payment=payment)
          purchased_product.save()
        
        create_payment_response = client.payments.create_payment(
          body={
            "source_id": token,
            "idempotency_key": idempotency_key,
            "amount_money": {
                "amount": payment.amount_cents,
                "currency": ACCOUNT_CURRENCY,
            },
            "reference_id": str(payment.pk),
            "note": str(payment),
          }
        )
        
        payment.metadata = {"square_response_body": create_payment_response.body}
        payment.save()
        
        if create_payment_response.is_success():
            payment.completed_at = timezone.now()
            payment.save()
            return JsonResponse({"square_res": create_payment_response.body, "payment_success_page": f"/payments/{payment.id}/success"}, safe=False)
        elif create_payment_response.is_error():
            return JsonResponse({"square_res": create_payment_response.body}, safe=False)
    else:
        return JsonResponse({'error': 'Invalid request method'}, safe=False, status_code=405)
            