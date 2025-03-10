from typing import Any
from django import forms
from common.utils import is_valid_net_id


class NetIDField(forms.CharField):
    net_id = forms.CharField()

    def to_python(self, value):
        return value.lower()

    def validate(self, value):
        super().validate(value)
        if not is_valid_net_id(value):
            raise forms.ValidationError("Invalid Net ID!")
