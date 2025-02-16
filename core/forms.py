from django import forms
import re

class PhoneNumberField(forms.IntegerField):
    def validate(self, value):
        super().validate(value)
        if not self.is_valid_phone_number(value):
            raise forms.ValidationError("Invalid Phone Number!")
        
    def is_valid_phone_number(self, value):
        return re.fullmatch(r'^\+?\d{3}-\d{3}-\d{4}$', value) is not None

class ContactInfoForm(forms.Form):
    first_name = forms.CharField(label='First Name', max_length=100)
    last_name = forms.CharField(label='Last Name', max_length=100)
    Contact = PhoneNumberField(label='Phone Number', max_length=10)