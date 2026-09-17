"""
Rendering and sending for transactional email.
"""

import re
import textwrap
from dataclasses import dataclass
from email.utils import formataddr, parseaddr

import css_inline
from bs4 import BeautifulSoup
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from inscriptis import get_text
from inscriptis.model.config import ParserConfig

# Plain text bodies are wrapped, which is the width every mail client's plain text view is
# designed around.
PLAIN_TEXT_EMAIL_CHARACTER_WRAP_WIDTH = 72

_TEXT_LAYOUT_CONFIG = ParserConfig(display_images=True, deduplicate_captions=True)

# Marks the hidden inbox-preview line in base.html. A data attribute rather than a class so that
# it survives whatever the CSS inliner decides to do with the classes it has consumed.
PREHEADER_ATTRIBUTE = "data-preheader"


class EmailDeliveryError(Exception):
    """Raised when a message was rendered and stored but the delivery backend would not take it."""


@dataclass(frozen=True)
class RenderedEmail:
    subject: str
    text_body: str
    html_body: str


def render_email(message_template: str, context: dict) -> RenderedEmail:
    """
    Render a message template into a subject line, a plain text body, and an HTML body.

    ``context`` should include an ``org`` mapping (see :func:`email_org_context`). This touches
    neither the database nor the email backend, so it is safe to call from tests.
    """

    html = css_inline.inline(
        render_to_string(message_template, context),
        keep_style_tags=False,
        keep_at_rules=True,
        load_remote_stylesheets=False,
    )

    document = BeautifulSoup(html, "html.parser")
    subject = document.title.get_text(strip=True) if document.title else ""

    for preheader in document.select(f"[{PREHEADER_ATTRIBUTE}]"):
        preheader.decompose()

    return RenderedEmail(
        subject=subject,
        text_body=_layout_as_text(str(document)),
        html_body=html.strip() + "\n",
    )


def _layout_as_text(html: str) -> str:
    """Render ``html`` to text the way a browser would, then tidy it for a mail body."""
    lines = []
    for line in get_text(html, _TEXT_LAYOUT_CONFIG).splitlines():
        line = line.rstrip()
        if re.search(r"\S {2,}\S", line):
            lines.append(line)
        else:
            lines.extend(
                textwrap.wrap(
                    line, PLAIN_TEXT_EMAIL_CHARACTER_WRAP_WIDTH, break_long_words=False, break_on_hyphens=False
                )
                or [""]
            )

    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip() + "\n"


def _contrasting_text_color(background_hex: str) -> str:
    """
    Pick black or white text for ``background_hex``, whichever is more readable on it.

    Email clients support neither CSS custom properties nor ``color-mix()``, so this has to be
    resolved at render time or a light accent colour ends up as white text on a white button.
    """
    color = (background_hex or "").lstrip("#")
    if len(color) == 3:
        color = "".join(channel * 2 for channel in color)
    try:
        red, green, blue = (int(color[offset : offset + 2], 16) for offset in (0, 2, 4))
    except (ValueError, IndexError):
        return "#ffffff"

    # Relative luminance, per WCAG 2.x, simplified to the sRGB coefficients.
    luminance = (0.299 * red + 0.587 * green + 0.114 * blue) / 255
    return "#000000" if luminance > 0.6 else "#ffffff"


def email_org_context() -> dict:
    """Build the ``org`` context that the email header, footer, and stylesheet render from."""
    from core.models import ServerSettings

    server_settings = ServerSettings.objects.get_or_create()[0]

    logo_url = None
    if server_settings.logo and settings.PUBLIC_URL:
        logo_url = f"{settings.PUBLIC_URL.rstrip('/')}{server_settings.logo.url}"

    return {
        "name": server_settings.organization_name,
        "accent_color": server_settings.accent_color_hex,
        "accent_text_color": _contrasting_text_color(server_settings.accent_color_hex),
        "logo_url": logo_url,
        "contact_email": server_settings.contact_email,
        "mailing_address": server_settings.mailing_address,
        "website_url": server_settings.website_url,
    }


def _from_address(org_name: str) -> str:
    """Put the organization's name in front of EMAIL_FROM, if it isn't there already."""
    display_name, address = parseaddr(settings.EMAIL_FROM)
    if not address:
        # Nothing parseable to work with - leave whatever was configured alone rather than
        # silently sending from a different address.
        return settings.EMAIL_FROM

    return formataddr((display_name or org_name, address))


def _transactional_headers() -> dict[str, str]:
    # Headers that tell mailboxes not to reply to this message and stops out-of-office replies from Exchange and Microsoft 365
    #
    # Message-ID is deliberately not set here. django-post_office assigns one when it persists
    # the message (POST_OFFICE["MESSAGE_ID_ENABLED"], with the domain taken from PUBLIC_URL) and
    # overwrites whatever is in these headers with the value it stored, so that the ID in the
    # database is the one that actually goes out on the wire.
    return {
        "Auto-Submitted": "auto-generated",
        "X-Auto-Response-Suppress": "OOF, AutoReply",
    }


def build_email(message_template: str, context: dict, to: list[str]) -> EmailMultiAlternatives:
    """Render ``message_template`` and build the multipart message for it, without sending."""
    org = email_org_context()
    rendered = render_email(message_template, {**context, "org": org})

    message = EmailMultiAlternatives(
        subject=rendered.subject,
        body=rendered.text_body,
        from_email=_from_address(org["name"]),
        to=to,
        reply_to=[org["contact_email"]] if org["contact_email"] else None,
        headers=_transactional_headers(),
    )
    message.attach_alternative(rendered.html_body, "text/html")
    return message


def send_templated_email(message_template: str, context: dict, to: list[str]) -> int:
    """
    Render and send a transactional email. Returns the number of messages sent.

    Sending goes through django-post_office, so the message is written to the database and shows
    up under Post Office in the admin whether or not delivery works. Raises on failure, in the
    same way as ``send_mail(fail_silently=False)``. Callers that need to reuse a connection or add
    attachments should use :func:`build_email` and send it themselves.
    """
    sent = build_email(message_template, context, to).send()

    # post_office catches delivery exceptions so that it can record the failure against the
    # stored message, and reports it by returning a send count of 0 instead of re-raising. Turn
    # that back into an exception: every caller here treats a transactional email as something
    # that has to either go out or be complained about loudly, and the record of the failure is
    # already in the database by this point.
    if not sent:
        raise EmailDeliveryError(f"Failed to deliver {message_template} to {', '.join(to)} - see the Post Office admin")

    return sent
