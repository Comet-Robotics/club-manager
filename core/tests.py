from django.contrib import admin
from django.contrib.auth.models import User
from django.core import mail
from django.core.mail.backends.base import BaseEmailBackend
from django.test import TestCase, override_settings
from django.urls import reverse
from post_office.connections import connections as email_connections
from post_office.models import STATUS, Email, EmailTemplate, Log

from core.emails import EmailDeliveryError, send_templated_email

TEMPLATE = "email/messages/discord_account_link.html"
CONTEXT = {
    "first_name": "Ada",
    "account_details": {"Net ID": "axl000000"},
    "link_url": "https://clubmanager.example/accounts/link/1234",
}


POST_OFFICE_CONFIG = {
    "BACKENDS": {"default": "django.core.mail.backends.locmem.EmailBackend"},
    "DEFAULT_PRIORITY": "now",
    "LOG_LEVEL": 2,
    "MESSAGE_ID_ENABLED": True,
    "MESSAGE_ID_FQDN": "clubmanager.example",
}


@override_settings(
    PUBLIC_URL="https://clubmanager.example",
    EMAIL_BACKEND="post_office.EmailBackend",
    POST_OFFICE=POST_OFFICE_CONFIG,
)
class SendTemplatedEmailTest(TestCase):
    """
    Covers what routing mail through django-post_office is supposed to buy us: a stored copy of
    every message, a log row per delivery attempt, and a Message-ID in the database that matches
    the one that went out.
    """

    post_office_config = POST_OFFICE_CONFIG

    def setUp(self):
        # post_office caches one delivery connection per backend alias in a thread-local that
        # outlives a test, so a test that swaps the backend under POST_OFFICE["BACKENDS"] would
        # otherwise keep delivering through whichever backend was resolved first.
        email_connections.close()

    def test_sent_message_is_stored_with_a_log_and_a_message_id(self):
        send_templated_email(TEMPLATE, CONTEXT, ["ada@utdallas.edu"])

        stored = Email.objects.get()
        self.assertEqual(stored.to, ["ada@utdallas.edu"])
        self.assertEqual(stored.status, STATUS.sent)
        self.assertTrue(stored.html_message)
        self.assertTrue(stored.message)

        # A success has to be logged too, not just a failure - LOG_LEVEL 2.
        log = Log.objects.get(email=stored)
        self.assertEqual(log.status, STATUS.sent)

        self.assertTrue(stored.message_id.endswith("@clubmanager.example>"), stored.message_id)

        # The stored ID is the one the recipient sees, rather than something the SMTP library
        # invented at send time.
        self.assertEqual(mail.outbox[0].extra_headers["Message-ID"], stored.message_id)

    def test_transactional_headers_survive_the_round_trip(self):
        send_templated_email(TEMPLATE, CONTEXT, ["ada@utdallas.edu"])

        headers = mail.outbox[0].extra_headers
        self.assertEqual(headers["Auto-Submitted"], "auto-generated")
        self.assertEqual(headers["X-Auto-Response-Suppress"], "OOF, AutoReply")

    def test_failed_delivery_raises_but_is_still_recorded(self):
        # post_office catches the delivery exception in order to record it, so check that
        # send_templated_email turns that back into something a caller cannot miss, and that the
        # failed message is still readable in the admin afterwards.
        failing_config = {
            **self.post_office_config,
            "BACKENDS": {"default": "core.tests.RefusingEmailBackend"},
        }

        with self.settings(POST_OFFICE=failing_config):
            with self.assertLogs("post_office", level="ERROR"):
                with self.assertRaises(EmailDeliveryError):
                    send_templated_email(TEMPLATE, CONTEXT, ["ada@utdallas.edu"])

        stored = Email.objects.get()
        self.assertEqual(stored.status, STATUS.failed)
        self.assertTrue(stored.html_message)
        self.assertEqual(Log.objects.get(email=stored).status, STATUS.failed)


class RefusingEmailBackend(BaseEmailBackend):
    """Stands in for an SMTP server that won't take the message."""

    def send_messages(self, email_messages):
        raise OSError("SMTP server is having a day")


@override_settings(
    PUBLIC_URL="https://clubmanager.example",
    EMAIL_BACKEND="post_office.EmailBackend",
    POST_OFFICE=POST_OFFICE_CONFIG,
)
class PostOfficeAdminTest(TestCase):
    """
    The point of keeping every message is that an officer can go read one, so smoke test the
    admin pages that make that possible. The Email detail page in particular re-parses the stored
    message into MIME parts and runs the HTML body through a sanitizer, which is the kind of
    thing that breaks quietly on a version bump.
    """

    def setUp(self):
        email_connections.close()
        self.client.force_login(User.objects.create_superuser("officer", "officer@example.com", "pw"))

    def test_email_template_admin_is_hidden(self):
        # Nothing reads post_office's database-stored templates - see clubManager/admin.py.
        self.assertNotIn(EmailTemplate, admin.site._registry)
        self.assertIn(Email, admin.site._registry)
        self.assertIn(Log, admin.site._registry)

    def test_a_sent_message_can_be_read_in_the_admin(self):
        send_templated_email(TEMPLATE, CONTEXT, ["ada@utdallas.edu"])
        stored = Email.objects.get()

        for url in [
            reverse("admin:post_office_email_changelist"),
            reverse("admin:post_office_log_changelist"),
            reverse("admin:post_office_attachment_changelist"),
        ]:
            self.assertEqual(self.client.get(url).status_code, 200, url)

        detail = self.client.get(reverse("admin:post_office_email_change", args=[stored.pk]))
        self.assertEqual(detail.status_code, 200)
        self.assertContains(detail, stored.message_id.strip("<>"))
        self.assertContains(detail, "HTML Body")


class NormalizeUsernameTest(TestCase):
    def test_none_stays_none(self):
        from common.utils import normalize_username

        self.assertIsNone(normalize_username(None))

    def test_strips_and_lowercases(self):
        from common.utils import normalize_username

        self.assertEqual(normalize_username("  ABC000001 "), "abc000001")
        self.assertEqual(normalize_username("abc000001"), "abc000001")
        self.assertEqual(normalize_username(""), "")


class UsernameNormalizationHelpersTest(TestCase):
    def _drop_canonical_index(self):
        # The test database has migration 0030's functional unique index applied, which
        # makes a colliding state unrepresentable -- the fixture UPDATE itself would
        # 500. These tests exercise the pre-migration guard, so drop the index first.
        # DDL is transactional in Postgres, so TestCase rollback restores it.
        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute("DROP INDEX IF EXISTS auth_user_username_lower_uniq")

    def test_pre_save_signal_canonicalizes_orm_writes(self):
        user = User.objects.create_user("  QRS000010 ", password="pw")
        user.refresh_from_db()
        self.assertEqual(user.username, "qrs000010")

    def test_find_case_collisions_detects_case_and_whitespace_variants(self):
        from common.username_normalization import find_case_collisions

        self._drop_canonical_index()

        keeper = User.objects.create_user("aaa000001", password="pw")
        other = User.objects.create_user("zzz999999", password="pw")
        User.objects.filter(pk=other.pk).update(username="AAA000001")

        collisions = find_case_collisions(User)
        self.assertIn("aaa000001", collisions)
        self.assertEqual(len(collisions), 1)
        keeper.refresh_from_db()
        self.assertEqual(keeper.username, "aaa000001")

    def test_find_case_collisions_detects_whitespace_variant(self):
        from common.username_normalization import find_case_collisions

        self._drop_canonical_index()
        User.objects.create_user("bbb000002", password="pw")
        padded = User.objects.create_user("zzz999998", password="pw")
        User.objects.filter(pk=padded.pk).update(username="  BBB000002 ")

        self.assertIn("bbb000002", find_case_collisions(User))

    def test_lowercase_usernames_rewrites_case_and_whitespace(self):
        from common.username_normalization import find_case_collisions, lowercase_usernames

        upper = User.objects.create_user("ccc000003", password="pw")
        User.objects.filter(pk=upper.pk).update(username="CCC000003")
        padded = User.objects.create_user("ddd000004", password="pw")
        User.objects.filter(pk=padded.pk).update(username="  DDD000004 ")

        lowercase_usernames(User)

        upper.refresh_from_db()
        padded.refresh_from_db()
        self.assertEqual(upper.username, "ccc000003")
        self.assertEqual(padded.username, "ddd000004")
        self.assertEqual(find_case_collisions(User), [])


class CaseInsensitiveBackendTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("ghi000005", password="correct-pw")

    def test_exact_login_still_works(self):
        from django.contrib.auth import authenticate

        self.assertIsNotNone(authenticate(username="ghi000005", password="correct-pw"))

    def test_uppercase_and_padded_login_work(self):
        from django.contrib.auth import authenticate

        self.assertIsNotNone(authenticate(username="GHI000005", password="correct-pw"))
        self.assertIsNotNone(authenticate(username="  ghi000005  ", password="correct-pw"))

    def test_wrong_password_unknown_and_inactive_rejected(self):
        from django.contrib.auth import authenticate

        self.assertIsNone(authenticate(username="ghi000005", password="wrong-pw"))
        self.assertIsNone(authenticate(username="nosuchuser1", password="whatever"))
        self.assertIsNone(authenticate(username=None, password="correct-pw"))
        self.user.is_active = False
        self.user.save()
        self.assertIsNone(authenticate(username="GHI000005", password="correct-pw"))

    def test_ambiguous_collision_refuses_to_guess(self):
        from django.contrib.auth import authenticate
        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute("DROP INDEX IF EXISTS auth_user_username_lower_uniq")
        dupe = User.objects.create_user("zzz999997", password="correct-pw")
        User.objects.filter(pk=dupe.pk).update(username="GHI000005")
        self.assertIsNone(authenticate(username="ghi000005", password="correct-pw"))


class UserAdminSmokeTest(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_superuser("officer", "officer@example.com", "pw"))
        self.member = User.objects.create_user("jkl000006", password="pw")

    def test_add_page_renders(self):
        self.assertEqual(self.client.get(reverse("admin:auth_user_add")).status_code, 200)

    def test_change_page_renders_without_password_hash_field(self):
        response = self.client.get(reverse("admin:auth_user_change", args=[self.member.pk]))
        self.assertEqual(response.status_code, 200)
        # Stock UserChangeForm renders the password hash read-only, not as an editable field.
        self.assertContains(response, "Raw passwords are not stored")

    def test_add_page_rejects_case_variant_duplicate(self):
        response = self.client.post(
            reverse("admin:auth_user_add"),
            {
                "username": "JKL000006",
                "password1": "some-long-test-password",
                "password2": "some-long-test-password",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="JKL000006").exists())


class UserSerializerCaseInsensitiveTest(TestCase):
    def test_case_variant_duplicate_fails_validation_not_db(self):
        from api.serializers import UserSerializer

        User.objects.create_user("mno000007", password="pw")
        serializer = UserSerializer(data={"username": "MNO000007"})
        self.assertFalse(serializer.is_valid())
        self.assertIn("username", serializer.errors)
