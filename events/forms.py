from typing import Any
from django import forms
from .utils import format_card_data, is_valid_card_data, is_valid_net_id

class CometCardField(forms.CharField):
    card_data = forms.CharField()

    def to_python(self, value):
        return format_card_data(value)

    def validate(self, value):
        super().validate(value)
        if not is_valid_card_data(value):
            raise forms.ValidationError("Invalid Card Data!")

class NetIDField(forms.CharField):
    net_id = forms.CharField()

    def to_python(self, value):
        return value.lower()

    def validate(self, value):
        super().validate(value)
        if not is_valid_net_id(value):
            raise forms.ValidationError("Invalid Net ID!")


class SignInForm(forms.Form):
    card_data = CometCardField(label='Swipe Card', max_length=100, widget=forms.TextInput(attrs={'autofocus': True, 'class': "input input-bordered"}))

class CreateProfileForm(forms.Form):
    first_name = forms.CharField(label='First Name', max_length=100)
    last_name = forms.CharField(label='Last Name', max_length=100)
    net_id = NetIDField(label='Net ID', max_length=20)

class UserSearchForm(forms.Form):
    search = forms.CharField(label='Search', max_length=100, required=False, widget=forms.TextInput(attrs={'autofocus': True, 'class': "input input-bordered"}))
    
class RSVPForm(forms.Form):
    first_name = forms.CharField(label='First Name', max_length=100, widget=forms.TextInput(
                              attrs={'class': "input input-bordered"}))
    last_name = forms.CharField(label='Last Name', max_length=100, widget=forms.TextInput(
                              attrs={'class': "input input-bordered"}))
    net_id = NetIDField(label='Net ID', max_length=20, widget=forms.TextInput(
                              attrs={'class': "input input-bordered"}))
