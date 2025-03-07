from django import forms
from common.forms import NetIDField
from clubManager import settings


class PaymentSignInForm(forms.Form):
    payment_choices = [
        ("cash", "In-Person Cash Payment"),
    ]
    if settings.ENABLE_SQUARE_PAYMENTS:
        payment_choices.append(("square_api", "Credit Card/Debit Card (Online)"))

    # TODO: allow username to not be a net id
    username = NetIDField(
        label="Net ID",
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={"autofocus": True}),
    )
    payment_method = forms.ChoiceField(
        label="Payment Method",
        choices=payment_choices,
        required=True,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
