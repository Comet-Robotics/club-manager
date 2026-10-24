"""
Volume limits for the emails that self-service registration sends.

Two unauthenticated endpoints - `/accounts/register` and the `confirm_registration`
branch of `/payments/<id>/pay/` - turn a typed-in Net ID into mail addressed to
`<netid>@utdallas.edu`. `UserStub` already refuses a second pending registration for the
same Net ID inside 24 hours, which protects each *recipient* from being mailed twice,
but it says nothing about how much mail leaves the club's SMTP domain: someone walking
plausible Net IDs gets one message per Net ID, and one message per Net ID is all it
takes to burn the domain's reputation. The counters here cap that - per client over an
hour, and across the whole instance over a day.

`/link` is metered too, per Discord account rather than per address. A Discord account can
only hold one pending registration, but it can replace it (the way out of a Net ID typo),
and every replacement is another email against the same daily sending budget.

Only emails that are actually about to go out are counted: callers create the `UserStub`
first, so a Net ID that already has an account or a pending link costs nothing, and a
client that is over its own limit stops there without spending the instance-wide one.
"""

from django.conf import settings
from django.http import HttpRequest
from django_ratelimit.core import is_ratelimited

# Shared by both web entry points on purpose: they send the same email, so a client that
# has used up its allowance on the registration page has used it up on the payment page too.
PER_IP_GROUP = "registration-email-per-ip"
PER_DISCORD_USER_GROUP = "registration-email-per-discord-user"
GLOBAL_GROUP = "registration-email-global"


def get_client_ip(request: HttpRequest) -> str:
    """
    The address to meter this request against.

    In production the public ingress is Cloudflare Tunnel, which hands requests to nginx,
    which proxies to gunicorn over a unix socket. `REMOTE_ADDR` is empty there, so the
    client address is whatever nginx put in `X-Real-IP` (`include proxy_params`). nginx
    only knows the real client because its realip module swaps in `CF-Connecting-IP` for
    connections from the tunnel (deploy/clubManager.nginx.conf.template); without that,
    every request would carry the tunnel's own address and share one bucket.

    Trusting a header is safe only because nginx *overwrites* `X-Real-IP` on every request
    and nothing else can reach gunicorn. If the app is ever exposed directly, or put
    behind another proxy, this has to be revisited.

    Under `runserver` there is no proxy and no header, so fall back to `REMOTE_ADDR`.
    """
    return request.META.get("HTTP_X_REAL_IP") or request.META.get("REMOTE_ADDR") or "unknown"


def _spend(group: str, bucket: str, rate: str) -> bool:
    """
    Count one email against `bucket` and say whether that put it over `rate`.

    django-ratelimit only reads the request to match methods and build keys, and with
    the default method set and a key that ignores it, it never looks - which lets the
    Discord bot, which has no request, share these buckets.

    Counting is `cache.add` followed by `cache.incr`. The `incr` half is atomic: the cache
    backend is `common.cache.AtomicDatabaseCache`, which takes a Postgres row lock on the
    bucket before its read-modify-write, so two workers racing on the same bucket
    serialize instead of losing an increment.
    """
    return is_ratelimited(None, group=group, key=lambda _group, _request: bucket, rate=rate, increment=True)


def _over_global_limit() -> bool:
    return _spend(GLOBAL_GROUP, "all", settings.REGISTRATION_EMAIL_RATE_GLOBAL)


def registration_throttled(request: HttpRequest) -> bool:
    """
    Count a registration email from the web and say whether it must not be sent.

    Call once a `UserStub` exists and the email is next, and delete the stub if this says
    no. The per-client limit is checked first and the instance-wide one only if it
    passes, so a single client hammering the form cannot close registration for everyone.
    """
    if _spend(PER_IP_GROUP, get_client_ip(request), settings.REGISTRATION_EMAIL_RATE_PER_IP):
        return True
    return _over_global_limit()


def discord_registration_throttled(discord_user_id: str) -> bool:
    """`registration_throttled` for `/link`, metered per Discord account instead of per address."""
    if _spend(PER_DISCORD_USER_GROUP, str(discord_user_id), settings.REGISTRATION_EMAIL_RATE_PER_DISCORD_USER):
        return True
    return _over_global_limit()
