from django.conf import settings
from django.test import TestCase, Client, override_settings
from django.contrib.auth.models import User
from django.utils import timezone

from events.models import Attendance, Event, SignInMethod
from events.views import LOOKUP_USER_LIMIT
from payments.models import Payment, Product, PurchasedProduct, Term


class LookupUserViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.staff_user = User.objects.create_user(username="staff", password="pass", is_staff=True)
        self.event = Event.objects.create(
            event_name="Test Event",
            event_date=timezone.now(),
        )
        # Create enough users to exceed the limit
        for i in range(LOOKUP_USER_LIMIT + 5):
            User.objects.create_user(
                username=f"alice{i}",
                first_name="Alice",
                last_name=f"Smith{i}",
            )
        self.client.login(username="staff", password="pass")

    def test_get_returns_no_users_by_default(self):
        response = self.client.get(f"/events/{self.event.pk}/lookup-user/")
        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(response.context["users"], [])

    def test_post_with_query_returns_matching_users(self):
        response = self.client.post(
            f"/events/{self.event.pk}/lookup-user/",
            {"search": "Alice"},
        )
        self.assertEqual(response.status_code, 200)
        users = response.context["users"]
        self.assertGreater(len(users), 0)
        for user in users:
            self.assertIn("Alice", user.first_name)

    def test_post_with_query_limits_results(self):
        response = self.client.post(
            f"/events/{self.event.pk}/lookup-user/",
            {"search": "Alice"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(response.context["users"]), LOOKUP_USER_LIMIT)

    def test_post_with_empty_query_limits_results(self):
        response = self.client.post(
            f"/events/{self.event.pk}/lookup-user/",
            {"search": ""},
        )
        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(response.context["users"]), LOOKUP_USER_LIMIT)

    def test_post_no_match_returns_no_users(self):
        response = self.client.post(
            f"/events/{self.event.pk}/lookup-user/",
            {"search": "zzznomatch"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(response.context["users"], [])


@override_settings(FEATURE_FLAGS={**settings.FEATURE_FLAGS, "SELF_CHECK_IN": True})
class SelfSignInViewTest(TestCase):
    """The member-facing self sign-in flow at /events/<id>/self-sign-in/."""

    def setUp(self):
        self.client = Client()
        self.event = Event.objects.create(event_name="Test Event", event_date=timezone.now())
        self.product = Product.objects.create(
            name="Fall Dues", description="Fall membership dues", amount_cents=1000, max_purchases_per_user=-1
        )
        self.term = Term.objects.create(
            name="Fall 2026",
            start_date=timezone.now().date() - timezone.timedelta(days=30),
            end_date=timezone.now().date() + timezone.timedelta(days=30),
            product=self.product,
        )

    def _make_member(self, username="abc123456", discord_id="12345"):
        user = User.objects.create_user(username=username, first_name="Alice", last_name="Smith")
        payment = Payment.objects.create(user=user, amount_cents=1000, completed_at=timezone.now())
        PurchasedProduct.objects.create(payment=payment, product=self.product)
        if discord_id:
            profile = user.userprofile
            profile.discord_id = discord_id
            profile.save()
        return user

    def _post(self, username):
        return self.client.post(f"/events/{self.event.pk}/self-sign-in/", {"username": username})

    def test_get_renders_form_without_authentication(self):
        response = self.client.get(f"/events/{self.event.pk}/self-sign-in/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)
        self.assertIsNone(response.context.get("message"))

    def test_member_signs_in_and_is_recorded_as_self_qr(self):
        user = self._make_member()

        response = self._post("abc123456")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["message"], "success")
        self.assertEqual(response.context["user"], user)
        self.assertFalse(response.context.get("not_linked"))
        attendance = Attendance.objects.get(event=self.event, user=user)
        self.assertEqual(attendance.sign_in_method, SignInMethod.SELF_QR)

    def test_net_id_is_matched_case_insensitively(self):
        user = self._make_member()

        response = self._post("ABC123456")

        self.assertEqual(response.context["message"], "success")
        self.assertTrue(Attendance.objects.filter(event=self.event, user=user).exists())

    def test_unknown_net_id_offers_next_step_and_records_nothing(self):
        response = self._post("zzz999999")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["message"], "not_found")
        self.assertTrue(response.context["next_step_url"])
        self.assertFalse(Attendance.objects.exists())

    def test_signing_in_twice_reports_repeat(self):
        self._make_member()

        self._post("abc123456")
        response = self._post("abc123456")

        self.assertEqual(response.context["message"], "repeat")
        self.assertEqual(Attendance.objects.count(), 1)

    def test_non_member_is_shown_a_dues_link(self):
        user = User.objects.create_user(username="nop123456", first_name="No", last_name="Pay")

        response = self._post("nop123456")

        self.assertEqual(response.context["message"], "not_member")
        self.assertEqual(response.context["next_step_url"], f"/payments/{self.product.pk}/pay/")
        # Attendance is still recorded; only the warning differs.
        self.assertTrue(Attendance.objects.filter(event=self.event, user=user).exists())

    def test_unlinked_member_is_told_how_to_link_discord(self):
        self._make_member(discord_id=None)

        response = self._post("abc123456")

        self.assertEqual(response.context["message"], "success")
        self.assertTrue(response.context["not_linked"])
        self.assertContains(response, "/link abc123456")

    def test_malformed_net_id_is_rejected(self):
        response = self._post("not-a-net-id")

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context.get("message"))
        self.assertTrue(response.context["form"].errors)
        self.assertFalse(Attendance.objects.exists())


class SelfCheckInFeatureFlagTest(TestCase):
    """Self sign-in ships default-off behind the SELF_CHECK_IN flag."""

    def setUp(self):
        self.event = Event.objects.create(event_name="Test Event", event_date=timezone.now())

    def test_flag_defaults_off(self):
        self.assertIn("SELF_CHECK_IN", settings.FEATURE_FLAGS)
        self.assertFalse(settings.FEATURE_FLAGS["SELF_CHECK_IN"])

    @override_settings(FEATURE_FLAGS={**settings.FEATURE_FLAGS, "SELF_CHECK_IN": False})
    def test_disabled_flag_hides_the_page(self):
        response = self.client.get(f"/events/{self.event.pk}/self-sign-in/")
        self.assertEqual(response.status_code, 404)

    @override_settings(FEATURE_FLAGS={**settings.FEATURE_FLAGS, "SELF_CHECK_IN": False})
    def test_disabled_flag_creates_no_attendance(self):
        self.client.post(f"/events/{self.event.pk}/self-sign-in/", {"username": "abc123456"})
        self.assertFalse(Attendance.objects.exists())
