#!/usr/bin/env bash

set -e

pipenv install --deploy
pipenv run python manage.py migrate
# Creates the database cache table and marks it UNLOGGED. Both steps are no-ops once
# done, so this is safe to run on every deploy.
pipenv run python manage.py setup_cache_table
pipenv run python manage.py collectstatic --noinput --clear
find /var/www/static -type f -exec chmod 644 {} +

MEDIA_ROOT="$(pipenv run python -c 'from clubManager import settings; print(settings.MEDIA_ROOT)' | tail -n 1)"
if [[ "$MEDIA_ROOT" == /root/* ]]; then
  echo "ERROR: MEDIA_ROOT ($MEDIA_ROOT) is under /root, which the nginx worker cannot traverse (mode 0700), so /media/ requests will 403. Set MEDIA_ROOT in .env, e.g. /var/www/media." >&2
  exit 1
fi
mkdir -p "$MEDIA_ROOT"
find "$MEDIA_ROOT" -type d -exec chmod 755 {} +
find "$MEDIA_ROOT" -type f -exec chmod 644 {} +

pipenv run python manage.py generate_nginx_configuration
sudo systemctl reload nginx
sudo systemctl restart gunicorn
sudo systemctl restart discord_bot

# The mail timers were added after the existing deployments were set up by init.sh, so link and
# enable them here rather than requiring a re-run of init.sh. All three steps are no-ops once
# done, so this is safe to run on every deploy.
DEPLOY_PATH="$(cd "$(dirname "${BASH_SOURCE:-$0}")" && pwd)"
for unit in post_office_queue.service post_office_queue.timer \
            post_office_cleanup.service post_office_cleanup.timer; do
  sudo ln -sfn "$DEPLOY_PATH/$unit" "/etc/systemd/system/$unit"
done
sudo systemctl daemon-reload
sudo systemctl enable post_office_queue.timer post_office_cleanup.timer
# Restart rather than start, so a changed timer definition is picked up.
sudo systemctl restart post_office_queue.timer
sudo systemctl restart post_office_cleanup.timer
