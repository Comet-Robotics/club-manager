from django.shortcuts import render, get_object_or_404, redirect
from .forms import PaymentSignInForm
import configparser
from datetime import datetime
import json
from square.client import Client
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.views import View
from payments.models import Payment, Product


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

# Create your views here.
class ChooseUserView(View):
    template_name = 'choose_user.html'

    def get(self, request, product_id):
        form = PaymentSignInForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request, product_id):
        form = PaymentSignInForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                return render(request, self.template_name, {'form': form, 'message': 'User not found'})
            return redirect('payment_form', product_id=product_id, user_id=user.id)
        return render(request, self.template_name, {'form': form})

def payment_form(request, product_id, user_id):
    return render(request, 'payment_form.html', {'APPLICATION_ID': APPLICATION_ID, 'LOCATION_ID': LOCATION_ID, 'ACCESS_TOKEN': ACCESS_TOKEN, 'PAYMENT_FORM_URL': PAYMENT_FORM_URL, 'ACCOUNT_CURRENCY': ACCOUNT_CURRENCY, 'ACCOUNT_COUNTRY': ACCOUNT_COUNTRY})

@csrf_exempt
def process_payment(request, product_id, user_id):
    if request.method == 'POST': 
        requestBody = json.loads(request.body)
        
        token = requestBody.get('token')
        idempotency_key = requestBody.get('idempotencyKey')
        
        product = get_object_or_404(Product, id=product_id)
        user = get_object_or_404(User, id=user_id)
        
        payment = Payment(method=Payment.Methods.square, product=product, user=user)
        payment.save()
        
        # TODO: if square lets us add metadata to payments, we can use that to store the payment id, user_id and other info here, so we have a paper trail in case persisting payment to DB fails
        create_payment_response = client.payments.create_payment(
        body={
            "source_id": token,
            "idempotency_key": idempotency_key,
            "amount_money": {
                "amount": payment.product.amount_cents,
                "currency": ACCOUNT_CURRENCY,
            },
        }
        )
        
        payment.metadata = {"request_body": requestBody, "response_body": create_payment_response.body}
        payment.save()
        
        if create_payment_response.is_success():
            payment.completed_at = datetime.now()
            payment.save()
            return JsonResponse(create_payment_response.body, safe=False)
        elif create_payment_response.is_error():
            return JsonResponse(create_payment_response.body, safe=False)
    else:
        return JsonResponse({'error': 'Invalid request method'}, safe=False, status_code=405)
            