#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""

import os
import sys

# Keep in sync with .python-version.
REQUIRED_PYTHON = (3, 12)


def main():
    """Run administrative tasks."""
    if sys.version_info < REQUIRED_PYTHON:
        required = ".".join(str(part) for part in REQUIRED_PYTHON)
        current = ".".join(str(part) for part in sys.version_info[:3])
        sys.exit(
            f"Club Manager requires Python {required} or newer, but this is Python {current}.\n"
            "Django 6.1 dropped support for older versions. `mise install` installs the version\n"
            ".python-version names; then run this through mise, e.g. `mise exec -- pipenv run python\n"
            "manage.py ...`, or activate mise in your shell."
        )

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "clubManager.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
