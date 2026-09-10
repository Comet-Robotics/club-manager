from html.parser import HTMLParser
from unittest import mock

from django.core import mail
from django.core.mail import EmailMultiAlternatives
from django.test import SimpleTestCase, override_settings

from core.emails import PREHEADER_ATTRIBUTE, _contrasting_text_color, build_email, render_email, send_templated_email

# Elements that never have a closing tag, so the nesting check must not expect one.
VOID_ELEMENTS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}

ORG = {
    "name": "Comet Robotics",
    "accent_color": "#bf1e2e",
    "accent_text_color": "#ffffff",
    "logo_url": None,
    "contact_email": "hello@example.org",
    "mailing_address": "800 W Campbell Rd\nRichardson, TX 75080",
    "website_url": "https://example.org",
}

DISCORD_LINK_CONTEXT = {
    "org": ORG,
    "first_name": "Ada",
    "account_details": {"Full Name": "Ada Lovelace", "Discord Name": "ada", "Net ID": "axl123456"},
    "link_url": "https://example.org/accounts/link/1ab2c3d4-0000-0000-0000-000000000000",
}

DISCORD_LINK_TEMPLATE = "email/messages/discord_account_link.html"


class TagNestingParser(HTMLParser):
    """Collects every place an element is closed out of order or left unclosed."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.open_tags: list[str] = []
        self.errors: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag not in VOID_ELEMENTS:
            self.open_tags.append(tag)

    def handle_endtag(self, tag):
        if tag in VOID_ELEMENTS:
            return
        if not self.open_tags:
            self.errors.append(f"</{tag}> closes an element that was never opened")
        elif self.open_tags[-1] != tag:
            self.errors.append(f"</{tag}> closes out of order - innermost open element is <{self.open_tags[-1]}>")
            if tag in self.open_tags:
                while self.open_tags.pop() != tag:
                    pass
        else:
            self.open_tags.pop()

    def close(self):
        super().close()
        self.errors += [f"<{tag}> is never closed" for tag in reversed(self.open_tags)]


class TransactionalEmailRenderingTests(SimpleTestCase):
    """
    Contract for the shared email templates and the derivation pipeline.

    render_email takes its org context as an argument rather than reading ServerSettings, so none
    of this needs a database.
    """

    def assert_well_formed_html(self, html: str):
        parser = TagNestingParser()
        parser.feed(html)
        parser.close()
        self.assertEqual(parser.errors, [], "malformed HTML:\n" + "\n".join(parser.errors))

    def test_html_body_is_a_complete_document(self):
        # The emails these replaced were bare fragments starting at <h2>, which is what
        # SpamAssassin's HTML_MIME_NO_HTML_TAG rule looks for.
        email = render_email(DISCORD_LINK_TEMPLATE, DISCORD_LINK_CONTEXT)

        self.assertTrue(email.html_body.lstrip().startswith("<!DOCTYPE html>"))
        for required in ("<html", "<head", "<title>", 'meta charset="utf-8"', "<body"):
            self.assertIn(required, email.html_body)
        self.assert_well_formed_html(email.html_body)

    def test_stylesheet_is_inlined_for_clients_that_ignore_style_blocks(self):
        email = render_email(DISCORD_LINK_TEMPLATE, DISCORD_LINK_CONTEXT)

        self.assertNotIn("<style", email.html_body)
        # A rule from base.html, and one that only reaches its element via a descendant selector.
        self.assertRegex(email.html_body, r"<h1[^>]*font-size: ?22px")
        self.assertRegex(email.html_body, r"<td[^>]*background-color: ?#bf1e2e")

    def test_outlook_conditional_comment_survives_inlining(self):
        # premailer parses and re-serialises the document; conditional comments are the one thing
        # in base.html that a naive HTML round trip would silently drop.
        email = render_email(DISCORD_LINK_TEMPLATE, DISCORD_LINK_CONTEXT)

        self.assertIn("[if mso]", email.html_body)

    def test_call_to_action_is_an_anchor_not_a_button_element(self):
        email = render_email(DISCORD_LINK_TEMPLATE, DISCORD_LINK_CONTEXT)

        # <button> inside <a> is invalid, and email clients render it inconsistently or not at all.
        self.assertNotIn("<button", email.html_body)
        self.assertIn(f'href="{DISCORD_LINK_CONTEXT["link_url"]}"', email.html_body)

    def test_text_body_carries_the_same_copy_without_markup(self):
        email = render_email(DISCORD_LINK_TEMPLATE, DISCORD_LINK_CONTEXT)

        self.assertNotIn("<", email.text_body)
        self.assertNotIn("&amp;", email.text_body)
        for expected in ("Ada", "axl123456", DISCORD_LINK_CONTEXT["link_url"], "Comet Robotics"):
            self.assertIn(expected, email.text_body)

    def test_text_body_excludes_the_hidden_preheader(self):
        # The preheader is inbox-preview text padded with zero-width characters. A naive HTML to
        # text conversion pulls it in, junk and all, at the very top of the body.
        email = render_email(DISCORD_LINK_TEMPLATE, DISCORD_LINK_CONTEXT)

        self.assertIn("Confirm the request", email.html_body)
        self.assertNotIn("Confirm the request", email.text_body)
        self.assertNotIn("‌", email.text_body)
        self.assertNotIn(PREHEADER_ATTRIBUTE, email.text_body)

    def test_text_body_keeps_the_org_name_when_the_header_is_a_logo(self):
        # With a logo configured the header is an <img> rather than text. A text conversion that
        # drops images loses the organization name off the top of the message entirely - which is
        # what happened on the first real send.
        with_logo = {**ORG, "logo_url": "https://portal.example.org/media/logos/logo.png"}
        email = render_email(DISCORD_LINK_TEMPLATE, {**DISCORD_LINK_CONTEXT, "org": with_logo})

        self.assertIn("<img", email.html_body)
        self.assertIn("Comet Robotics", email.text_body.splitlines()[0])

    def test_text_body_is_wrapped_but_keeps_table_columns_aligned(self):
        email = render_email(DISCORD_LINK_TEMPLATE, DISCORD_LINK_CONTEXT)

        lines = email.text_body.splitlines()
        self.assertLessEqual(max(len(line) for line in lines), 72)
        # The label/value table should still read as two columns rather than being re-flowed.
        self.assertTrue(
            any(line.startswith("Net ID") and "axl123456" in line for line in lines),
            f"expected an aligned Net ID row, got:\n{email.text_body}",
        )

    def test_copy_reads_correctly_in_both_parts(self):
        email = render_email(DISCORD_LINK_TEMPLATE, DISCORD_LINK_CONTEXT)

        # The text part has no clickable button, so the wording must never refer to one.
        for body in (email.text_body, email.html_body):
            self.assertIn("confirm it below", body)
            self.assertNotIn("button below", body)

    def test_subject_comes_from_the_document_title(self):
        email = render_email(DISCORD_LINK_TEMPLATE, DISCORD_LINK_CONTEXT)

        self.assertEqual(email.subject, "Link your Discord account to Comet Robotics")

    def test_footer_includes_contact_details_when_set(self):
        email = render_email(DISCORD_LINK_TEMPLATE, DISCORD_LINK_CONTEXT)

        for body in (email.text_body, email.html_body):
            self.assertIn("800 W Campbell Rd", body)
            self.assertIn("hello@example.org", body)
            # Substring only - the plain text footer is wrapped, so the surrounding phrase may
            # straddle a line break.
            self.assertIn("unsubscribe", body)

    def test_footer_omits_contact_details_when_unset(self):
        bare_org = {**ORG, "contact_email": "", "mailing_address": "", "website_url": ""}
        email = render_email(DISCORD_LINK_TEMPLATE, {**DISCORD_LINK_CONTEXT, "org": bare_org})

        self.assertNotIn("800 W Campbell Rd", email.text_body)
        # An unset field should not leave a blank line or a dangling separator behind.
        self.assertNotIn("\n\n\n", email.text_body)
        self.assert_well_formed_html(email.html_body)

    def test_values_are_escaped_in_html_and_left_alone_in_text(self):
        context = {**DISCORD_LINK_CONTEXT, "first_name": 'Ada <script>"&'}
        email = render_email(DISCORD_LINK_TEMPLATE, context)

        self.assertNotIn("<script>", email.html_body)
        self.assertIn('Ada <script>"&', email.text_body)


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    EMAIL_FROM="club-manager@example.org",
    PUBLIC_URL="https://portal.example.org",
)
class TransactionalEmailMessageTests(SimpleTestCase):
    """
    Contract for the message we hand to the email backend.

    email_org_context is patched out because it is the only part of sending that reads
    ServerSettings, and none of what is asserted here depends on the database.
    """

    def setUp(self):
        patcher = mock.patch("core.emails.email_org_context", return_value=ORG)
        patcher.start()
        self.addCleanup(patcher.stop)
        mail.outbox = []

    def test_sends_plain_text_as_the_body_and_html_as_the_alternative(self):
        # Getting this the wrong way round produces an HTML-only message, which SpamAssassin's
        # MIME_HTML_ONLY rule scores against us.
        sent = send_templated_email(DISCORD_LINK_TEMPLATE, DISCORD_LINK_CONTEXT, ["ada@example.org"])

        self.assertEqual(sent, 1)
        message = mail.outbox[0]
        self.assertIsInstance(message, EmailMultiAlternatives)
        assert isinstance(message, EmailMultiAlternatives)  # narrows the type for mypy
        self.assertEqual(message.content_subtype, "plain")
        self.assertNotIn("<html", message.body)

        self.assertEqual(len(message.alternatives), 1)
        html_part, content_type = message.alternatives[0]
        self.assertEqual(content_type, "text/html")
        self.assertIn("<html", str(html_part))

    def test_addresses_and_subject_come_from_settings_and_the_template(self):
        message = build_email(DISCORD_LINK_TEMPLATE, DISCORD_LINK_CONTEXT, ["ada@example.org"])

        self.assertEqual(message.subject, "Link your Discord account to Comet Robotics")
        self.assertEqual(message.to, ["ada@example.org"])
        # A named sender is a stronger signal than a bare address, to filters and to readers.
        self.assertEqual(message.from_email, "Comet Robotics <club-manager@example.org>")
        # Replies should reach a person, not the unattended sending address.
        self.assertEqual(message.reply_to, ["hello@example.org"])

    def test_leaves_an_already_named_from_address_alone(self):
        with override_settings(EMAIL_FROM="Comet Robotics Officers <officers@example.org>"):
            message = build_email(DISCORD_LINK_TEMPLATE, DISCORD_LINK_CONTEXT, ["a@example.org"])

        self.assertEqual(message.from_email, "Comet Robotics Officers <officers@example.org>")

    def test_omits_reply_to_when_no_contact_address_is_configured(self):
        with mock.patch("core.emails.email_org_context", return_value={**ORG, "contact_email": ""}):
            message = build_email(DISCORD_LINK_TEMPLATE, DISCORD_LINK_CONTEXT, ["a@example.org"])

        self.assertEqual(message.reply_to, [])

    def test_message_id_uses_the_public_hostname(self):
        # Django would otherwise derive this from socket.getfqdn(), which on a deployed container
        # is an internal hostname that does not match the sending domain.
        message = build_email(DISCORD_LINK_TEMPLATE, DISCORD_LINK_CONTEXT, ["ada@example.org"])

        self.assertTrue(message.extra_headers["Message-ID"].endswith("@portal.example.org>"))

    def test_marks_the_message_as_machine_generated(self):
        message = build_email(DISCORD_LINK_TEMPLATE, DISCORD_LINK_CONTEXT, ["ada@example.org"])

        self.assertEqual(message.extra_headers["Auto-Submitted"], "auto-generated")
        # Not "All", which would also suppress the non-delivery reports we want to keep seeing.
        self.assertEqual(message.extra_headers["X-Auto-Response-Suppress"], "OOF, AutoReply")

    @override_settings(PUBLIC_URL=None)
    def test_omits_message_id_when_there_is_no_public_url_to_derive_it_from(self):
        message = build_email(DISCORD_LINK_TEMPLATE, DISCORD_LINK_CONTEXT, ["ada@example.org"])

        self.assertNotIn("Message-ID", message.extra_headers)


class ContrastingTextColorTests(SimpleTestCase):
    def test_picks_readable_text_for_light_and_dark_backgrounds(self):
        self.assertEqual(_contrasting_text_color("#bf1e2e"), "#ffffff")
        self.assertEqual(_contrasting_text_color("#4BC0FF"), "#000000")
        self.assertEqual(_contrasting_text_color("#fff"), "#000000")

    def test_falls_back_to_white_for_unparseable_values(self):
        self.assertEqual(_contrasting_text_color(""), "#ffffff")
        self.assertEqual(_contrasting_text_color("not a color"), "#ffffff")
