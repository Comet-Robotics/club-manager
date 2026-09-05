from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase

from accounts.models import UserStub, validate_after_registration_redirect_destination


class UserStubRedirectDestinationTests(SimpleTestCase):
    def test_allows_site_relative_destination(self):
        validate_after_registration_redirect_destination("/pay/whatever?invoice=123")

    def test_rejects_external_redirect_destinations(self):
        unsafe_destinations = [
            "https://attacker.example/pay/whatever",
            "//attacker.example/pay/whatever",
            "/\\attacker.example/pay/whatever",
            "javascript:alert(1)",
        ]

        for destination in unsafe_destinations:
            with self.subTest(destination=destination):
                with self.assertRaises(ValidationError):
                    validate_after_registration_redirect_destination(destination)


class UserStubDiscordUserTests(TestCase):
    @patch("core.signals.handlers.get_major_from_netid", return_value=None)
    def test_create_persists_discord_user_id_on_profile(self, _get_major_from_netid):
        user_stub = UserStub.create(
            net_id="discordstub",
            after_registration_redirect_destination="",
            discord_user_id="123456789012345678",
        )

        user_stub.user.userprofile.refresh_from_db()
        self.assertEqual(user_stub.user.userprofile.discord_id, "123456789012345678")

    @patch("core.signals.handlers.get_major_from_netid", return_value=None)
    def test_management_command_accepts_discord_user_id(self, _get_major_from_netid):
        call_command(
            "create_user_stub",
            "commandstub",
            "--discord-user-id",
            "987654321098765432",
        )

        user_stub = UserStub.objects.get(user__username="commandstub")
        self.assertEqual(user_stub.user.userprofile.discord_id, "987654321098765432")
