"""
Backfill usernames to lowercase and enforce case-insensitive uniqueness at the database level.

Usernames are Net IDs, which are case-insensitive in practice, but ``auth_user.username`` was
compared exactly. That let two accounts coexist as ``abc000000`` and ``ABC000000`` while
``/link`` and ``/pay`` only ever looked up the lowercase form, so the all-caps one was
invisible (issue #72).

The pre_save signal keeps new ORM writes canonical, but signals are bypassed by ``bulk_create``
and ``queryset.update``. The functional unique index is what makes case-insensitivity a
property of the schema rather than a convention. Together they mean only one casing can exist,
so existing ``=`` lookups stay correct without every call site changing.
"""

from django.db import migrations

from common.username_normalization import find_case_collisions, lowercase_usernames


def assert_no_case_collisions(apps, schema_editor):
    collisions = find_case_collisions(apps.get_model("auth", "User"))
    if collisions:
        raise RuntimeError(
            "Cannot normalize usernames: the values below are claimed by more than one "
            "account, differing only by case. Merging them would reassign one person's "
            "payments, profile, and Discord link to the other, so resolve them in Django "
            "admin (rename or delete one account per value) and re-run. Offending values: "
            + ", ".join(sorted(collisions))
        )


def do_lowercase_usernames(apps, schema_editor):
    lowercase_usernames(apps.get_model("auth", "User"))


ADD_LOWERCASE_UNIQUE_INDEX = (
    "CREATE UNIQUE INDEX IF NOT EXISTS auth_user_username_lower_uniq ON auth_user (LOWER(username))"
)
DROP_LOWERCASE_UNIQUE_INDEX = "DROP INDEX IF EXISTS auth_user_username_lower_uniq"


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0029_serversettings_contact_email_and_more"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        # Check before rewriting: adding the index first would fail mid-statement with a bare
        # duplicate-key error that says nothing about which accounts collided.
        migrations.RunPython(assert_no_case_collisions, migrations.RunPython.noop),
        migrations.RunPython(do_lowercase_usernames, migrations.RunPython.noop),
        migrations.RunSQL(ADD_LOWERCASE_UNIQUE_INDEX, DROP_LOWERCASE_UNIQUE_INDEX),
    ]
