from unittest import mock

from django.test import TestCase

from clubManager import observability, settings
from clubManager.observability import init_sentry, resolve_tenant
from clubManager.utils import parse_bool


class ParseBoolTests(TestCase):
    def test_accepts_truthy_and_falsy_values_with_surrounding_whitespace(self):
        for value in ("y", "yes", "t", "true", "on", "1"):
            with self.subTest(value=value):
                self.assertTrue(parse_bool(f"  {value.upper()}  "))

        for value in ("n", "no", "f", "false", "off", "0"):
            with self.subTest(value=value):
                self.assertFalse(parse_bool(f"  {value.upper()}  "))

    def test_rejects_unknown_values(self):
        with self.assertRaises(ValueError):
            parse_bool("sometimes")


class InitSentryTests(TestCase):
    """
    The conditions under which Sentry must stay quiet.

    Reporting from a developer's laptop pollutes the issue feed for everyone sharing the
    project, and an instance has to be able to opt out, so each of these paths is worth
    pinning down.
    """

    def _init_sentry(self, *, debug=False, public_url="https://example.org", **overrides):
        config = {
            "sentry_enabled": True,
            "dsn": "https://sentry.example/123",
            "environment": "test",
            "release": None,
            "traces_sample_rate": 0.2,
            "profile_session_sample_rate": 0.5,
            "configured_tenant": "",
        }
        config.update(overrides)
        return init_sentry(debug=debug, public_url=public_url, **config)

    def test_disabled_in_debug(self):
        self.assertFalse(self._init_sentry(debug=True))

    def test_disabled_when_flag_is_falsy(self):
        self.assertFalse(self._init_sentry(sentry_enabled=False))

    def test_disabled_when_dsn_is_blank(self):
        self.assertFalse(self._init_sentry(dsn=""))

    def test_debug_wins_over_an_explicitly_enabled_flag(self):
        # Turning the flag on locally must not start reporting anyway.
        self.assertFalse(self._init_sentry(debug=True, sentry_enabled=True))

    def test_unparseable_flag_falls_back_to_enabled_in_settings(self):
        # A typo in the env var shouldn't silently switch reporting off.
        with mock.patch.dict("os.environ", {"SENTRY_ENABLED": "maybe"}):
            self.assertTrue(settings._env_value("SENTRY_ENABLED", True, parse_bool, "truth value"))

    def test_enabled_flag_uses_shared_truth_parser(self):
        with mock.patch.dict("os.environ", {"SENTRY_ENABLED": "  off  "}):
            self.assertFalse(settings._env_value("SENTRY_ENABLED", True, parse_bool, "truth value"))

    def test_sample_rate_uses_shared_env_parser(self):
        with mock.patch.dict("os.environ", {"SENTRY_TRACES_SAMPLE_RATE": " 0.35 "}):
            self.assertEqual(settings._env_value("SENTRY_TRACES_SAMPLE_RATE", 0.2, float, "number"), 0.35)

    def test_invalid_sample_rate_uses_default(self):
        with mock.patch.dict("os.environ", {"SENTRY_TRACES_SAMPLE_RATE": "not-a-number"}):
            self.assertEqual(settings._env_value("SENTRY_TRACES_SAMPLE_RATE", 0.2, float, "number"), 0.2)


class ResolveTenantTests(TestCase):
    """Instances share one Sentry project, so events must stay attributable."""

    def test_defaults_to_public_url_hostname(self):
        self.assertEqual(
            resolve_tenant("https://portal.cometrobotics.org/x", configured_tenant=""),
            "portal.cometrobotics.org",
        )

    def test_explicit_tenant_wins(self):
        self.assertEqual(
            resolve_tenant("https://portal.cometrobotics.org", configured_tenant="comet-robotics"),
            "comet-robotics",
        )

    def test_falls_back_when_public_url_is_missing(self):
        self.assertEqual(resolve_tenant(None, configured_tenant=""), "unknown")


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
