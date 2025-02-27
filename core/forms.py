from django import forms
from .models import UserProfile, User
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
        fields = ['gender',  'date_of_birth', 'race', 'is_hispanic','diet', 'shirt' ]
        labels = {
            "is_hispanic": "Are you Hispanic or Latino?",
            "race": "Select all races that you identify with",
            "diet": "Select any dietary restrictions",
            "shirt": "Shirt Size"
        }
        widgets = {
            'date_of_birth': forms.DateInput(format=('%m/%d/%Y'), attrs={'class':'form-control', 'placeholder':'Select a date', 'type':'date'}),
        }
        
class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name']