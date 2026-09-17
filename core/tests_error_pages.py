from unittest import mock

from django.test import RequestFactory, TestCase

from common import errors

SHOWN_TO_USER = "Include this reference code"


class ErrorPageTests(TestCase):
    """The error pages have to render when the rest of the app can't."""

    def setUp(self):
        self.request = RequestFactory().get("/anything")

    def _handlers(self):
        exception = Exception("boom")
        return [
            (400, errors.bad_request, (self.request, exception)),
            (403, errors.permission_denied, (self.request, exception)),
            (404, errors.page_not_found, (self.request, exception)),
            (500, errors.server_error, (self.request,)),
        ]

    def test_each_handler_returns_its_status_code(self):
        for status, handler, args in self._handlers():
            with self.subTest(status=status):
                self.assertEqual(handler(*args).status_code, status)

    def test_event_id_is_shown_to_the_user(self):
        with mock.patch("common.errors.sentry_sdk.last_event_id", return_value="cafebabe1234"):
            for status, handler, args in self._handlers():
                with self.subTest(status=status):
                    body = handler(*args).content.decode()
                    self.assertIn("cafebabe1234", body)
                    self.assertIn(SHOWN_TO_USER, body)

    def test_no_reference_code_shown_when_sentry_is_off(self):
        # With Sentry disabled there is no event to reference, so the page must not
        # offer the user a code that would find nothing.
        with mock.patch("common.errors.sentry_sdk.last_event_id", return_value=None):
            for status, handler, args in self._handlers():
                with self.subTest(status=status):
                    body = handler(*args).content.decode()
                    self.assertNotIn(SHOWN_TO_USER, body)
                    self.assertNotIn("<code>", body)

    def test_pages_do_not_depend_on_the_database(self):
        # The templates are rendered without a request precisely so that context
        # processors -- which read ServerSettings -- can't take the error page down with
        # them. Guard against someone switching these back to render(request, ...).
        with mock.patch("common.errors.sentry_sdk.last_event_id", return_value=None):
            with self.assertNumQueries(0):
                for _status, handler, args in self._handlers():
                    handler(*args)
