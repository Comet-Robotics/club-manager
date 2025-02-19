from django import forms
from core.models import ServerSettings

class ServerSettingsForm(forms.ModelForm):
    class Meta:
        model = ServerSettings
        exclude = ['_singleton', 'logo']
        
    # TODO: create a separate form for the logo
        