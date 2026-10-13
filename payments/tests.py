import zoneinfo
from datetime import datetime, timedelta
from datetime import timezone as dt_timezone
from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

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
