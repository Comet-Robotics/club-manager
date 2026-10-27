from uuid import uuid4

from django.db import migrations, models


def backup_and_deduplicate(apps, schema_editor):
    attendance = apps.get_model("events", "Attendance")
    connection = schema_editor.connection
    quote = connection.ops.quote_name
    table = quote(attendance._meta.db_table)
    backup_name = f"events_attendance_backup_{uuid4().hex}"

    with connection.cursor() as cursor:
        # Hold the snapshot and cleanup together with the constraint on PostgreSQL.
        if connection.vendor == "postgresql":
            cursor.execute(f"LOCK TABLE {table} IN ACCESS EXCLUSIVE MODE")
        cursor.execute(f"CREATE TABLE {quote(backup_name)} AS SELECT * FROM {table}")
        print(f"Attendance backup created: {backup_name}")
        cursor.execute(
            f"""
            DELETE FROM {table}
            WHERE id IN (
                SELECT id FROM (
                    SELECT id, ROW_NUMBER() OVER (
                        PARTITION BY event_id, user_id ORDER BY timestamp, id
                    ) AS duplicate_number
                    FROM {table}
                    WHERE user_id IS NOT NULL
                ) AS ranked_attendance
                WHERE duplicate_number > 1
            )
            """
        )


class Migration(migrations.Migration):
    dependencies = [("events", "0029_alter_attendance_sign_in_method")]

    operations = [
        migrations.RunPython(backup_and_deduplicate, reverse_code=migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="attendance",
            constraint=models.UniqueConstraint(fields=("event", "user"), name="unique_attendance_per_event_user"),
        ),
    ]
