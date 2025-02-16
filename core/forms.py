from django import forms
from phonenumber_field.formfields import PhoneNumberField

class PhoneNumberForm(forms.Form):
    phone_number = PhoneNumberField(region='US')

class ContactInfoForm(forms.Form):
    first_name = forms.CharField(label='First Name', max_length=100)
    last_name = forms.CharField(label='Last Name', max_length=100)
    Contact = PhoneNumberForm(label='Phone Number', max_length=10)