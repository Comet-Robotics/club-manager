"""
Data-migration helpers for normalizing stored usernames.

Kept out of the migration file so they can be imported and tested directly - a migration
module whose name starts with a digit is awkward to import, and the collision check is worth
having real tests around.

The canonical form is ``strip().lower()`` (see ``common.utils.normalize_username``). In SQL
that is ``LOWER(BTRIM(username))``: trim whitespace, then lowercase. The collision check,
the rewrite predicate, the rewrite expression, and the unique index must all use this same
expression, otherwise rows can pass the guard but still violate the index (or vice versa).
"""

from django.db.models import Count, Func


def _canonical_username():
    """SQL expression for the canonical username: ``LOWER(BTRIM(username))``."""
    return Func(Func("username", function="BTRIM"), function="LOWER")


def find_case_collisions(User):
    """
    Return the canonical usernames that more than one account currently claims.

    ``auth_user`` already has a plain unique constraint on ``username``, so this only finds
    rows that differ by case and/or surrounding whitespace. Merging those would pick a winner
    arbitrarily and silently reassign one person's payments, profile, and Discord link to the
    other account, so the migration refuses rather than guessing. See issue #72.
    """
    canonical = _canonical_username()
    return list(
        User.objects.annotate(canonical_username=canonical)
        .values("canonical_username")
        .annotate(n=Count("id"))
        .filter(n__gt=1)
        .values_list("canonical_username", flat=True)
    )


def lowercase_usernames(User):
    """
    Rewrite every non-canonical username in one UPDATE.

    ``queryset.update`` bypasses the pre_save signal, so the function call has to be part of
    the statement rather than relying on the handler in ``core.signals.handlers``.
    """
    canonical = _canonical_username()
    return User.objects.exclude(username=canonical).update(username=canonical)
