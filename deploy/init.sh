#!/usr/bin/env bash
# First-time setup for a deployment host: check the prerequisites mise can't provide, install
# the ones it can, and register the systemd/nginx units. Safe to re-run.

set -e

BASE_PATH="$(cd "$(dirname "${BASH_SOURCE:-$0}")" && pwd)"
# shellcheck source=deploy/mise.sh
source "$BASE_PATH/mise.sh"
# mise resolves its config from the working directory, so run from the repo root regardless of
# where this script was invoked from.
cd "$BASE_PATH/.."

# Things mise deliberately does not manage: these are long-running system services that belong
# to the distro, not to this project's toolchain. Check for them up front rather than failing
# halfway through with a missing binary.
missing=()
for cmd in curl sudo nginx psql systemctl; do
  command -v "$cmd" >/dev/null 2>&1 || missing+=("$cmd")
done
if [[ ${#missing[@]} -gt 0 ]]; then
  echo "ERROR: missing system prerequisites: ${missing[*]}" >&2
  echo "On a debian-based host: apt install curl sudo nginx postgresql" >&2
  echo "Nothing has been changed on this host." >&2
  exit 1
fi

# Python and pipenv, on the other hand, are ours. mise installs the exact versions that
# .python-version and mise.toml name, so the host needs no manual interpreter setup and no pyenv.
ensure_mise
install_toolchain

# The systemd units invoke mise by absolute path, because a system unit's PATH does not include
# a user's ~/.local/bin. Make sure that path resolves even if mise was installed elsewhere.
if [[ "$MISE" != "$MISE_SYSTEM_PATH" ]]; then
  echo "Linking $MISE_SYSTEM_PATH -> $MISE so the systemd units can find mise."
  sudo ln -sfn "$MISE" "$MISE_SYSTEM_PATH"
fi

# -f/-n so a re-run replaces the existing links instead of erroring out.
for unit in gunicorn.service gunicorn.socket discord_bot.service \
            post_office_queue.service post_office_queue.timer \
            post_office_cleanup.service post_office_cleanup.timer; do
  sudo ln -sfn "$BASE_PATH/$unit" "/etc/systemd/system/$unit"
done
sudo ln -sfn "$BASE_PATH/clubManager.nginx.conf" /etc/nginx/sites-available/clubManager
sudo ln -sfn /etc/nginx/sites-available/clubManager /etc/nginx/sites-enabled/clubManager

sudo systemctl enable discord_bot.service
sudo systemctl enable gunicorn.socket
sudo systemctl enable gunicorn.service
# The timers are enabled, not the oneshot services they trigger.
sudo systemctl enable post_office_queue.timer
sudo systemctl enable post_office_cleanup.timer

sudo rm -f /etc/nginx/sites-enabled/default
sudo systemctl daemon-reload
