"""
Sentry setup for Club Manager.

Lives outside settings.py so the enable/disable rules are readable and testable on
their own. `init_sentry()` is called near the top of settings.py, before Django loads
any application code -- the Django integration needs to be initialized that early to
patch framework internals.
"""

import logging
import os
from urllib.parse import urlparse

# Comet Robotics' hosted Sentry project. Every instance reports here by default so that
# a breakage on any deployment is debuggable from one place; events are tagged with a
# tenant (see `resolve_tenant`) to tell those deployments apart. An instance that wants
# its own project can set SENTRY_DSN, or opt out entirely with SENTRY_ENABLED=0.
DEFAULT_SENTRY_DSN = "https://474f3f624969b1b7f16b6243ed154185@o4512098201698304.ingest.us.sentry.io/4512098322743296"

_TRUTHY = ("y", "yes", "t", "true", "on", "1")
_FALSY = ("n", "no", "f", "false", "off", "0")


def _env_flag(name: str, default: bool) -> bool:
    """Read a boolean env var, falling back to `default` when unset or unparseable."""
    raw = os.getenv(name)
    if raw is None:
        return default
    value = raw.strip().lower()
    if value in _TRUTHY:
        return True
    if value in _FALSY:
        return False
    print(f"Warning: {name} is set to {raw!r}, which isn't a truth value. Using default {default}.")
    return default


def _env_float(name: str, default: float) -> float:
    """Read a float env var, falling back to `default` when unset or unparseable."""
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        print(f"Warning: {name} is set to {raw!r}, which isn't a number. Using default {default}.")
        return default


def resolve_tenant(public_url: str | None) -> str:
    """
    Identify which Club Manager deployment an event came from.

    Instances share one Sentry project, so every event needs a tenant tag to be
    attributable. The host an instance is served from is already unique per deployment
    and is configured everywhere, so it makes a good default; SENTRY_TENANT overrides it
    when a friendlier name is wanted.
    """
    configured = os.getenv("SENTRY_TENANT", "").strip()
    if configured:
        return configured

    hostname = urlparse(public_url).hostname if public_url else None
    return hostname or "unknown"


# Scope tags reach errors and logs, but not streamed spans -- those are their own
# envelope items and never pass through the event scope. These are stamped onto each
# span by `_before_send_span` instead. Mutable because set_service() corrects `service`
# after settings.py has already initialized the SDK.
_SPAN_ATTRIBUTES: dict[str, str] = {}


def _before_send_span(span, _hint):
    """Stamp the tenant and service onto every streamed span."""
    span.setdefault("attributes", {}).update(_SPAN_ATTRIBUTES)
    return span


def init_sentry(*, debug: bool, public_url: str | None, service: str = "web") -> bool:
    """
    Initialize the Sentry SDK unless this instance has opted out.

    Sentry stays off in local development: reporting is skipped entirely when DEBUG is
    on, when SENTRY_ENABLED is falsy, or when the DSN has been blanked out. Returns
    whether the SDK was actually initialized.

    `service` distinguishes the processes that share this configuration -- the Django
    site and the Discord bot both load settings.py, and their errors look nothing alike.
    """
    if debug:
        print("Sentry is disabled because DEBUG is on.")
        return False

    if not _env_flag("SENTRY_ENABLED", True):
        print("Sentry is disabled because SENTRY_ENABLED is set to a falsy value.")
        return False

    dsn = os.getenv("SENTRY_DSN", DEFAULT_SENTRY_DSN).strip()
    if not dsn:
        print("Sentry is disabled because SENTRY_DSN is set to an empty value.")
        return False

    # Imported lazily so a deployment that opted out doesn't pay for the import, and so
    # settings.py still loads if the dependency somehow isn't installed.
    import sentry_sdk
    from sentry_sdk.integrations.asyncio import AsyncioIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration

    sentry_sdk.init(
        dsn=dsn,
        environment=os.getenv("SENTRY_ENVIRONMENT", "production"),
        release=os.getenv("SENTRY_RELEASE") or None,
        # Attaches request headers, client IP, and the signed-in user to events. This is
        # the debugging metadata that makes a production report actionable.
        send_default_pii=True,
        # Both rates are metered, so these are deliberately not the 1.0 the Sentry
        # onboarding wizard suggests -- that value is meant to show data immediately in a
        # demo, not to run in production. Tune per instance via the env vars.
        traces_sample_rate=_env_float("SENTRY_TRACES_SAMPLE_RATE", 0.2),
        # Send spans in batches as they finish, instead of buffering a whole transaction
        # in memory until its root span closes. Lifts the 1000-span-per-transaction cap
        # and gets trace data visible sooner. The one behavioral change: breadcrumbs are
        # no longer attached to spans -- they stay on errors, which is where we read them.
        trace_lifecycle="stream",
        # Only honoured in stream mode; it is how the tenant reaches span data at all.
        before_send_span=_before_send_span,
        profile_session_sample_rate=_env_float("SENTRY_PROFILE_SESSION_SAMPLE_RATE", 0.5),
        profile_lifecycle="trace",
        enable_logs=True,
        integrations=[
            LoggingIntegration(
                # Anything logged at INFO or above becomes a breadcrumb and a searchable
                # Sentry log; ERROR and above additionally becomes its own issue. This is
                # what picks up the stdlib `logging` calls already scattered through the
                # Django apps and the Discord bot -- they need no changes.
                level=logging.INFO,
                sentry_logs_level=logging.INFO,
                event_level=logging.ERROR,
            ),
            # The bot runs its Discord client and its FastAPI server as sibling asyncio
            # tasks. Without this, an exception that kills one of those tasks is never
            # reported. Not auto-enabled, unlike the Django and FastAPI integrations.
            AsyncioIntegration(),
        ],
    )

    # Global scope, so these land on every event and log the process sends rather than
    # only on ones raised inside a request. Spans are covered separately, via
    # _before_send_span.
    tenant = resolve_tenant(public_url)
    scope = sentry_sdk.get_global_scope()
    scope.set_tag("tenant", tenant)
    scope.set_tag("service", service)
    _SPAN_ATTRIBUTES.update({"tenant": tenant, "service": service})

    return True


def set_service(service: str) -> None:
    """
    Re-tag this process after settings.py has already initialized Sentry.

    The Discord bot boots by importing clubManager.settings, which initializes the SDK
    as a side effect and tags it as the web service. Rather than initialize a second
    time, the bot corrects the tag through here.
    """
    try:
        import sentry_sdk
    except ImportError:
        return

    if sentry_sdk.get_client().is_active():
        sentry_sdk.get_global_scope().set_tag("service", service)
        _SPAN_ATTRIBUTES["service"] = service


def trigger_error(request):
    """
    Deliberately raise, to confirm a deployment is reporting to Sentry.

    Only routed when SENTRY_DEBUG_ENDPOINT is set. Sentry is off under DEBUG, so
    verifying the wiring means exercising it on a real deployment; this gives a way to
    do that on purpose instead of waiting for a genuine error.
    """
    raise ZeroDivisionError("Deliberate error to verify Sentry reporting.")


def instrument_discord_bot(bot) -> None:
    """
    Report unhandled Discord errors to Sentry.

    py-cord swallows exceptions raised inside event listeners and slash commands,
    printing them to stderr and carrying on. There's no Sentry integration for it, so
    the two error hooks it does expose get wired up by hand.
    """
    try:
        import sentry_sdk
    except ImportError:
        return

    if not sentry_sdk.get_client().is_active():
        return

    @bot.event
    async def on_error(event: str, *args, **kwargs) -> None:
        """Catch-all for exceptions raised inside any event listener."""
        with sentry_sdk.new_scope() as scope:
            scope.set_tag("discord.event", event)
            sentry_sdk.capture_exception()

    @bot.event
    async def on_application_command_error(ctx, error: Exception) -> None:
        """Catch-all for exceptions raised inside a slash command."""
        with sentry_sdk.new_scope() as scope:
            command = getattr(ctx, "command", None)
            scope.set_tag("discord.command", getattr(command, "qualified_name", "unknown"))

            user = getattr(ctx, "user", None) or getattr(ctx, "author", None)
            if user is not None:
                scope.set_user({"id": str(user.id), "username": str(user)})

            sentry_sdk.capture_exception(error)

        # py-cord's default handler re-raises to stderr; keep that so the error is still
        # visible in the bot's own logs.
        raise error
