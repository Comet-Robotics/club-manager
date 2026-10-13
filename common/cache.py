"""
The database cache backend, with an increment that two workers cannot race.
"""

from django.core.cache.backends.db import DatabaseCache
from django.db import connections, router, transaction


class AtomicDatabaseCache(DatabaseCache):
    """
    `DatabaseCache` with a genuinely atomic `incr`.

    Why: Django's `DatabaseCache` never overrides `incr`, so it inherits
    `BaseCache.incr`, which is a read-modify-write in Python - `get` the current value,
    add the delta, `set` the result. Nothing holds the row in between. gunicorn runs
    several worker processes against one Postgres instance, so two workers incrementing
    the same key can both read 7, both write 8, and one increment is simply gone. That
    is the lost update that makes rate-limiting libraries refuse to run on this backend
    (django-ratelimit, for one, flags it as "does not support atomic increment"), and a
    counter that undercounts is exactly the kind of thing a limit must not be built on.

    How: take a Postgres row lock on the cache row first, then do the base class's
    read-modify-write inside the same transaction. `SELECT ... FOR UPDATE` holds the
    lock until commit, so a second worker's `SELECT ... FOR UPDATE` on the same
    `cache_key` blocks until the first worker's new value is committed and then reads
    it. Concurrent increments on one key are serialized; increments on different keys
    lock different rows and do not contend.

    `super().incr()` is deliberately what does the actual work, so Django's own base64
    and pickle decoding, its expiry handling, and its `_base_set` culling logic all keep
    running - on the same connection, inside the locked transaction. `_base_set` opens
    its own `transaction.atomic`, which nests as a savepoint rather than committing
    early.

    Behavior is otherwise the base class's, unchanged:

    - A missing key still raises `ValueError`. `SELECT ... FOR UPDATE` matching no rows
      locks nothing, and `super().incr()` then raises exactly as it would have. An
      expired key is a missing key for this purpose - `get` drops it - so it raises too.
      Callers must `add` before they `incr`. That is the shape rate limiters use - an
      `add` of the initial count followed by an `incr` per request - and it is the
      `incr` half that this class makes safe.
    - `BaseCache.decr` delegates to `incr` with a negated delta, so it is covered by
      this one override and needs none of its own.

    This is still a `BaseDatabaseCache` subclass, so `manage.py createcachetable` finds
    it and creates the table as it would for the stock backend.
    """

    def incr(self, key, delta=1, version=None):
        db = router.db_for_write(self.cache_model_class)
        connection = connections[db]
        quote_name = connection.ops.quote_name
        cache_key_column = quote_name("cache_key")
        locked_key = self.make_and_validate_key(key, version=version)

        with transaction.atomic(using=db):
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT {column} FROM {table} WHERE {column} = %s FOR UPDATE".format(
                        column=cache_key_column,
                        table=quote_name(self._table),
                    ),
                    [locked_key],
                )
                # The row is locked until this transaction commits; the value itself is
                # read back by the base implementation below.
                cursor.fetchone()

            return super().incr(key, delta=delta, version=version)
