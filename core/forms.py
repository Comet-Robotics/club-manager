from django import forms
from core.models import ServerSettings

class ServerSettingsForm(forms.ModelForm):
    class Meta:
        model = ServerSettings
        exclude = ['_singleton', 'logo']
        
    # TODO: create a separate form for the logo so that form can be submitted independently of this one, so we don't have to reupload the image every time the form is submitted
        