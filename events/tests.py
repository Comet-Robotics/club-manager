from datetime import timedelta

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse

from events.models import Event
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


class SignInMembershipRenewalTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.staff_user = User.objects.create_user(username="staff", password="pass", is_staff=True)
        self.client.login(username="staff", password="pass")
        self.event = Event.objects.create(event_name="Test Event", event_date=timezone.now())
        today = timezone.localdate()

        self.spring_term = self.create_term("Spring", today - timedelta(days=90), today + timedelta(days=14))
        self.fall_term = self.create_term("Fall", today - timedelta(days=1), today + timedelta(days=120))

    def create_term(self, name, start_date, end_date):
        product = Product.objects.create(
            name=f"{name} dues",
            amount_cents=1000,
            max_purchases_per_user=1,
        )
        return Term.objects.create(name=name, start_date=start_date, end_date=end_date, product=product)

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
