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
