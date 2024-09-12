from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

def is_valid_card_data(data: str):
    # Implement your validation logic here
    # For example, check if the data is a number and has the correct length
    return data.isdigit() and len(data) == 16

def is_valid_net_id(data: str):
    letters = data[0:3]
    numbers = data[3:]
    is_correct_length = len(letters) == 3 and len(numbers) == 6
    return is_correct_length and letters.isalpha() and numbers.isdigit()

def validate_staff(user_pk: int):
    user = User.objects.get(pk=user_pk)
    if not user.is_staff:
        raise ValidationError(
            _("%(username)s is not staff"),
            params={"username": user.username},
        )
