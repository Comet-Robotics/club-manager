"""
Data-migration helpers for normalizing stored usernames.

Kept out of the migration file so they can be imported and tested directly - a migration
module whose name starts with a digit is awkward to import, and the collision check is worth
having real tests around.
"""

from django.db.models import Count, Func


def find_case_collisions(User):
    """
    Return the lowercased usernames that more than one account currently claims.

    ``auth_user`` already has a plain unique constraint on ``username``, so this only finds
    rows that differ by case alone. Merging those would pick a winner arbitrarily and silently
    reassign one person's payments, profile, and Discord link to the other account, so the
    migration refuses rather than guessing. See issue #72.
    """
    return list(
        User.objects.annotate(lower_username=Func("username", function="LOWER"))
        .values("lower_username")
        .annotate(n=Count("id"))
        .filter(n__gt=1)
        .values_list("lower_username", flat=True)
    )


def lowercase_usernames(User):
    """
    Rewrite every non-lowercase username in one UPDATE.

    ``queryset.update`` bypasses the pre_save signal, so the function call has to be part of
    the statement rather than relying on the handler in ``core.signals.handlers``.
    """
    return User.objects.filter(username__regex=r".*[A-Z].*").update(username=Func("username", function="LOWER"))
