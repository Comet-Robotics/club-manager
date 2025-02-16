from django import forms

class PhoneNumberField(forms.IntegerField):
    phone = forms.IntegerField()

    def validate(self, value):
        super().validate(value)
        if not is_valid_phone_number(value):
            raise forms.ValidationError("Invalid Phone Number!")

class ContactInfoForm(forms.Form):
    first_name = forms.CharField(label='First Name', max_length=100)
    last_name = forms.CharField(label='Last Name', max_length=100)
    Contact = PhoneNumberField(label='Phone Number', max_length=10)