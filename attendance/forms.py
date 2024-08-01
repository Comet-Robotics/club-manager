from typing import Any
from django import forms
from .utils import format_card_data, is_valid_card_data

class CometCardField(forms.CharField):
    card_data = forms.CharField()

    def to_python(self, value):
        return format_card_data(value)

    def validate(self, value):
        super().validate(value)
        if not is_valid_card_data(value):
            raise forms.ValidationError("Invalid card data!")


class SignInForm(forms.Form):
    card_data = CometCardField(label='Swipe Card', max_length=100, widget=forms.TextInput(attrs={'autofocus': True}))

class CreateProfileForm(forms.Form):
    first_name = forms.CharField(label='First Name', max_length=100)
    last_name = forms.CharField(label='Last Name', max_length=100)
    net_id = forms.CharField(label='Net ID', max_length=20)

class UserSearchForm(forms.Form):
    search = forms.CharField(label='Search', max_length=100, required=False)