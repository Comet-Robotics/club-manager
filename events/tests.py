from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone

from events.models import Event
from events.views import LOOKUP_USER_LIMIT


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
