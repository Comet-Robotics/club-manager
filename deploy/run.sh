#!/usr/bin/env bash

set -e

pipenv install --deploy
pipenv run python manage.py migrate
pipenv run python manage.py collectstatic --noinput --clear
pipenv run python manage.py generate_nginx_configuration
sudo systemctl reload nginx
sudo systemctl restart gunicorn
sudo systemctl restart discord_bot