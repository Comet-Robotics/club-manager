from typing import Any
from django import forms

from events.models import Event
from .utils import format_card_data, is_valid_card_data, is_valid_net_id


class CometCardField(forms.CharField):
    card_data = forms.CharField()

    def to_python(self, value):
        return format_card_data(value)

    def validate(self, value):
        super().validate(value)
        if not is_valid_card_data(value):
            raise forms.ValidationError("Invalid Card Data!")


class NetIDField(forms.CharField):
    net_id = forms.CharField()

    def to_python(self, value):
        return value.lower()

    def validate(self, value):
        super().validate(value)
        if not is_valid_net_id(value):
            raise forms.ValidationError("Invalid Net ID!")


class SignInForm(forms.Form):
    card_data = CometCardField(
        label="Swipe Card",
        max_length=100,
        widget=forms.TextInput(attrs={"autofocus": True}),
    )


class UserSearchForm(forms.Form):
    search = forms.CharField(
        label="Search",
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={"autofocus": True}),
    )


class RSVPForm(forms.Form):
    first_name = forms.CharField(
        label="First Name", max_length=100
    )
    last_name = forms.CharField(
        label="Last Name", max_length=100
    )
    # TODO: allow username to not be a net id
    net_id = NetIDField(label="Net ID", max_length=20)


class EventForm(forms.ModelForm):
    project_id = forms.IntegerField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = Event
        exclude = ["created_at", "updated_at"]

        widgets = {
            "event_date": forms.DateTimeInput(
                format=("%Y-%m-%dT%H:%M"), attrs={"class": "form-control", "type": "datetime-local"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super(EventForm, self).__init__(*args, **kwargs)
        if self.instance and self.instance.event_date:
            self.fields["event_date"].initial = self.instance.event_date.strftime("%Y-%m-%dT%H:%M")

        # Prefill project field if project_id is provided in initial data
        if "initial" in kwargs and "project_id" in kwargs["initial"]:
            project_id = kwargs["initial"]["project_id"]
            try:
                from projects.models import Project

                project = Project.objects.get(pk=project_id)
                self.fields["project"].initial = project
            except Project.DoesNotExist:
                pass
