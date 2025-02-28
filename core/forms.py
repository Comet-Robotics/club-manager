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
        fields = ['gender',  'date_of_birth', 'race', 'is_hispanic','diet', 'shirt', 'major']
        labels = {
            "is_hispanic": "Are you Hispanic or Latino?",
            "race": "Select all races that you identify with",
            "diet": "Select any dietary restrictions",
            "shirt": "Shirt Size"
        }
        widgets = {
            'date_of_birth': forms.DateInput(format=('%Y-%m-%d'), attrs={'class':'form-control',  'type':'date'}),
        }

    def __init__(self, *args, **kwargs):
        super(UserProfileForm, self).__init__(*args, **kwargs)
        if self.instance and self.instance.date_of_birth:
            self.fields['date_of_birth'].initial = self.instance.date_of_birth.strftime('%Y-%m-%d')
        
class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name']
from core.models import ServerSettings

class ServerSettingsForm(forms.ModelForm):
    class Meta:
        model = ServerSettings
        exclude = ['_singleton', 'logo']
        
    # TODO: create a separate form for the logo so that form can be submitted independently of this one, so we don't have to reupload the image every time the form is submitted
        
