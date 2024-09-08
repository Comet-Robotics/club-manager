from django import forms
from common.forms import NetIDField

class PaymentSignInForm(forms.Form):
    username = NetIDField(label='Net ID', max_length=20, widget=forms.TextInput(attrs={'autofocus': True}))
