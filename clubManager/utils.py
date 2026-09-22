"""Small utilities that can be imported before Django initializes."""


def strtobool(val: str) -> bool:
    """Convert a string representation of truth to a boolean.

    True values are ``y``, ``yes``, ``t``, ``true``, ``on``, and ``1``; false
    values are ``n``, ``no``, ``f``, ``false``, ``off``, and ``0``. Raises
    ``ValueError`` when ``val`` is anything else.
    """
    val = val.strip().lower()
    if val in ("y", "yes", "t", "true", "on", "1"):
        return True
    if val in ("n", "no", "f", "false", "off", "0"):
        return False
    raise ValueError(f"invalid truth value {val!r}")
