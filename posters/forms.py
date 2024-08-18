from typing import Any
from django import forms

class PosterLogForm(forms.Form):
    poster_id = forms.IntegerField(label='Poster ID')
    latitude = forms.FloatField(label='Latitude')
    longitude = forms.FloatField(label='Longitude')
    description = forms.CharField(label='Description', required=False)