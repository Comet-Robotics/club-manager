import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clubManager.settings')
from clubManager import settings

import django
django.setup()

import csv
from datetime import datetime
from django.utils import timezone
from django.utils.timezone import make_aware
from payments.models import Payment, Product, Term
from django.contrib.auth.models import User

def parse_csv_and_store_data(file_path):
    scanTime = timezone.now()
    verifier = User.objects.get(username='osd220000')

        
    with open(file_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            try:
                payment_date = make_aware(datetime.strptime(row['Timestamp'], '%m/%d/%Y %H:%M:%S')) if row['Timestamp'] else None
                first_name = row['First Name']
                last_name = row['Last Name']
                net_id = row['Net ID'].lower()
                payment_method = row['Which payment method will you use to pay your $10 member dues?']
                has_paid = row['Has Paid?'] == 'Yes'
                approval_date = make_aware(datetime.strptime(row['When?'], '%m/%d/%Y %I:%M %p')) if row['When?'] else None

                if not has_paid:
                    continue
                
                selected_term = Term.objects.get(id=1)
                current_product = Product.objects.get(term=selected_term)
                
                
                #TODO need to manually enter these payment methods
                if payment_method == "Other Payment Method":
                    continue
                
                # Create or get the user
                user, created = User.objects.get_or_create(
                    defaults={
                        'first_name': first_name,
                        'last_name': last_name,
                        'username': net_id,
                    },
                    username=net_id
                )
                
                methods = {
                    "Regular Cash": "cash",
                    "Cash App": "cashapp",
                    "PayPal": "paypal",
                }
                
                # Create the payment
                Payment.objects.create(
                    user=user,
                    product=current_product,  # Replace with actual product instance
                    amount_cents=1000,  # Assuming $10 member dues
                    created_at=payment_date,
                    updated_at=approval_date,
                    method=methods[payment_method],
                    verified_by=verifier,
                    notes=f"{scanTime} - Imported from CSV",
                    metadata={}
                )
            except Exception as e:
                print(f"Error processing row: {row}")
                print(e)

# Call the function with the path to your CSV file
parse_csv_and_store_data('term1.csv')