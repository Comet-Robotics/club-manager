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
import re
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
    subprocess.run(["gh", "auth", "login", "--hostname", "github.com", "--git-protocol", "https", "--web"])


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
    return probe.returncode == 0 and "username=" in probe.stdout and "password=" in probe.stdout


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


def _env(name: str) -> str:
    """Read a setting from the environment, falling back to .env."""
    return os.environ.get(name) or dotenv_values(ROOT / ".env").get(name) or ""


def _find_pg_bin_dir() -> Path | None:
    """Locate a PostgreSQL install to run the dev database from.

    DEV_PG_BIN_DIR wins when set - that is the escape hatch for platforms mise
    can't supply binaries for (no conda-forge win-arm64 PostgreSQL exists), and
    for anyone who already has PostgreSQL installed. Otherwise use mise's.

    Returns the install *root* (the directory containing bin/), which is what
    pgserver expects to find linked in; accepts either that or its bin
    directory as input.
    """
    override = _env("DEV_PG_BIN_DIR")
    if not override:
        return _mise_postgres_dir()
    path = Path(override).expanduser()
    if (path / "bin" / "pg_ctl").exists():
        return path
    if (path / "pg_ctl").exists():  # given the bin dir; pgserver wants its parent
        return path.parent
    return None


def _pg_major(pg_root: Path) -> str | None:
    """Ask pg_ctl what version it is, e.g. '14' - pgserver reads the version
    from the directory name, so it has to match the binaries we actually link."""
    try:
        out = subprocess.run(
            [str(pg_root / "bin" / "pg_ctl"), "--version"],
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    match = re.search(r"(\d+)(?:\.\d+)?\s*$", out.strip())
    return match.group(1) if match else None


def _remove_link(link: Path) -> None:
    """Delete an existing symlink or Windows junction, if present."""
    if not link.exists() and not link.is_symlink():
        return
    try:
        link.unlink()
    except OSError:
        # Windows junctions need rmdir rather than unlink.
        try:
            link.rmdir()
        except OSError:
            shutil.rmtree(link, ignore_errors=True)


def _link_postgres_binaries(pg_dir: Path) -> None:
    """Expose a PostgreSQL install where pgserver looks for it.

    pgserver scans site-packages for `pgserver_binaries/pg*/bin`. Symlinks need
    admin or Developer Mode on Windows, so use a directory junction there - it
    needs neither.
    """
    import site

    try:
        site_dir = Path(site.getsitepackages()[0])
    except (ImportError, IndexError):
        return

    major = _pg_major(pg_dir)
    if major is None:
        raise SystemExit(
            f"dev_setup: {pg_dir / 'bin' / 'pg_ctl'} didn't report a PostgreSQL "
            "version. Is DEV_PG_BIN_DIR pointing at a PostgreSQL install?"
        )

    link = site_dir / "pgserver_binaries" / f"pg{major}"
    # Replace a stale link - it may point at a different install than we want.
    _remove_link(link)
    link.parent.mkdir(parents=True, exist_ok=True)

    if sys.platform == "win32":
        print(f"==> linking PostgreSQL {major} into pgserver (directory junction)")
        made = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(pg_dir)], capture_output=True, text=True)
        if made.returncode != 0:
            print(f"    junction failed ({made.stdout.strip() or made.stderr.strip()}), copying instead")
            shutil.copytree(pg_dir, link, symlinks=True)
    else:
        print(f"==> linking PostgreSQL {major} into pgserver")
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

    using_override = bool(_env("DEV_PG_BIN_DIR"))

    # With an explicit DEV_PG_BIN_DIR, relink even if pgserver already looks
    # usable - it may be pointed at the wrong PostgreSQL.
    if _pgserver_usable() and not using_override:
        print("==> pgserver already installed, skipping")
        return

    if not using_override:
        if shutil.which("mise") is None:
            raise SystemExit(
                "dev_setup: 'mise' not found, so I can't install PostgreSQL. Run this "
                "via `mise run new-developer-setup`, install mise, or set DEV_PG_BIN_DIR "
                "to an existing PostgreSQL install."
            )
        print(f"==> installing PostgreSQL {POSTGRES_VERSION} via mise (one-time, for the local dev database)")
        if subprocess.run(["mise", "install", f"postgres@{POSTGRES_VERSION}"]).returncode != 0:
            raise SystemExit(
                f"dev_setup: `mise install postgres@{POSTGRES_VERSION}` failed. No "
                "PostgreSQL build exists for this platform via mise (e.g. Windows on "
                "ARM). Install PostgreSQL yourself - on Windows: "
                "`winget install PostgreSQL.PostgreSQL.14` - then set DEV_PG_BIN_DIR "
                "in .env to its bin directory, or comment out DEV_PGDATA and set DB_*."
            )

    pg_dir = _find_pg_bin_dir()
    if pg_dir is None:
        raise SystemExit(
            f"dev_setup: could not find a usable PostgreSQL {POSTGRES_VERSION} install "
            "(looked for pg_ctl). Set DEV_PG_BIN_DIR in .env to an existing PostgreSQL "
            "bin directory, or comment out DEV_PGDATA and set the DB_* variables to use "
            "a server that's already running."
        )

    print("==> installing pgserver (one-time, for the local dev database)")
    install = subprocess.run([sys.executable, "-m", "pip", "install", FORK_PGSERVER_WHEEL])
    if install.returncode != 0:
        raise SystemExit("dev_setup: could not install the pgserver package.")

    _link_postgres_binaries(pg_dir)

    if not _pgserver_usable():
        raise SystemExit(
            f"dev_setup: pgserver installed but still can't use the PostgreSQL binaries "
            f"in {pg_dir}. Check that pg_ctl runs there, or comment out DEV_PGDATA and "
            "set DB_* in .env."
        )
    print(f"==> pgserver ready, running on PostgreSQL {POSTGRES_VERSION} from {pg_dir}")


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
