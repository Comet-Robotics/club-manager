from django import forms
from django.contrib.auth.models import User


class RegistrationCompletionForm(forms.ModelForm):
    """
    Collects the details a registration needs onto the unsaved `User` from
    `UserStub.build_user`. No password: registration does not create a login.

    `link_discord` only exists when the registration was started from Discord, because it
    asks about a specific account the person can see on the page. Offering it otherwise
    would be asking about nothing.
    """

    link_discord = forms.BooleanField(
        initial=True,
        label="Link this Discord account to my new account",
    )

    class Meta:
        model = User
        fields = ["first_name", "last_name"]
        labels = {"first_name": "First name", "last_name": "Last name"}

    def __init__(self, user, *args, has_pending_discord_id: bool = False, **kwargs):
        super().__init__(*args, instance=user, **kwargs)
        for field in self.fields.values():
            field.required = True

        if not has_pending_discord_id:
            del self.fields["link_discord"]
        else:
            # A checkbox that has to be ticked to submit is not a choice. Unchecked is a
            # valid answer here - it is the whole point of showing the box.
            self.fields["link_discord"].required = False
