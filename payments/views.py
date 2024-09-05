from django.shortcuts import render
from .forms import PaymentSignInForm
import configparser
import json
from square.client import Client
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


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
def choose_user(request):
    form = PaymentSignInForm()
    return render(request, 'choose_user.html', {'form': form})

def payment_form(request):
    return render(request, 'payment_form.html', {'APPLICATION_ID': APPLICATION_ID, 'LOCATION_ID': LOCATION_ID, 'ACCESS_TOKEN': ACCESS_TOKEN, 'PAYMENT_FORM_URL': PAYMENT_FORM_URL, 'ACCOUNT_CURRENCY': ACCOUNT_CURRENCY, 'ACCOUNT_COUNTRY': ACCOUNT_COUNTRY})

@csrf_exempt
def process_payment(request):
    if request.method == 'POST': 
        requestBody = json.loads(request.body)
        token = requestBody.get('token')
        idempotency_key = requestBody.get('idempotencyKey')
        
        
        create_payment_response = client.payments.create_payment(
        body={
            "source_id": token,
            "idempotency_key": idempotency_key,
            "amount_money": {
                "amount": 50,  # $1.00 charge
                "currency": ACCOUNT_CURRENCY,
            },
        }
        )
        
        print(create_payment_response.body)
        
        if create_payment_response.is_success():
            print(create_payment_response.body)
            return JsonResponse(create_payment_response.body, safe=False)
        elif create_payment_response.is_error():
            return JsonResponse(create_payment_response.body, safe=False)