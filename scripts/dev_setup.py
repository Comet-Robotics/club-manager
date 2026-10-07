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

from dotenv import dotenv_values

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


# pgserver = lifecycle management (initdb-if-missing, socket/port handling,
# refcounted shutdown) but its own wheels don't cover every platform we develop
# on, and the version it ships drifts from production. So: install the fork's
# pure-Python manager (no binaries), then point it at the PostgreSQL that mise
# installed. pgserver discovers binaries by scanning site-packages for
# `pgserver_binaries/pg*/bin`, so a symlink (junction on Windows) into mise's
# install directory is all it takes - no patching, no vendoring.
POSTGRES_VERSION = "14"  # match production; see README
FORK_PGSERVER_WHEEL = (
    "https://github.com/alexandre-fundcraft/pgserver/releases/download/latest/pgserver-0.3.0-py3-none-any.whl"
)


def _effective_dev_pgdata() -> str:
    return os.environ.get("DEV_PGDATA") or dotenv_values(ROOT / ".env").get("DEV_PGDATA") or ""


def _pgserver_usable() -> bool:
    """True if pgserver is installed *with* working Postgres binaries.

    Importing pgserver raises AttributeError when it finds no binaries, since
    it resolves them at import time - hence catching that too.
    """
    try:
        import pgserver  # noqa: F401
        from pgserver._commands import POSTGRES_BIN_PATH
    except (ImportError, AttributeError):
        return False
    return POSTGRES_BIN_PATH is not None and (POSTGRES_BIN_PATH / "pg_ctl").exists()


def _mise_postgres_dir() -> Path | None:
    """Absolute path to the PostgreSQL install mise manages, if there is one."""
    if shutil.which("mise") is None:
        return None
    result = subprocess.run(
        ["mise", "where", f"postgres@{POSTGRES_VERSION}"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    path = Path(result.stdout.strip())
    return path if (path / "bin" / "pg_ctl").exists() else None


def _link_postgres_binaries(pg_dir: Path) -> None:
    """Expose mise's PostgreSQL where pgserver looks for it.

    Symlinks need admin or Developer Mode on Windows, so use a directory
    junction there - it needs neither.
    """
    import site

    try:
        site_dir = Path(site.getsitepackages()[0])
    except (ImportError, IndexError):
        return
    link = site_dir / "pgserver_binaries" / f"pg{POSTGRES_VERSION}"
    if link.exists():
        return
    link.parent.mkdir(parents=True, exist_ok=True)
    print(f"==> linking mise's PostgreSQL {POSTGRES_VERSION} into pgserver")
    if sys.platform == "win32":
        # mklink /J takes (link, target) and needs no elevation.
        made = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(pg_dir)], capture_output=True, text=True
        ).returncode == 0
        if not made:
            print("    junction failed, copying the binaries instead")
            shutil.copytree(pg_dir, link, symlinks=True)
    else:
        link.symlink_to(pg_dir, target_is_directory=True)


def ensure_pgserver() -> None:
    """Install pgserver on demand if the dev flow needs it and it's missing.

    Kept out of the Pipfile: the binary wheels don't exist for every platform
    we develop on, which would break `pipenv install` there. Installed here
    instead, and only when DEV_PGDATA asks for it. If that fails, say so
    plainly and point at system Postgres.
    """
    if not _effective_dev_pgdata():
        return
    if _pgserver_usable():
        print("==> pgserver already installed, skipping")
        return

    if shutil.which("mise") is None:
        raise SystemExit(
            "dev_setup: 'mise' not found, so I can't install PostgreSQL. Run this "
            "via `mise run new-developer-setup`, or install mise first."
        )

    print(f"==> installing pgserver + PostgreSQL {POSTGRES_VERSION} (one-time, for the local dev database)")
    if subprocess.run(["mise", "install", f"postgres@{POSTGRES_VERSION}"]).returncode != 0:
        raise SystemExit(f"dev_setup: `mise install postgres@{POSTGRES_VERSION}` failed.")

    pg_dir = _mise_postgres_dir()
    if pg_dir is None:
        raise SystemExit(
            f"dev_setup: mise installed postgres@{POSTGRES_VERSION} but I can't find its "
            "binaries. Use system Postgres instead, then comment out DEV_PGDATA and set "
            "the DB_* variables in .env."
        )

    install = subprocess.run([sys.executable, "-m", "pip", "install", FORK_PGSERVER_WHEEL])
    if install.returncode != 0:
        raise SystemExit("dev_setup: could not install the pgserver package.")

    _link_postgres_binaries(pg_dir)

    if not _pgserver_usable():
        raise SystemExit(
            "dev_setup: pgserver installed but still can't see the PostgreSQL binaries. "
            "Use system Postgres instead: comment out DEV_PGDATA and set DB_* in .env."
        )
    print(f"==> pgserver ready, using PostgreSQL {POSTGRES_VERSION} from mise")


def main() -> None:
    ensure_github_auth()

    # Before Django loads settings, so a just-created .env applies to this run.
    ensure_env(ROOT)
    ensure_pgserver()

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
