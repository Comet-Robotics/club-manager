#!/usr/bin/env bash

set -e

BASE_PATH="$(cd "$(dirname "${BASH_SOURCE:-$0}")" && pwd)"
# shellcheck source=deploy/mise.sh
source "$BASE_PATH/mise.sh"
cd "$BASE_PATH/.."

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

ensure_mise
install_toolchain

link_system_mise

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
