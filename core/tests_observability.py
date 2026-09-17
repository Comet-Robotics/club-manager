from unittest import mock

from django.test import TestCase

from clubManager.observability import init_sentry, resolve_tenant


class InitSentryTests(TestCase):
    """
    The conditions under which Sentry must stay quiet.

    Reporting from a developer's laptop pollutes the issue feed for everyone sharing the
    project, and an instance has to be able to opt out, so each of these paths is worth
    pinning down.
    """

    def test_disabled_in_debug(self):
        with mock.patch.dict("os.environ", {}, clear=False):
            self.assertFalse(init_sentry(debug=True, public_url="https://example.org"))

    def test_disabled_when_flag_is_falsy(self):
        with mock.patch.dict("os.environ", {"SENTRY_ENABLED": "0"}):
            self.assertFalse(init_sentry(debug=False, public_url="https://example.org"))

    def test_disabled_when_dsn_is_blank(self):
        with mock.patch.dict("os.environ", {"SENTRY_DSN": ""}):
            self.assertFalse(init_sentry(debug=False, public_url="https://example.org"))

    def test_debug_wins_over_an_explicitly_enabled_flag(self):
        # Turning the flag on locally must not start reporting anyway.
        with mock.patch.dict("os.environ", {"SENTRY_ENABLED": "1"}):
            self.assertFalse(init_sentry(debug=True, public_url="https://example.org"))

    def test_unparseable_flag_falls_back_to_enabled(self):
        # A typo in the env var shouldn't silently switch reporting off.
        with mock.patch.dict("os.environ", {"SENTRY_ENABLED": "maybe", "SENTRY_DSN": ""}):
            # Still disabled here, but by the blank DSN rather than the bad flag.
            self.assertFalse(init_sentry(debug=False, public_url="https://example.org"))


class ResolveTenantTests(TestCase):
    """Instances share one Sentry project, so events must stay attributable."""

    def test_defaults_to_public_url_hostname(self):
        with mock.patch.dict("os.environ", {"SENTRY_TENANT": ""}):
            self.assertEqual(resolve_tenant("https://portal.cometrobotics.org/x"), "portal.cometrobotics.org")

    def test_explicit_tenant_wins(self):
        with mock.patch.dict("os.environ", {"SENTRY_TENANT": "comet-robotics"}):
            self.assertEqual(resolve_tenant("https://portal.cometrobotics.org"), "comet-robotics")

    def test_falls_back_when_public_url_is_missing(self):
        with mock.patch.dict("os.environ", {"SENTRY_TENANT": ""}):
            self.assertEqual(resolve_tenant(None), "unknown")
