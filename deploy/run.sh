#!/usr/bin/env bash

set -e

DEPLOY_PATH="$(cd "$(dirname "${BASH_SOURCE:-$0}")" && pwd)"
# shellcheck source=deploy/mise.sh
source "$DEPLOY_PATH/mise.sh"
cd "$DEPLOY_PATH/.."

ensure_mise
install_toolchain

PYTHON_BIN="$(python_bin)"
REQUIRED_PYTHON="$("$PYTHON_BIN" -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
VENV_PATH="$(mise_exec pipenv --venv 2>/dev/null || true)"
if [[ -n "$VENV_PATH" && -x "$VENV_PATH/bin/python" ]]; then
  VENV_PYTHON="$("$VENV_PATH/bin/python" -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
  if [[ "$VENV_PYTHON" != "$REQUIRED_PYTHON" ]]; then
    echo "Virtualenv is on Python $VENV_PYTHON but $REQUIRED_PYTHON is required; recreating it."
    mise_exec pipenv remove
  fi
fi

mise_exec pipenv install --deploy --python "$PYTHON_BIN"
mise_exec pipenv run python manage.py migrate
# Creates the database cache table and marks it UNLOGGED. Both steps are no-ops once
# done, so this is safe to run on every deploy.
mise_exec pipenv run python manage.py setup_cache_table
mise_exec pipenv run python manage.py collectstatic --noinput --clear
find /var/www/static -type f -exec chmod 644 {} +

MEDIA_ROOT="$(mise_exec pipenv run python -c 'from clubManager import settings; print(settings.MEDIA_ROOT)' | tail -n 1)"
if [[ "$MEDIA_ROOT" == /root/* ]]; then
  echo "ERROR: MEDIA_ROOT ($MEDIA_ROOT) is under /root, which the nginx worker cannot traverse (mode 0700), so /media/ requests will 403. Set MEDIA_ROOT in .env, e.g. /var/www/media." >&2
  exit 1
fi
mkdir -p "$MEDIA_ROOT"
find "$MEDIA_ROOT" -type d -exec chmod 755 {} +
find "$MEDIA_ROOT" -type f -exec chmod 644 {} +

mise_exec pipenv run python manage.py generate_nginx_configuration

# The mail timers were added after the existing deployments were set up by init.sh, so link and
# enable them here rather than requiring a re-run of init.sh. All three steps are no-ops once
# done, so this is safe to run on every deploy.
for unit in post_office_queue.service post_office_queue.timer \
            post_office_cleanup.service post_office_cleanup.timer; do
  sudo ln -sfn "$DEPLOY_PATH/$unit" "/etc/systemd/system/$unit"
done

sudo systemctl daemon-reload
sudo systemctl enable post_office_queue.timer post_office_cleanup.timer

sudo systemctl reload nginx
sudo systemctl restart gunicorn
sudo systemctl restart discord_bot
# Restart rather than start, so a changed timer definition is picked up.
sudo systemctl restart post_office_queue.timer
sudo systemctl restart post_office_cleanup.timer
