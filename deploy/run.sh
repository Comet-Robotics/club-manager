#!/usr/bin/env bash

set -e

pipenv install --deploy
pipenv run python manage.py migrate
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
