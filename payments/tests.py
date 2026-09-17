"""
Payment is keyed on the Net ID, not on an authenticated session. Registration never
signs anyone in, so these cover the seam: a member who just registered is anonymous
and must still be able to pay.

The registration email is addressed from whatever Net ID was typed into the payment
form, so an unknown Net ID gets a confirmation step before anything is sent - a typo
must not mail a stranger.
"""

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.utils.html import escape

from accounts.models import RegistrationEmailError, UserStub
from core.models import ServerSettings
from payments.models import Payment, Product, Term


class PaymentRegistrationTestCase(TestCase):
    """
    Base for the payment-page registration tests.

    Creating a `User` kicks off a NetID -> major directory lookup, and saving a
    `UserProfile` fires the member-role signal, which needs a current `Term` to
    resolve membership and would otherwise call out to the bot API. Give it a real
    Term - on its own product, so the product under test stays an ordinary one - and
    stub the outbound calls. `UserStub.notify` reads the organization name off
    `ServerSettings`, so there has to be a row for it.
    """

    def setUp(self):
        super().setUp()
        today = timezone.now().date()
        Term.objects.create(
            name="Test Term",
            start_date=today - timedelta(days=30),
            end_date=today + timedelta(days=30),
            product=Product.objects.create(name="Membership Dues", amount_cents=2000, max_purchases_per_user=1),
        )
        for target, replacement in (
            ("core.signals.handlers.add_member_role", AsyncMock(return_value=True)),
            ("core.signals.handlers.get_major_from_netid", MagicMock(return_value=None)),
        ):
            patcher = patch(target, new=replacement)
            patcher.start()
            self.addCleanup(patcher.stop)

        ServerSettings.objects.get_or_create(defaults={"organization_name": "Comet Robotics"})

        self.product = Product.objects.create(name="Dues", amount_cents=2000, max_purchases_per_user=-1)
        self.pay_url = reverse("choose_user", args=[self.product.id])

    def pay_as(self, net_id, **extra):
        return self.client.post(self.pay_url, {"username": net_id, "payment_method": "cash", **extra})

    def confirm_registration_for(self, net_id):
        return self.pay_as(net_id, confirm_registration="1")


class PaymentAfterRegistrationTests(PaymentRegistrationTestCase):
    def test_signed_out_user_can_pay_cash(self):
        """The whole flow: unknown net id -> confirm -> stub -> registration -> pay."""
        # 1. An unknown Net ID asks for confirmation before anything is sent.
        response = self.pay_as("abc123456")
        self.assertContains(response, "Is that your Net ID?")
        self.assertFalse(UserStub.objects.filter(net_id="abc123456").exists())

        # 2. Confirming it spawns the registration stub and emails the link.
        response = self.confirm_registration_for("abc123456")
        self.assertContains(response, "Check your UT Dallas email")
        stub = UserStub.objects.get(net_id="abc123456")
        self.assertEqual(stub.after_registration_redirect_destination, self.pay_url)

        # 3. Finish registration. No login happens.
        response = self.client.post(
            reverse("registration_complete", args=[stub.user_registration_key]),
            {"first_name": "Ada", "last_name": "Lovelace"},
        )
        self.assertRedirects(response, self.pay_url, fetch_redirect_response=False)
        self.assertNotIn("_auth_user_id", self.client.session)

        user = User.objects.get(username="abc123456")
        self.assertTrue(user.is_active)
        self.assertFalse(user.has_usable_password())

        # 4. Follow the redirect: the payment page renders for an anonymous visitor.
        self.assertEqual(self.client.get(self.pay_url).status_code, 200)

        # 5. And the payment goes through, keyed on the Net ID alone.
        response = self.pay_as("abc123456")
        payment = Payment.objects.get(user=user)
        self.assertRedirects(response, reverse("payment_success", args=[payment.id]), fetch_redirect_response=False)
        self.assertEqual(payment.amount_cents, 2000)

    def test_payment_success_page_renders_signed_out(self):
        user = User.objects.create(username="abc123456", is_active=True)
        user.set_unusable_password()
        user.save()

        self.pay_as("abc123456")
        payment = Payment.objects.get(user=user)

        response = self.client.get(reverse("payment_success", args=[payment.id]))
        self.assertEqual(response.status_code, 200)


class UnknownNetIDConfirmationTests(PaymentRegistrationTestCase):
    def test_unknown_net_id_asks_before_registering_anyone(self):
        response = self.pay_as("abc123456")

        self.assertContains(response, "abc123456")
        self.assertContains(response, "Is that your Net ID?")
        self.assertContains(response, "Yes, email me a registration link")
        self.assertFalse(UserStub.objects.exists())
        self.assertEqual(mail.outbox, [])

    def test_confirming_creates_the_stub_and_sends_one_email(self):
        response = self.confirm_registration_for("abc123456")

        self.assertContains(
            response,
            escape(
                "Check your UT Dallas email for a link to finish registering — "
                "it will bring you back here to finish this payment."
            ),
        )
        stub = UserStub.objects.get(net_id="abc123456")
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ["abc123456@utdallas.edu"])
        self.assertIn(stub.get_registration_url(), message.body)

    def test_confirming_again_does_not_resend_the_email(self):
        UserStub.create(net_id="abc123456", after_registration_redirect_destination=self.pay_url)
        mail.outbox = []

        response = self.confirm_registration_for("abc123456")

        self.assertContains(
            response,
            escape(
                "We already emailed abc123456@utdallas.edu a registration link recently — check your inbox (and spam)."
            ),
        )
        self.assertEqual(mail.outbox, [])

    @patch("payments.views.UserStub.notify", side_effect=RegistrationEmailError)
    def test_an_undeliverable_email_leaves_no_stub_behind(self, _notify):
        response = self.confirm_registration_for("abc123456")

        self.assertContains(
            response,
            escape("We couldn't send the registration email. Please try again in a few minutes or ask an officer."),
        )
        self.assertFalse(UserStub.objects.exists())

    def test_a_known_net_id_never_sees_the_confirmation(self):
        user = User.objects.create(username="abc123456")

        response = self.pay_as("abc123456")

        payment = Payment.objects.get(user=user)
        self.assertRedirects(response, reverse("payment_success", args=[payment.id]), fetch_redirect_response=False)
        self.assertEqual(mail.outbox, [])

    def test_confirming_a_net_id_that_registered_in_the_meantime_just_pays(self):
        """The account can appear between typing the Net ID and confirming it."""
        user = User.objects.create(username="abc123456")

        response = self.confirm_registration_for("abc123456")

        payment = Payment.objects.get(user=user)
        self.assertRedirects(response, reverse("payment_success", args=[payment.id]), fetch_redirect_response=False)
        self.assertFalse(UserStub.objects.exists())
        self.assertEqual(mail.outbox, [])
