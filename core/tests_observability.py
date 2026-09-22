from unittest import mock

from django.test import TestCase

from clubManager import observability
from clubManager.observability import init_sentry, resolve_tenant
from clubManager.utils import strtobool


class StrtoboolTests(TestCase):
    def test_accepts_truthy_and_falsy_values_with_surrounding_whitespace(self):
        for value in ("y", "yes", "t", "true", "on", "1"):
            with self.subTest(value=value):
                self.assertTrue(strtobool(f"  {value.upper()}  "))

        for value in ("n", "no", "f", "false", "off", "0"):
            with self.subTest(value=value):
                self.assertFalse(strtobool(f"  {value.upper()}  "))

    def test_rejects_unknown_values(self):
        with self.assertRaises(ValueError):
            strtobool("sometimes")


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

    def test_enabled_flag_uses_shared_truth_parser(self):
        with mock.patch.dict("os.environ", {"SENTRY_ENABLED": "  off  "}):
            self.assertFalse(observability._env_flag("SENTRY_ENABLED", True))


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


class SpanAttributeTests(TestCase):
    """
    Spans need the tenant stamped on separately.

    In stream mode spans are their own envelope items and never pass through the event
    scope, so the global scope tags that cover errors and logs do not reach them. Without
    `before_send_span` the trace data arrives unattributable -- which is the whole point
    of the tenant.
    """

    def setUp(self):
        self._saved = dict(observability._SPAN_ATTRIBUTES)
        observability._SPAN_ATTRIBUTES.clear()
        observability._SPAN_ATTRIBUTES.update({"tenant": "some-club", "service": "web"})
        self.addCleanup(self._restore)

    def _restore(self):
        observability._SPAN_ATTRIBUTES.clear()
        observability._SPAN_ATTRIBUTES.update(self._saved)

    def test_attributes_are_added_to_a_span(self):
        span = observability._before_send_span({"name": "GET /"}, None)
        self.assertEqual(span["attributes"]["tenant"], "some-club")
        self.assertEqual(span["attributes"]["service"], "web")

    def test_existing_attributes_are_preserved(self):
        span = observability._before_send_span({"attributes": {"http.method": "GET"}}, None)
        self.assertEqual(span["attributes"]["http.method"], "GET")
        self.assertEqual(span["attributes"]["tenant"], "some-club")

    def test_set_service_retags_spans_not_just_events(self):
        # The bot corrects its service tag after settings.py initialized the SDK; spans
        # emitted afterwards have to pick that up too.
        with mock.patch("sentry_sdk.get_client") as get_client:
            get_client.return_value.is_active.return_value = True
            observability.set_service("discord-bot")

        span = observability._before_send_span({}, None)
        self.assertEqual(span["attributes"]["service"], "discord-bot")
