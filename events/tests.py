from datetime import timedelta
import re

from django.conf import settings
from django.test import TestCase, Client, TransactionTestCase, override_settings
from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse

from events.views import LOOKUP_USER_LIMIT
from payments.models import Payment, Product, PurchasedProduct, Term


def make_term(name, start_date, end_date):
    product = Product.objects.create(
        name=f"{name} dues",
        amount_cents=1000,
        max_purchases_per_user=1,
    )
    return Term.objects.create(name=name, start_date=start_date, end_date=end_date, product=product)


from events.models import Attendance, Event, SignInMethod
from events.views import LOOKUP_USER_LIMIT, qr_code_svg
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
        response = self.client.get(reverse("lookup-user", kwargs={"event_id": self.event.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(response.context["users"], [])

    def test_post_with_query_returns_matching_users(self):
        response = self.client.post(
            reverse("lookup-user", kwargs={"event_id": self.event.pk}),
            {"search": "Alice"},
        )
        self.assertEqual(response.status_code, 200)
        users = response.context["users"]
        self.assertGreater(len(users), 0)
        for user in users:
            self.assertIn("Alice", user.first_name)

    def test_post_with_query_limits_results(self):
        response = self.client.post(
            reverse("lookup-user", kwargs={"event_id": self.event.pk}),
            {"search": "Alice"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(response.context["users"]), LOOKUP_USER_LIMIT)

    def test_post_with_empty_query_limits_results(self):
        response = self.client.post(
            reverse("lookup-user", kwargs={"event_id": self.event.pk}),
            {"search": ""},
        )
        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(response.context["users"]), LOOKUP_USER_LIMIT)

    def test_post_no_match_returns_no_users(self):
        response = self.client.post(
            reverse("lookup-user", kwargs={"event_id": self.event.pk}),
            {"search": "zzznomatch"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(response.context["users"], [])

    def test_lookup_user_requires_staff(self):
        self.client.logout()
        response = self.client.post(
            reverse("lookup-user", kwargs={"event_id": self.event.pk}),
            {"search": ""},
        )
        self.assertEqual(response.status_code, 302)


@override_settings(FEATURE_FLAGS={**settings.FEATURE_FLAGS, "UNIFIED_EVENT_CHECK_IN": False})
class SignInMembershipRenewalTest(TestCase):
    """Check-in messaging during a term overlap, where two terms are active at once."""

    def setUp(self):
        self.client = Client()
        self.staff_user = User.objects.create_user(username="staff", password="pass", is_staff=True)
        self.client.login(username="staff", password="pass")
        self.event = Event.objects.create(event_name="Test Event", event_date=timezone.now())
        today = timezone.localdate()

        self.spring_term = make_term("Spring", today - timedelta(days=90), today + timedelta(days=14))
        self.fall_term = make_term("Fall", today - timedelta(days=1), today + timedelta(days=120))

    def create_member_for_term(self, username, card_number, term):
        user = User.objects.create_user(username=username, password="pass")
        user.userprofile.comet_card_serial_number = card_number
        user.userprofile.save()
        payment = Payment.objects.create(
            user=user,
            amount_cents=1000,
            verified_by=self.staff_user,
            metadata={},
        )
        PurchasedProduct.objects.create(product=term.product, payment=payment)
        return user

    def sign_in(self, card_number):
        return self.client.post(
            reverse("sign_in", kwargs={"event_id": self.event.pk}),
            {"card_data": f";{card_number}=0000000000000000"},
        )

    def test_spring_only_member_is_prompted_to_renew_for_fall(self):
        self.create_member_for_term("spring_member", "1234567890123456", self.spring_term)

        response = self.sign_in("1234567890123456")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["message"], "renewal")
        self.assertEqual(response.context["renewal_term"], self.fall_term)
        self.assertContains(response, "Membership Renewal Needed")

    def test_fall_member_signs_in_without_renewal_warning(self):
        self.create_member_for_term("fall_member", "6543210987654321", self.fall_term)

        response = self.sign_in("6543210987654321")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["message"], "success")
        self.assertNotContains(response, "Membership Renewal Needed")

    def test_non_member_gets_non_member_message_not_renewal_warning(self):
        """The renewal prompt must never outrank the 'not a member' message."""
        User.objects.create_user(username="non_member", password="pass")
        user_profile = User.objects.get(username="non_member").userprofile
        user_profile.comet_card_serial_number = "1111222233334444"
        user_profile.save()

        response = self.sign_in("1111222233334444")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["message"], "nomember")
        self.assertNotContains(response, "Membership Renewal Needed")

    def test_member_of_both_terms_sees_no_renewal_warning(self):
        """Paying the renewing term already covers both, so no prompt should appear."""
        user = self.create_member_for_term("both_terms", "5555666677778888", self.spring_term)
        payment = Payment.objects.create(
            user=user,
            amount_cents=1000,
            verified_by=self.staff_user,
            metadata={},
        )
        PurchasedProduct.objects.create(product=self.fall_term.product, payment=payment)

        response = self.sign_in("5555666677778888")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["message"], "success")
        self.assertNotContains(response, "Membership Renewal Needed")

    def test_repeat_sign_in_still_shows_renewal_warning(self):
        """A member who already checked in still needs the renewal nudge."""
        self.create_member_for_term("spring_member", "1234567890123456", self.spring_term)
        self.sign_in("1234567890123456")

        response = self.sign_in("1234567890123456")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["message"], "renewal")
        self.assertEqual(Attendance.objects.filter(event=self.event).count(), 1)

    def test_repeat_sign_in_for_non_member_shows_non_member(self):
        User.objects.create_user(username="non_member", password="pass")
        user_profile = User.objects.get(username="non_member").userprofile
        user_profile.comet_card_serial_number = "1111222233334444"
        user_profile.save()
        self.sign_in("1111222233334444")

        response = self.sign_in("1111222233334444")

        self.assertEqual(response.context["message"], "nomember")

    def test_no_active_terms_does_not_warn_about_renewal(self):
        """With no active term there is nothing to renew toward, so only membership status shows."""
        Term.objects.all().delete()
        self.create_member_for_term("former_member", "9999888877776666", self.spring_term)

        response = self.sign_in("9999888877776666")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["message"], "nomember")
        self.assertIsNone(response.context["renewal_term"])
        self.assertNotContains(response, "Membership Renewal Needed")


class SignInMethodMigrationTest(TransactionTestCase):
    def test_existing_checkin_method_survives_rename(self):
        from django.db import connection
        from django.db.migrations.executor import MigrationExecutor

        executor = MigrationExecutor(connection)
        executor.migrate([("events", "0027_add_checkin_method_to_attendance")])
        old_apps = executor.loader.project_state([("events", "0027_add_checkin_method_to_attendance")]).apps
        Event = old_apps.get_model("events", "Event")
        Attendance = old_apps.get_model("events", "Attendance")
        event = Event.objects.create(event_name="Migration test", event_date=timezone.now())
        attendance = Attendance.objects.create(event=event, checkin_method="self_qr")
        try:
            executor = MigrationExecutor(connection)
            executor.migrate([("events", "0029_alter_attendance_sign_in_method")])
            new_apps = executor.loader.project_state([("events", "0029_alter_attendance_sign_in_method")]).apps
            self.assertEqual(
                new_apps.get_model("events", "Attendance").objects.get(pk=attendance.pk).sign_in_method, "self_qr"
            )
        finally:
            MigrationExecutor(connection).migrate(MigrationExecutor(connection).loader.graph.leaf_nodes())


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
            start_date=timezone.now().date() - timedelta(days=30),
            end_date=timezone.now().date() + timedelta(days=30),
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
        self.assertTrue(response.context["form"].fields["username"].widget.attrs.get("autofocus"))

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

    @override_settings(
        FEATURE_FLAGS={**settings.FEATURE_FLAGS, "SELF_CHECK_IN": True, "WEB_ACCOUNT_REGISTRATION": False}
    )
    def test_unknown_net_id_offers_next_step_and_records_nothing(self):
        response = self._post("zzz999999")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["message"], "not_found")
        self.assertNotIn("next_step_url", response.context)
        self.assertFalse(Attendance.objects.exists())

    def test_session_prefills_net_id(self):
        user = self._make_member()
        self.client.force_login(user)
        response = self.client.get(reverse("self_sign_in", args=[self.event.pk]))
        self.assertEqual(response.context["form"].initial["username"], user.username)

    @override_settings(
        FEATURE_FLAGS={**settings.FEATURE_FLAGS, "SELF_CHECK_IN": True, "WEB_ACCOUNT_REGISTRATION": True}
    )
    def test_unknown_net_id_requires_confirmation_before_registration(self):
        from unittest.mock import patch

        with patch("payments.views.UserStub.create") as create:
            response = self._post("zzz999999")
            self.assertEqual(response.context["confirm_net_id"], "zzz999999")
            create.assert_not_called()

    @override_settings(
        FEATURE_FLAGS={**settings.FEATURE_FLAGS, "SELF_CHECK_IN": True, "WEB_ACCOUNT_REGISTRATION": True}
    )
    def test_confirmed_registration_returns_to_event(self):
        from unittest.mock import patch

        with (
            patch("payments.views.UserStub.create") as create,
            patch("payments.views.UserStub.notify"),
            patch("payments.views.registration_throttled", return_value=False),
        ):
            response = self.client.post(
                reverse("self_sign_in", args=[self.event.pk]),
                {"username": "zzz999999", "confirm_registration": "1"},
            )
        self.assertIn("registration_message", response.context)
        self.assertEqual(
            create.call_args.kwargs["after_registration_redirect_destination"],
            reverse("self_sign_in", args=[self.event.pk]),
        )

    def test_repeat_non_member_still_sees_dues_and_linking_prompt(self):
        User.objects.create_user(username="nop123456")
        self._post("nop123456")
        response = self._post("nop123456")
        self.assertTrue(response.context["not_linked"])
        self.assertEqual(response.context["next_step_url"], f"/payments/{self.product.pk}/pay/")

    def test_signing_in_twice_reports_repeat(self):
        self._make_member()

        self._post("abc123456")
        response = self._post("abc123456")

        self.assertEqual(response.context["message"], "repeat")
        self.assertNotIn("autofocus", response.context["form"].fields["username"].widget.attrs)
        self.assertEqual(Attendance.objects.count(), 1)

    def test_non_member_is_shown_a_dues_link(self):
        user = User.objects.create_user(username="nop123456", first_name="No", last_name="Pay")

        response = self._post("nop123456")

        self.assertEqual(response.context["message"], "not_member")
        self.assertNotIn("autofocus", response.context["form"].fields["username"].widget.attrs)
        self.assertEqual(response.context["next_step_url"], f"/payments/{self.product.pk}/pay/")
        # Attendance is still recorded; only the warning differs.
        self.assertTrue(Attendance.objects.filter(event=self.event, user=user).exists())

    def test_dues_link_targets_longest_active_term_during_overlap(self):
        User.objects.create_user(username="nop123456")
        later_term = make_term(
            "Later", timezone.localdate() - timedelta(days=1), timezone.localdate() + timedelta(days=90)
        )
        response = self._post("nop123456")
        self.assertEqual(response.context["next_step_url"], reverse("choose_user", args=[later_term.product_id]))

    def test_unlinked_member_is_told_how_to_link_discord(self):
        from core.models import ServerSettings

        self._make_member(discord_id=None)
        ServerSettings.objects.create(organization_name="Comet Robotics")

        response = self._post("abc123456")

        self.assertEqual(response.context["message"], "success")
        self.assertNotIn("autofocus", response.context["form"].fields["username"].widget.attrs)
        self.assertTrue(response.context["not_linked"])
        self.assertContains(response, "/link abc123456")
        self.assertContains(response, 'data-copy-command="/link net_id:abc123456"')
        self.assertContains(response, "in the Comet Robotics Discord server")
        self.assertContains(response, 'aria-label="Copy Discord link command"')

    def test_unlinked_member_sees_generic_server_when_organization_is_unset(self):
        self._make_member(discord_id=None)

        response = self._post("abc123456")

        self.assertContains(response, "in the organization's Discord server", html=False)

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


class ConcurrentSelfSignInTest(TransactionTestCase):
    def test_concurrent_sign_ins_record_one_attendance(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier, BrokenBarrierError
        from unittest.mock import patch

        from django.db import close_old_connections
        from django.db.models.query import QuerySet

        user = User.objects.create_user(username="abc123456")
        event = Event.objects.create(event_name="Concurrent sign-in", event_date=timezone.now())
        start = Barrier(2)
        both_missed = Barrier(2)
        original_get = QuerySet.get

        def synchronized_get(queryset, *args, **kwargs):
            try:
                return original_get(queryset, *args, **kwargs)
            except Attendance.DoesNotExist:
                if queryset.model is Attendance:
                    try:
                        both_missed.wait(timeout=1)
                    except BrokenBarrierError:
                        pass
                raise

        def sign_in():
            close_old_connections()
            try:
                start.wait(timeout=5)
                user.userprofile.sign_in_to_event(event, SignInMethod.SELF_QR)
            finally:
                close_old_connections()

        with patch.object(QuerySet, "get", synchronized_get), ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(lambda _: sign_in(), range(2)))
        self.assertEqual(Attendance.objects.filter(event=event, user=user).count(), 1)


class AttendanceDeduplicationMigrationTest(TransactionTestCase):
    def test_backup_deduplicate_and_enforce_unique_attendance(self):
        from django.db import IntegrityError, connection, transaction
        from django.db.migrations.executor import MigrationExecutor

        executor = MigrationExecutor(connection)
        executor.migrate([("events", "0029_alter_attendance_sign_in_method")])
        old_apps = executor.loader.project_state([("events", "0029_alter_attendance_sign_in_method")]).apps
        Event = old_apps.get_model("events", "Event")
        Attendance = old_apps.get_model("events", "Attendance")
        User = old_apps.get_model("auth", "User")
        user = User.objects.create(username="dedup-test")
        event = Event.objects.create(event_name="Deduplication test", event_date=timezone.now())
        older = Attendance.objects.create(
            event=event, user=user, timestamp=timezone.now() - timedelta(days=1), sign_in_method="self_qr"
        )
        newer = Attendance.objects.create(
            event=event, user=user, timestamp=timezone.now(), sign_in_method="staff_initiated"
        )
        anonymous = Attendance.objects.create(event=event, user=None)
        existing_tables = set(connection.introspection.table_names())
        try:
            executor = MigrationExecutor(connection)
            executor.migrate([("events", "0030_unique_attendance")])
            new_apps = executor.loader.project_state([("events", "0030_unique_attendance")]).apps
            NewAttendance = new_apps.get_model("events", "Attendance")
            self.assertTrue(NewAttendance.objects.filter(pk=older.pk, sign_in_method="self_qr").exists())
            self.assertFalse(NewAttendance.objects.filter(pk=newer.pk).exists())
            self.assertTrue(NewAttendance.objects.filter(pk=anonymous.pk).exists())
            backups = [
                name
                for name in set(connection.introspection.table_names()) - existing_tables
                if name.startswith("events_attendance_backup_")
            ]
            self.assertEqual(len(backups), 1)
            with connection.cursor() as cursor:
                cursor.execute(
                    f"SELECT id, sign_in_method FROM {connection.ops.quote_name(backups[0])} WHERE event_id = %s",
                    [event.pk],
                )
                self.assertEqual(
                    dict(cursor.fetchall()),
                    {older.pk: "self_qr", newer.pk: "staff_initiated", anonymous.pk: "staff_initiated"},
                )
            with self.assertRaises(IntegrityError), transaction.atomic():
                NewAttendance.objects.create(event_id=event.pk, user_id=user.pk)
            NewAttendance.objects.create(event_id=event.pk, user_id=None)
        finally:
            MigrationExecutor(connection).migrate(MigrationExecutor(connection).loader.graph.leaf_nodes())


@override_settings(FEATURE_FLAGS={**settings.FEATURE_FLAGS, "SELF_CHECK_IN": True})
class SelfSignInQrViewTest(TestCase):
    """The staff-facing page pairing the self sign-in link with its QR code."""

    def setUp(self):
        self.event = Event.objects.create(event_name="Test Event", event_date=timezone.now())

    def test_requires_staff(self):
        response = self.client.get(f"/events/{self.event.pk}/self-sign-in-qr/")
        self.assertEqual(response.status_code, 302)

    def test_staff_sees_link_and_qr(self):
        staff = User.objects.create_user(username="staff", password="pass", is_staff=True)
        self.client.login(username="staff", password="pass")

        with self.settings(PUBLIC_URL="https://clubmanager.example"):
            response = self.client.get(f"/events/{self.event.pk}/self-sign-in-qr/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["sign_in_url"],
            f"https://clubmanager.example/events/{self.event.pk}/self-sign-in/",
        )
        self.assertIn("<svg", response.context["qr_svg"])

    def test_qr_page_embeds_the_link_in_the_page(self):
        staff = User.objects.create_user(username="staff", password="pass", is_staff=True)
        self.client.login(username="staff", password="pass")

        with self.settings(PUBLIC_URL="https://clubmanager.example"):
            response = self.client.get(f"/events/{self.event.pk}/self-sign-in-qr/")

        self.assertContains(response, "https://clubmanager.example/events/")
        self.assertContains(response, "<svg")

    def test_link_on_event_card_points_at_the_qr_page(self):
        response = self.client.get(f"/events/{self.event.pk}/overview")
        self.assertContains(response, f"/events/{self.event.pk}/self-sign-in-qr/")

    @override_settings(FEATURE_FLAGS={**settings.FEATURE_FLAGS, "SELF_CHECK_IN": False})
    def test_disabled_flag_hides_the_qr_page(self):
        staff = User.objects.create_user(username="staff", password="pass", is_staff=True)
        self.client.login(username="staff", password="pass")

        response = self.client.get(f"/events/{self.event.pk}/self-sign-in-qr/")
        self.assertEqual(response.status_code, 404)

    @override_settings(FEATURE_FLAGS={**settings.FEATURE_FLAGS, "SELF_CHECK_IN": False})
    def test_disabled_flag_hides_the_event_card_button(self):
        response = self.client.get(f"/events/{self.event.pk}/overview")
        self.assertNotContains(response, "Self Sign-In QR")


class QrCodeSvgTest(TestCase):
    """
    The inline QR SVG is scaled by CSS, so a wrong viewBox silently crops the code
    and stops it scanning while still looking like a QR code on screen.
    """

    URL = "https://clubmanager.example/events/1/self-sign-in/"

    def test_viewbox_covers_the_whole_drawing_area(self):
        svg = qr_code_svg(self.URL)
        width_match = re.search(r'<svg[^>]*\bwidth="(\d+)"', svg)
        assert width_match is not None
        width = int(width_match.group(1))
        viewbox = re.search(r'viewBox="0 0 (\d+) (\d+)"', svg)

        assert viewbox is not None
        # segno draws the symbol plus a quiet zone, so the viewBox must be at
        # least as large as the reported extent -- using the matrix size instead
        # crops the code.
        self.assertEqual(viewbox.groups(), (str(width), str(width)))

    def test_viewbox_is_larger_than_the_symbol_matrix(self):
        import segno

        svg = qr_code_svg(self.URL)
        match = re.search(r'viewBox="0 0 (\d+)', svg)
        assert match is not None
        viewbox = int(match.group(1))

        self.assertGreater(viewbox, len(segno.make(self.URL).matrix))

    def test_svg_scales_without_distortion(self):
        self.assertIn('preserveAspectRatio="xMidYMid meet"', qr_code_svg(self.URL))
