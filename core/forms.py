from django import forms
from .models import UserProfile, User, ServerSettings


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ["gender", "date_of_birth", "race", "is_hispanic", "diet", "shirt", "major"]
        labels = {
            "is_hispanic": "Are you Hispanic or Latino?",
            "race": "Select all races that you identify with",
            "diet": "Select any dietary restrictions",
            "shirt": "Shirt Size",
        }
        widgets = {
            "date_of_birth": forms.DateInput(format=("%Y-%m-%d"), attrs={"class": "form-control", "type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super(UserProfileForm, self).__init__(*args, **kwargs)
        if self.instance and self.instance.date_of_birth:
            self.fields["date_of_birth"].initial = self.instance.date_of_birth.strftime("%Y-%m-%d")


class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name"]


class ServerSettingsForm(forms.ModelForm):
    class Meta:
        model = ServerSettings
        exclude = ["_singleton", "logo"]

class ServerSettingsLogoForm(forms.ModelForm):
    class Meta:
        model = ServerSettings
        fields = ["logo"]