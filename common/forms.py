from django import forms
from common.utils import is_valid_net_id, normalize_username


class NetIDField(forms.CharField):
    """
    A Net ID, normalized to the same lowercase form used for storage.
    """

    DEFAULT_MAX_LENGTH = 9

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("label", "Net ID")
        kwargs.setdefault("max_length", self.DEFAULT_MAX_LENGTH)
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        value = super().to_python(value)
        return normalize_username(value)

    def validate(self, value):
        super().validate(value)
        if not is_valid_net_id(value):
            raise forms.ValidationError("Invalid Net ID!")

    def widget_attrs(self, widget):
        defaults = {
            **super().widget_attrs(widget),
            "autocapitalize": "none",
            "autocorrect": "off",
            "autocomplete": "off",
            "spellcheck": "false",
            "inputmode": "text",
        }
        return {key: value for key, value in defaults.items() if key not in widget.attrs}
