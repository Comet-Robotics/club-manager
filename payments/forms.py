from django import forms
from common.forms import NetIDField

class PaymentSignInForm(forms.Form):
    
    payment_choices = [
        ('square_api', 'Credit Card/Debit Card (Online)'),
        ('cash', 'In-Person Cash Payment'),
    ]
    username = NetIDField(label='Net ID', max_length=20, required=True, widget=forms.TextInput(attrs={'autofocus': True}))
    payment_method = forms.ChoiceField(label='Payment Method', choices=payment_choices, required=True, widget=forms.Select(attrs={'class': 'form-control'}))