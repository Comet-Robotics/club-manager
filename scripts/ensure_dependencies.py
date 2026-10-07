#!/usr/bin/env python
"""Install the project's Python dependencies, re-locking if the lockfile doesn't fit.

Our committed Pipfile.lock is resolved on macOS. pipenv applies dependency
markers from the Pipfile rather than from an existing lock, so a macOS lock
tells Windows to build `uvloop`, which doesn't support Windows and fails. The
lock records nothing about which platform it was resolved for, so there's no
way to detect that up front - we just try, and on failure re-resolve the lock
for this machine and retry once.

Runs as the first step of `mise run new-developer-setup`, before dev_setup.py,
which needs the virtualenv to already exist. Takes an optional argument: the
interpreter to build the virtualenv with, defaulting to our pinned version.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def pinned_python_version() -> str:
    """The exact Python version mise installs for us - see .python-version."""
    return (ROOT / ".python-version").read_text().strip()


def pipenv(*args: str) -> int:
    return subprocess.run(["pipenv", *args], cwd=ROOT).returncode


def main(argv: list[str]) -> int:
    # Callers on a platform where the pinned interpreter can't install our
    # dependencies (Windows on ARM needs an x86_64 build) pass the interpreter
    # to use explicitly.
    version = argv[1] if len(argv) > 1 else pinned_python_version()

    if pipenv("install", "--dev", "--python", version) == 0:
        return 0

    print(
        "\n==> install failed, which usually means Pipfile.lock was resolved on a "
        "different platform.\n==> re-resolving it for this machine and retrying..."
    )
    if pipenv("lock") != 0:
        print("==> `pipenv lock` failed, see the error above.")
        return 1
    if pipenv("install", "--dev", "--python", version) == 0:
        print(
            "\n==> done. Pipfile.lock is now resolved for this machine - it will show "
            "as modified\n    in `git status`. Don't commit it, or everyone else "
            "inherits a lockfile shaped for your OS."
        )
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
