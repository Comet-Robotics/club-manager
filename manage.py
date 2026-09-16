#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""

import os
import sys

# Keep in sync with [requires] python_version in the Pipfile. Django 6.1 dropped support for
# anything older, so without this the failure surfaces as a confusing "couldn't import Django".
REQUIRED_PYTHON = (3, 12)


def main():
    """Run administrative tasks."""
    if sys.version_info < REQUIRED_PYTHON:
        required = ".".join(str(part) for part in REQUIRED_PYTHON)
        current = ".".join(str(part) for part in sys.version_info[:3])
        sys.exit(
            f"Club Manager requires Python {required} or newer, but this is Python {current}.\n"
            "Django 6.1 dropped support for older versions. Install the required version (see the\n"
            ".python-version file), then recreate the virtualenv with: pipenv --rm && pipenv install --dev"
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
