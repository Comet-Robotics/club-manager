from django.conf import settings
from django.core.cache import caches
from django.core.cache.backends.db import BaseDatabaseCache
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import connections, router


class Command(BaseCommand):
    help = (
        "Create the database cache table(s) and mark them UNLOGGED. Safe to run on every deploy: "
        "creating an existing table is skipped and re-marking an unlogged table is a no-op."
    )

    def handle(self, *args, **options):
        # Django's own command builds the table with the exact column types the backend
        # expects; we only add the storage tweak it has no option for.
        call_command("createcachetable", verbosity=options["verbosity"], stdout=self.stdout)

        for alias in settings.CACHES:
            cache = caches[alias]
            if not isinstance(cache, BaseDatabaseCache):
                continue

            connection = connections[router.db_for_write(cache.cache_model_class)]
            if connection.vendor != "postgresql":
                self.stdout.write(f"Skipping '{cache._table}': UNLOGGED is a PostgreSQL feature.")
                continue

            # An UNLOGGED table skips the write-ahead log, so cache writes are cheaper and
            # generate no WAL churn. The trade-off is that its contents are truncated after
            # a crash and are not replicated - both fine for a cache, whose contents are
            # by definition reconstructible. Note ALTER ... SET UNLOGGED rewrites the table
            # under an exclusive lock, which is instant for a table this size.
            table = connection.ops.quote_name(cache._table)
            with connection.cursor() as cursor:
                cursor.execute(f"ALTER TABLE {table} SET UNLOGGED")

            self.stdout.write(self.style.SUCCESS(f"Cache table '{cache._table}' is UNLOGGED."))
