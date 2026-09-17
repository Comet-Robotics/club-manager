import zoneinfo
from datetime import datetime, timedelta
from datetime import timezone as dt_timezone
from unittest import mock
from unittest.mock import AsyncMock, patch

from django.contrib.auth.models import User
from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from django.utils.html import escape

from accounts.models import RegistrationEmailError, UserStub
from core.models import ServerSettings
from payments.models import Payment, Product, PurchasedProduct, Term


def make_term(name, start_date, end_date):
    product = Product.objects.create(
        name=f"{name} dues",
        amount_cents=1000,
        max_purchases_per_user=1,
    )
    return Term.objects.create(name=name, start_date=start_date, end_date=end_date, product=product)


def make_member(username, term, *, successful=True):
    """Creates a user with a paid membership in `term`."""
    user = User.objects.create_user(username=username, password="pass")
    payment = Payment.objects.create(
        user=user,
        amount_cents=1000,
        is_successful=successful,
        completed_at=timezone.now() if successful else None,
    )
    PurchasedProduct.objects.create(product=term.product, payment=payment, quantity=1)
    return user


class TermOverlapTestCase(TestCase):
    """Terms can overlap, so more than one term may be active on a given day."""

    def setUp(self):
        self.today = timezone.localdate()
        # An overlap: Spring runs for 14 more days, Fall has already started.
        self.spring = make_term("Spring", self.today - timedelta(days=90), self.today + timedelta(days=14))
        self.fall = make_term("Fall", self.today - timedelta(days=1), self.today + timedelta(days=120))

    # get_active_terms

    def test_get_active_terms_includes_both_terms_during_overlap(self):
        self.assertEqual(set(Term.get_active_terms()), {self.spring, self.fall})

    def test_get_active_terms_excludes_expired_term(self):
        expired = make_term("Expired", self.today - timedelta(days=300), self.today - timedelta(days=1))
        self.assertNotIn(expired, Term.get_active_terms())

    def test_get_active_terms_excludes_future_term(self):
        future = make_term("Future", self.today + timedelta(days=30), self.today + timedelta(days=300))
        self.assertNotIn(future, Term.get_active_terms())

    def test_term_starting_today_is_active(self):
        starts_today = make_term("Starts Today", self.today, self.today + timedelta(days=30))
        self.assertIn(starts_today, Term.get_active_terms())

    def test_term_ending_today_is_active(self):
        ends_today = make_term("Ends Today", self.today - timedelta(days=30), self.today)
        self.assertIn(ends_today, Term.get_active_terms())

    def test_active_terms_are_computed_from_the_local_date(self):
        """Term boundaries are plain dates, so they must not be resolved against the UTC date.

        In a timezone behind UTC there is a window every evening where the UTC date is already the
        next day. Using the UTC date there would expire a member hours before their local last day
        actually ended. This test pins the clock into that window.
        """
        tz = zoneinfo.ZoneInfo("America/Chicago")
        # 2026-10-12 21:00 local is 2026-10-13 02:00 UTC, so the two dates differ.
        during_the_gap = datetime(2026, 10, 12, 21, 0, tzinfo=tz)
        local_day = during_the_gap.date()

        with mock.patch("django.utils.timezone.now", return_value=during_the_gap):
            ends_today = make_term("Ends Local Day", local_day - timedelta(days=30), local_day)
            starts_today = make_term("Starts Local Day", local_day, local_day + timedelta(days=30))
            yesterday = make_term("Already Over", local_day - timedelta(days=60), local_day - timedelta(days=1))

            active = set(Term.get_active_terms())

        # The UTC date here is 2026-10-13, which would wrongly expire `ends_today`.
        self.assertEqual(during_the_gap.astimezone(dt_timezone.utc).date(), local_day + timedelta(days=1))
        self.assertIn(ends_today, active)
        self.assertIn(starts_today, active)
        self.assertNotIn(yesterday, active)

    # get_active_term_with_earliest_end_date

    def test_earliest_end_date_term_is_the_expiring_term_during_overlap(self):
        self.assertEqual(Term.get_active_term_with_earliest_end_date(), self.spring)

    def test_earliest_end_date_term_when_only_one_is_active(self):
        self.spring.delete()
        self.assertEqual(Term.get_active_term_with_earliest_end_date(), self.fall)

    def test_earliest_end_date_term_is_none_when_no_terms_are_active(self):
        self.spring.delete()
        self.fall.delete()
        self.assertIsNone(Term.get_active_term_with_earliest_end_date())

    # get_active_term_with_latest_end_date

    def test_latest_end_date_term_is_the_renewing_term_during_overlap(self):
        self.assertEqual(Term.get_active_term_with_latest_end_date(), self.fall)

    def test_latest_end_date_term_when_only_one_is_active(self):
        self.fall.delete()
        self.assertEqual(Term.get_active_term_with_latest_end_date(), self.spring)

    def test_latest_end_date_term_is_none_when_no_terms_are_active(self):
        self.spring.delete()
        self.fall.delete()
        self.assertIsNone(Term.get_active_term_with_latest_end_date())

    def test_latest_end_date_term_prefers_newer_start_date_on_tied_end_date(self):
        """Two terms ending the same day are equally valuable; the newer one breaks the tie."""
        self.spring.delete()
        self.fall.delete()
        shared_end = self.today + timedelta(days=60)
        older = make_term("Older", self.today - timedelta(days=200), shared_end)
        newer = make_term("Newer", self.today - timedelta(days=100), shared_end)

        self.assertEqual(Term.get_active_term_with_latest_end_date(), newer)
        self.assertEqual(Term.get_active_term_with_earliest_end_date(), older)

    # get_members

    def test_get_members_returns_only_paid_purchases_for_that_term(self):
        spring_member = make_member("spring_member", self.spring)
        make_member("fall_member", self.fall)
        make_member("unpaid_spring_member", self.spring, successful=False)

        members = self.spring.get_members()

        self.assertEqual([payment.payment.user for payment in members], [spring_member])

    def test_get_members_is_empty_without_purchases(self):
        self.assertEqual(list(self.spring.get_members()), [])


# Payment is keyed on the Net ID, not on an authenticated session. Registration never
# signs anyone in, so these cover the seam: a member who just registered is anonymous
# and must still be able to pay.
#
# The registration email is addressed from whatever Net ID was typed into the payment
# form, so an unknown Net ID gets a confirmation step before anything is sent - a typo
# must not mail a stranger.
class PaymentRegistrationTestCase(TestCase):
    """
    Base for the payment-page registration tests.

    Saving a `UserProfile` fires the member-role signal, which needs a current `Term`
    to resolve membership and would otherwise call out to the bot API. Give it a real
    Term - on its own product, so the product under test stays an ordinary one - and
    stub the outbound call. `UserStub.notify` reads the organization name off
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
        patcher = patch("core.signals.handlers.add_member_role", new=AsyncMock(return_value=True))
        patcher.start()
        self.addCleanup(patcher.stop)

        ServerSettings.objects.get_or_create(defaults={"organization_name": "Comet Robotics"})

        self.product = Product.objects.create(name="Dues", amount_cents=2000, max_purchases_per_user=-1)
        self.pay_url = reverse("choose_user", args=[self.product.id])

    def pay_as(self, net_id, *, ip=None, **extra):
        # `ip` becomes the X-Real-IP nginx sets in production, which is what the
        # registration throttle buckets on. Left off, the request looks like local dev.
        headers = {"HTTP_X_REAL_IP": ip} if ip else {}
        return self.client.post(self.pay_url, {"username": net_id, "payment_method": "cash", **extra}, **headers)

    def confirm_registration_for(self, net_id, *, ip=None):
        return self.pay_as(net_id, ip=ip, confirm_registration="1")


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
            {"first_name": "Ada", "last_name": "Lovelace", "major": "CS"},
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


@override_settings(
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
    REGISTRATION_EMAIL_RATE_PER_IP="2/h",
    REGISTRATION_EMAIL_RATE_GLOBAL="150/d",
)
class PaymentRegistrationThrottleTests(PaymentRegistrationTestCase):
    """
    Confirming an unknown Net ID here mails it, so that one branch is metered.

    The rest of the page must stay untouched: it is what officers use to take cash from
    a queue of members at a recruiting table, all from the same laptop and therefore the
    same address as far as the throttle can tell.
    """

    ip = "198.51.100.1"
    over_limit_message = "We've had a lot of registration requests recently."

    def setUp(self):
        super().setUp()
        cache.clear()

    def exhaust_per_ip_allowance(self):
        for index in (1, 2):
            self.confirm_registration_for(f"abc00000{index}", ip=self.ip)

    def test_confirmations_up_to_the_per_ip_limit_all_send(self):
        self.exhaust_per_ip_allowance()

        self.assertEqual(UserStub.objects.count(), 2)
        self.assertEqual(len(mail.outbox), 2)

    def test_the_confirmation_over_the_per_ip_limit_registers_nobody(self):
        self.exhaust_per_ip_allowance()
        mail.outbox.clear()

        response = self.confirm_registration_for("abc000003", ip=self.ip)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, escape(self.over_limit_message))
        self.assertFalse(UserStub.objects.filter(net_id="abc000003").exists())
        self.assertEqual(mail.outbox, [])

    @override_settings(REGISTRATION_EMAIL_RATE_GLOBAL="2/d")
    def test_the_global_cap_trips_across_different_client_ips(self):
        self.confirm_registration_for("abc000001", ip="198.51.100.1")
        self.confirm_registration_for("abc000002", ip="198.51.100.2")
        mail.outbox.clear()

        response = self.confirm_registration_for("abc000003", ip="198.51.100.3")

        self.assertContains(response, escape(self.over_limit_message))
        self.assertEqual(UserStub.objects.count(), 2)
        self.assertEqual(mail.outbox, [])

    def test_cash_payments_for_known_members_are_never_throttled(self):
        """
        An officer at the check-in table takes payment after payment from one device.

        The throttle lives on the registration branch alone, so the limit being spent -
        by this device or by everyone sharing its NATed address - must not stop a member
        who already has an account from paying.
        """
        self.exhaust_per_ip_allowance()
        self.confirm_registration_for("abc000003", ip=self.ip)

        for net_id in ("xyz000001", "xyz000002", "xyz000003"):
            with self.subTest(net_id=net_id):
                user = User.objects.create(username=net_id)

                response = self.pay_as(net_id, ip=self.ip)

                payment = Payment.objects.get(user=user)
                self.assertRedirects(
                    response, reverse("payment_success", args=[payment.id]), fetch_redirect_response=False
                )

    def test_the_confirmation_prompt_itself_is_not_metered(self):
        """Asking "is that your Net ID?" sends nothing, so it should cost nothing."""
        for index in (1, 2, 3, 4):
            response = self.pay_as(f"abc00000{index}", ip=self.ip)
            self.assertContains(response, "Is that your Net ID?")

        self.assertEqual(mail.outbox, [])
        self.assertContains(self.confirm_registration_for("abc000001", ip=self.ip), "Check your UT Dallas email")

    def test_the_allowance_is_shared_with_the_accounts_registration_page(self):
        """Both pages send the same email, so they draw on one bucket."""
        self.exhaust_per_ip_allowance()

        response = self.client.post(reverse("registration_request"), {"net_id": "abc000003"}, HTTP_X_REAL_IP=self.ip)

        self.assertContains(response, "a lot of registration requests")
        self.assertFalse(UserStub.objects.filter(net_id="abc000003").exists())
