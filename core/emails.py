"""
Rendering and sending for transactional email.

Each email is one Django template under ``core/templates/email/messages/`` containing ordinary
HTML, extending ``email/base.html`` for the header, footer, and stylesheet. Everything else is
derived from that single render:

* the **subject** is the ``<title>`` of the rendered document
* the **HTML part** is the document with ``base.html``'s stylesheet inlined by css_inline,
  because email clients largely ignore ``<style>`` blocks
* the **plain text part** is what a browser would show as the rendered page's text, via inscriptis

So there is no separate plain text template to keep in step, and no repeated ``style="..."``
attributes. The one thing this asks of whoever writes a message template is that the copy read
correctly in both parts - say "confirm below", never "click the button below" - and that layout
tables are only used for layout, since inscriptis will faithfully reproduce a table as a table.
"""

import re
import textwrap
from dataclasses import dataclass
from email.utils import formataddr, make_msgid, parseaddr
from urllib.parse import urlparse

import css_inline
from bs4 import BeautifulSoup
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from inscriptis import get_text

# Plain text bodies are wrapped, which is the width every mail client's plain text view is
# designed around.
PLAIN_TEXT_WIDTH = 72

# Marks the hidden inbox-preview line in base.html. A data attribute rather than a class so that
# it survives whatever the CSS inliner decides to do with the classes it has consumed.
PREHEADER_ATTRIBUTE = "data-preheader"


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
    # Inline base.html's stylesheet. Conditional comments for Outlook survive this, and descendant
    # selectors are resolved onto the elements they matched.
    html = css_inline.inline(
        render_to_string(message_template, context),
        keep_style_tags=False,
        # At-rules cannot be inlined onto an element, so keep them in a style block rather than
        # dropping them - otherwise a future @media rule would vanish silently.
        keep_at_rules=True,
        # A send must never make a network call. We have no external stylesheets, and this makes
        # sure a stray <link> could not introduce one.
        load_remote_stylesheets=False,
    )

    document = BeautifulSoup(html, "html.parser")
    subject = document.title.get_text(strip=True) if document.title else ""

    # The preheader is inbox-preview text, deliberately invisible in the message itself, so it has
    # no business in the plain text body either. Removed from the parsed copy only - the HTML we
    # send keeps it.
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
    for line in get_text(html).splitlines():
        line = line.rstrip()
        # inscriptis pads table cells apart with runs of spaces to preserve their columns.
        # Re-wrapping such a line would destroy the alignment, so only prose gets wrapped.
        if re.search(r"\S {2,}\S", line):
            lines.append(line)
        else:
            lines.extend(textwrap.wrap(line, PLAIN_TEXT_WIDTH, break_long_words=False, break_on_hyphens=False) or [""])

    # Block elements each end their own line, so wherever two of them meet there is a run of blank
    # lines to collapse.
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
    # Imported here because core.models imports from payments.models, and a module-level import
    # would make core.emails unusable before the app registry is ready.
    from core.models import ServerSettings

    if settings.FEATURE_FLAGS["AUTO_SERVER_SETTINGS_INIT"]:
        server_settings = ServerSettings.objects.get_or_create()[0]
    else:
        server_settings = ServerSettings.objects.get()

    logo_url = None
    if server_settings.logo and settings.PUBLIC_URL:
        # Email clients have no page to resolve a relative URL against, so assets need absolute
        # ones.
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
    """Put the organisation's name in front of EMAIL_FROM, if it isn't there already."""
    display_name, address = parseaddr(settings.EMAIL_FROM)
    if not address:
        # Nothing parseable to work with - leave whatever was configured alone rather than
        # silently sending from a different address.
        return settings.EMAIL_FROM
    # A bare address is a weaker sender signal than a named one, both to spam filters and to the
    # person deciding whether the mail looks legitimate.
    return formataddr((display_name or org_name, address))


def _transactional_headers() -> dict[str, str]:
    headers = {
        # RFC 3834: tells conforming responders not to reply to this message.
        "Auto-Submitted": "auto-generated",
        # Microsoft's equivalent, which is what actually stops out-of-office replies from Exchange
        # and Microsoft 365 - where most of our recipients read their mail. Deliberately not "All",
        # which would also suppress the non-delivery reports we want to see.
        "X-Auto-Response-Suppress": "OOF, AutoReply",
    }

    # Django defaults the Message-ID domain to socket.getfqdn(), which on a container or VPS is
    # usually something like "localhost" or an internal hostname. A Message-ID that doesn't match
    # the sending domain is a well-known spam signal, so derive it from PUBLIC_URL instead.
    message_id_domain = urlparse(settings.PUBLIC_URL).hostname if settings.PUBLIC_URL else None
    if message_id_domain:
        headers["Message-ID"] = make_msgid(domain=message_id_domain)

    return headers


def build_email(message_template: str, context: dict, to: list[str]) -> EmailMultiAlternatives:
    """Render ``message_template`` and build the multipart message for it, without sending."""
    org = email_org_context()
    rendered = render_email(message_template, {**context, "org": org})

    message = EmailMultiAlternatives(
        subject=rendered.subject,
        # Plain text is the message body and HTML is the alternative, which is what makes this
        # multipart/alternative. HTML-only mail scores against us in every spam filter.
        body=rendered.text_body,
        from_email=_from_address(org["name"]),
        to=to,
        # Replies should reach a person. Without this they go to the sending address, which for a
        # relay like Mailtrap is unattended.
        reply_to=[org["contact_email"]] if org["contact_email"] else None,
        headers=_transactional_headers(),
    )
    message.attach_alternative(rendered.html_body, "text/html")
    return message


def send_templated_email(message_template: str, context: dict, to: list[str]) -> int:
    """
    Render and send a transactional email. Returns the number of messages sent.

    Raises on failure, in the same way as ``send_mail(fail_silently=False)``. Callers that need to
    reuse a connection or add attachments should use :func:`build_email` and send it themselves.
    """
    return build_email(message_template, context, to).send()
