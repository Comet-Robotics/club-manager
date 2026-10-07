#!/usr/bin/env python
"""First-time local dev setup. Idempotent - safe to re-run.

Runs (printing each step as it goes):
  1. GitHub login via gh (skipped if already authenticated)
  2. create .env from .env.example if missing
  3. migrate
  4. setup_cache_table (the shared UNLOGGED cache table)
  5. create a default superuser if none exists yet

Usage:
    mise exec -- pipenv run python scripts/dev_setup.py
    OR
    mise run new-developer-setup

Override the default admin credentials with env vars (dev only):
    DEV_ADMIN_USERNAME, DEV_ADMIN_EMAIL, DEV_ADMIN_PASSWORD
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

# Running as `python scripts/dev_setup.py` puts scripts/ (not the repo root)
# on sys.path, so add the root (parent of this file) for `clubManager`.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "clubManager.settings")

def ensure_env(root: Path) -> None:
    """Create .env from .env.example if it doesn't exist yet."""
    env_file = root / ".env"
    if env_file.exists():
        print("==> .env already exists, skipping")
        return
    example = root / ".env.example"
    if not example.exists():
        print("==> no .env or .env.example found, continuing without one")
        return
    print("==> creating .env from .env.example")
    env_file.write_text(example.read_text())


# NOTE: keep module level side-effect free (imports only). All setup work
# lives in main() so importing this file never touches anything.
import django  # noqa: E402

from django.contrib.auth import get_user_model  # noqa: E402
from django.core.management import call_command  # noqa: E402

ADMIN_USERNAME = os.environ.get("DEV_ADMIN_USERNAME", "adm123456")
ADMIN_EMAIL = os.environ.get("DEV_ADMIN_EMAIL", "adm123456@utdallas.edu")
ADMIN_PASSWORD = os.environ.get("DEV_ADMIN_PASSWORD", "adm123456")


def ensure_github_auth() -> None:
    """Log into the GitHub CLI (HTTPS) unless already authenticated."""
    if _git_helper_has_github_creds():
        print("==> Git already has HTTPS credentials for github.com, skipping")
        return
    if shutil.which("gh") is None:
        print("==> gh (GitHub CLI) not found - install it with: mise install")
        print("    skipping GitHub login (you'll need it to push / open PRs)")
        return
    if subprocess.run(["gh", "auth", "status"], capture_output=True).returncode == 0:
        print("==> already logged into GitHub, skipping")
        return
    print("==> GitHub login")
    print("    You need a free GitHub account (https://github.com/signup).")
    if not sys.stdin.isatty():
        print("    No terminal here, so run `mise exec -- gh auth login` yourself to finish logging in.")
        return
    print("    I'm opening a browser window - approve the login there, then come back here.")
    print("    When it asks about authenticating Git, say yes so pushes work too.")
    subprocess.run(
        ["gh", "auth", "login", "--hostname", "github.com", "--git-protocol", "https", "--web"]
    )


def _git_helper_has_github_creds() -> bool:
    """True if git's credential helper already has github.com HTTPS creds.

    Asks the helper non-interactively (prompting disabled, so this can never
    hang waiting for input) - covers auth set up outside the gh CLI.
    """
    try:
        env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
        probe = subprocess.run(
            ["git", "credential", "fill"],
            input="protocol=https\nhost=github.com\n\n",
            capture_output=True,
            text=True,
            env=env,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return (
        probe.returncode == 0
        and "username=" in probe.stdout
        and "password=" in probe.stdout
    )


def main() -> None:
    ensure_github_auth()

    # Before Django loads settings, so a just-created .env applies to this run.
    ensure_env(ROOT)

    django.setup()

    print("==> migrate")
    call_command("migrate", interactive=False)

    print("==> setup_cache_table")
    call_command("setup_cache_table")

    user_model = get_user_model()
    if user_model.objects.filter(username=ADMIN_USERNAME).exists():
        print(f"==> user '{ADMIN_USERNAME}' already exists, skipping superuser creation")
    else:
        print(f"==> creating superuser '{ADMIN_USERNAME}'")
        user_model.objects.create_superuser(
            username=ADMIN_USERNAME,
            email=ADMIN_EMAIL,
            password=ADMIN_PASSWORD,
        )

    print("\nDone. Log in with:")
    print(f"  username: {ADMIN_USERNAME}")
    print(f"  password: {ADMIN_PASSWORD}")


if __name__ == "__main__":
    sys.exit(main())
