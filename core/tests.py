from datetime import timedelta

from django.contrib import admin
from django.contrib.auth.models import User
from django.core import mail
from django.core.mail.backends.base import BaseEmailBackend
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from post_office.connections import connections as email_connections
from post_office.models import STATUS, Email, EmailTemplate, Log

from core.emails import EmailDeliveryError, send_templated_email
from core.models import UserProfile
from payments.models import Payment, Product, PurchasedProduct, Term

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


def make_term(name, start_date, end_date):
    product = Product.objects.create(
        name=f"{name} dues",
        amount_cents=1000,
        max_purchases_per_user=1,
    )
    return Term.objects.create(name=name, start_date=start_date, end_date=end_date, product=product)


def make_member(username, term, *, successful=True):
    """Creates a user with a paid membership in `term` and returns the user."""
    user = User.objects.create_user(username=username, password="pass")
    payment = Payment.objects.create(
        user=user,
        amount_cents=1000,
        completed_at=timezone.now() if successful else None,
    )
    PurchasedProduct.objects.create(product=term.product, payment=payment)
    return user


class UserProfileMembershipTest(TestCase):
    """Membership checks during a term overlap, where two terms are active at once."""

    def setUp(self):
        self.today = timezone.localdate()
        self.spring = make_term("Spring", self.today - timedelta(days=90), self.today + timedelta(days=14))
        self.fall = make_term("Fall", self.today - timedelta(days=1), self.today + timedelta(days=120))
        self.expired = make_term("Expired", self.today - timedelta(days=300), self.today - timedelta(days=1))
        self.future = make_term("Future", self.today + timedelta(days=30), self.today + timedelta(days=300))

    def buy(self, user, term):
        """Buys `term` dues for `user`."""
        payment = Payment.objects.create(user=user, amount_cents=1000, completed_at=timezone.now())
        return PurchasedProduct.objects.create(product=term.product, payment=payment)

    # is_member_for_terms

    def test_is_member_for_terms_returns_only_requested_paid_terms(self):
        user = User.objects.create_user(username="alice", password="pass")
        self.buy(user, self.spring)
        self.buy(user, self.future)

        memberships = user.userprofile.is_member_for_terms([self.spring, self.fall])

        self.assertEqual([term for term, _ in memberships], [self.spring])

    def test_is_member_for_terms_ignores_unpaid_membership(self):
        user = make_member("unpaid", self.spring, successful=False)

        self.assertEqual(user.userprofile.is_member_for_terms([self.spring]), [])

    def test_is_member_for_terms_with_no_terms_returns_empty(self):
        user = make_member("spring_member", self.spring)

        self.assertEqual(user.userprofile.is_member_for_terms([]), [])

    def test_is_member_for_terms_includes_both_terms_during_overlap(self):
        user = User.objects.create_user(username="alice", password="pass")
        self.buy(user, self.spring)
        self.buy(user, self.fall)

        memberships = user.userprofile.is_member_for_terms([self.spring, self.fall])

        self.assertEqual({term for term, _ in memberships}, {self.spring, self.fall})

    def test_is_member_for_terms_does_not_leak_other_users_memberships(self):
        alice = make_member("alice", self.spring)
        make_member("bob", self.spring)

        self.assertEqual([term for term, _ in alice.userprofile.is_member_for_terms([self.spring])], [self.spring])

    # get_active_membership_terms / is_active_member

    def test_member_of_expiring_term_only_is_still_an_active_member(self):
        """The expiring term alone qualifies a member today."""
        user = make_member("spring_only", self.spring)

        self.assertTrue(user.userprofile.is_active_member())
        self.assertEqual([term for term, _ in user.userprofile.get_active_membership_terms()], [self.spring])

    def test_member_of_renewing_term_only_is_an_active_member(self):
        user = make_member("fall_only", self.fall)

        self.assertTrue(user.userprofile.is_active_member())

    def test_member_of_expired_term_is_not_an_active_member(self):
        user = make_member("expired_member", self.expired)

        self.assertFalse(user.userprofile.is_active_member())
        self.assertEqual(user.userprofile.get_active_membership_terms(), [])

    def test_member_of_future_term_only_is_not_yet_an_active_member(self):
        """Paying ahead does not make you a member before the term starts."""
        user = make_member("future_member", self.future)

        self.assertFalse(user.userprofile.is_active_member())

    def test_unpaid_membership_is_not_an_active_member(self):
        user = make_member("unpaid_member", self.spring, successful=False)

        self.assertFalse(user.userprofile.is_active_member())

    def test_no_active_terms_makes_nobody_an_active_member(self):
        user = make_member("former_member", self.expired)
        Term.objects.all().delete()

        self.assertFalse(user.userprofile.is_active_member())

    def test_member_of_past_and_future_terms_but_no_active_term_is_not_active(self):
        user = User.objects.create_user(username="alice", password="pass")
        self.buy(user, self.expired)
        self.buy(user, self.future)

        self.assertFalse(user.userprofile.is_active_member())

    # get_active_members

    def test_get_active_members_includes_members_of_either_active_term(self):
        spring_only = make_member("spring_only", self.spring)
        fall_only = make_member("fall_only", self.fall)
        expired_member = make_member("expired_member", self.expired)
        future_member = make_member("future_member", self.future)
        unpaid_member = make_member("unpaid_member", self.spring, successful=False)

        members = set(UserProfile.get_active_members())

        self.assertEqual(members, {spring_only, fall_only})
        self.assertNotIn(expired_member, members)
        self.assertNotIn(future_member, members)
        self.assertNotIn(unpaid_member, members)

    def test_get_active_members_lists_a_dual_term_member_once(self):
        user = make_member("both_terms", self.spring)
        self.buy(user, self.fall)

        self.assertEqual(list(UserProfile.get_active_members()), [user])

    def test_get_active_members_is_empty_when_no_terms_are_active(self):
        make_member("former_member", self.expired)
        Term.objects.all().delete()

        self.assertEqual(list(UserProfile.get_active_members()), [])
