from django import forms
from django.test import SimpleTestCase

from accounts.forms import RegistrationRequestForm
from common.forms import NetIDField
from events.forms import RSVPForm, SelfSignInForm
from payments.forms import PaymentSignInForm


class NetIDFieldTests(SimpleTestCase):
    def test_shared_configuration_across_forms(self):
        for form_class, name in (
            (RegistrationRequestForm, "net_id"),
            (RSVPForm, "net_id"),
            (SelfSignInForm, "username"),
            (PaymentSignInForm, "username"),
        ):
            with self.subTest(form=form_class.__name__):
                field = form_class().fields[name]
                assert isinstance(field, NetIDField)
                self.assertEqual(field.label, "Net ID")
                self.assertEqual(field.max_length, 9)
                self.assertTrue(field.required)
                self.assertEqual(field.widget.attrs["maxlength"], "9")
                for attr, value in {
                    "autocapitalize": "none",
                    "autocorrect": "off",
                    "spellcheck": "false",
                    "inputmode": "text",
                }.items():
                    self.assertEqual(field.widget.attrs[attr], value)
                self.assertEqual(field.clean("  ABC123456  "), "abc123456")
                for invalid in ("", "invalid", "abc1234567"):
                    with self.subTest(value=invalid), self.assertRaises(forms.ValidationError):
                        field.clean(invalid)

    def test_surface_specific_widget_attributes(self):
        self.assertEqual(SelfSignInForm().fields["username"].widget.attrs["autocomplete"], "username")
        self.assertEqual(RegistrationRequestForm().fields["net_id"].widget.attrs["autocomplete"], "off")
        self.assertEqual(PaymentSignInForm().fields["username"].widget.attrs["autocomplete"], "off")
        for form, name in (
            (SelfSignInForm(), "username"),
            (RegistrationRequestForm(), "net_id"),
            (PaymentSignInForm(), "username"),
        ):
            self.assertTrue(form.fields[name].widget.attrs["autofocus"])
        self.assertNotIn("autofocus", RSVPForm().fields["net_id"].widget.attrs)

    def test_field_defaults_can_be_overridden(self):
        field = NetIDField(label="Custom label", widget=forms.TextInput(attrs={"autocomplete": "username"}))
        self.assertEqual(field.label, "Custom label")
        self.assertEqual(field.widget.attrs["autocomplete"], "username")
