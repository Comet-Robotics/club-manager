"""
Volume limits for the emails that self-service registration sends.

Two unauthenticated endpoints - `/accounts/register` and the `confirm_registration`
branch of `/payments/<id>/pay/` - turn a typed-in Net ID into mail addressed to
`<netid>@utdallas.edu`. `UserStub` already refuses a second pending registration for the
same Net ID inside 24 hours, which protects each *recipient* from being mailed twice,
but it says nothing about how much mail leaves the club's SMTP domain: someone walking
plausible Net IDs gets one message per Net ID, and one message per Net ID is all it
takes to burn the domain's reputation. The two counters here cap that - per client over
an hour, and across the whole instance over a day.

The Discord entry point is not metered here; it is already gated by Discord identity.
"""

from django.conf import settings
from django.http import HttpRequest
from django_ratelimit.core import is_ratelimited

# Shared by both entry points on purpose: they send the same email, so a client that has
# used up its allowance on the registration page has used it up on the payment page too.
PER_IP_GROUP = "registration-email-per-ip"
GLOBAL_GROUP = "registration-email-global"


def get_client_ip(request: HttpRequest) -> str:
    """
    The address to meter this request against.

    In production nginx is the only ingress and proxies to gunicorn over a unix socket,
    so `REMOTE_ADDR` is empty or meaningless and the real client address is whatever
    nginx put in `X-Real-IP` (`include proxy_params` in
    deploy/clubManager.nginx.conf.template). Trusting a client-supplied header would
    normally hand an attacker an unlimited supply of buckets; it is safe here only
    because nginx *overwrites* `X-Real-IP` on every request and nothing else can reach
    gunicorn. If the app is ever exposed directly, or put behind a second proxy, this
    has to be revisited.

    Under `runserver` there is no proxy and no header, so fall back to `REMOTE_ADDR`.
    """
    return request.META.get("HTTP_X_REAL_IP") or request.META.get("REMOTE_ADDR") or "unknown"


def _per_ip_key(_group: str, request: HttpRequest) -> str:
    return get_client_ip(request)


def _global_key(_group: str, _request: HttpRequest) -> str:
    # One bucket for the whole instance.
    return "all"


def registration_throttled(request: HttpRequest) -> bool:
    """
    Count this registration email against both limits and say whether to send it.

    Call immediately before creating a `UserStub`: this increments, so calling it on a
    request that was never going to send mail spends someone else's allowance.

    Counting is `cache.add` followed by `cache.incr` (django-ratelimit does this
    internally). The `incr` half is atomic: the cache backend is
    `common.cache.AtomicDatabaseCache`, which takes a Postgres row lock on the bucket
    before its read-modify-write, so two gunicorn workers racing on the same bucket
    serialize instead of losing an increment. Counts here are exact, not approximate.
    """
    # Both are evaluated before the `or` so that every attempt is counted against both
    # buckets; short-circuiting would let the global tally drift once a client is capped.
    over_per_ip = is_ratelimited(
        request,
        group=PER_IP_GROUP,
        key=_per_ip_key,
        rate=settings.REGISTRATION_EMAIL_RATE_PER_IP,
        increment=True,
    )
    over_global = is_ratelimited(
        request,
        group=GLOBAL_GROUP,
        key=_global_key,
        rate=settings.REGISTRATION_EMAIL_RATE_GLOBAL,
        increment=True,
    )
    return over_per_ip or over_global
