#!/usr/bin/env bash

set -e

pipenv install --deploy
pushd frontend
npm install && npm run build
popd
pipenv run python manage.py migrate
pipenv run python manage.py collectstatic --noinput --clear
sudo systemctl restart gunicorn
sudo systemctl restart discord_bot