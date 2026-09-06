from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import SetPasswordForm
from common.forms import NetIDField


class RegistrationRequestForm(forms.Form):
    net_id = NetIDField(label="Net ID", max_length=20, widget=forms.TextInput(attrs={"autofocus": True}))


class RegistrationCompletionForm(forms.ModelForm):
    """
    Collects the details a registration needs onto the unsaved `User` from
    `UserStub.build_user`. No password: registration does not create a login.

    `link_discord` only exists when the registration was started from Discord, because it
    asks about a specific account the person can see on the page. Offering it otherwise
    would be asking about nothing. It is answered by which button submits the form rather
    than by a checkbox, so there is no pre-filled answer to skim past: someone who never
    started this from Discord has to actively choose to hand that account the link.
    """

    link_discord = forms.TypedChoiceField(
        choices=[("yes", "Link this Discord account"), ("no", "Don't link it")],
        coerce=lambda value: value == "yes",
        error_messages={"required": "Choose whether to link this Discord account."},
    )

    class Meta:
        model = User
        fields = ["first_name", "last_name"]
        labels = {"first_name": "First name", "last_name": "Last name"}

    def __init__(self, user, data=None, files=None, *, has_pending_discord_id: bool = False, **kwargs):
        super().__init__(data=data, files=files, instance=user, **kwargs)
        for field in self.fields.values():
            field.required = True

        if not has_pending_discord_id:
            del self.fields["link_discord"]
