from django import forms
from .models import UserProfile
from phonenumber_field.formfields import PhoneNumberField

class PhoneNumberForm(forms.Form):
    phone_number = PhoneNumberField(region='US')
    

class ContactInfoForm(forms.Form):
    first_name = forms.CharField(label='First Name', max_length=100)
    last_name = forms.CharField(label='Last Name', max_length=100)
    # Contact = PhoneNumberForm(label='Phone Number')
    
class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['gender', 'race', 'diet', 'shirt', 'is_lgbt', 'is_hispanic', 'date_of_birth']