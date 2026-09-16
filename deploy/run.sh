#!/usr/bin/env bash

set -e

# Django 6.1 requires Python 3.12+, so a deploy onto an older interpreter cannot work.
# pipenv already fails in that case, but its message ("Aborting deploy") doesn't mention
# Python at all, so check up front and say what to actually do about it. The required
# version comes from the Pipfile so there is only one source of truth.
REQUIRED_PYTHON="$(awk '/^\[requires\]/{f=1;next} /^\[/{f=0} f && /python_version/{gsub(/[^0-9.]/,"");print;exit}' Pipfile)"
if [[ -z "$REQUIRED_PYTHON" ]]; then
  echo "ERROR: could not read [requires] python_version from Pipfile." >&2
  exit 1
fi

# An existing virtualenv on the wrong version is the common trap: pipenv reuses it rather
# than rebuilding when python_version changes, so it has to be removed by hand.
CURRENT_PYTHON="$(pipenv run python -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null | tail -n 1)"
if [[ "$CURRENT_PYTHON" =~ ^[0-9]+\.[0-9]+$ && "$CURRENT_PYTHON" != "$REQUIRED_PYTHON" ]]; then
  echo "ERROR: this project's virtualenv is on Python $CURRENT_PYTHON, but Python $REQUIRED_PYTHON is required." >&2
  echo "pipenv will not rebuild it for you. Recreate it, then re-run this script:" >&2
  echo "  pipenv --rm" >&2
  echo "Nothing has been migrated or restarted; the running deployment is untouched." >&2
  exit 1
fi

if ! command -v "python$REQUIRED_PYTHON" >/dev/null 2>&1 &&
  ! pyenv versions --bare 2>/dev/null | grep -q "^$REQUIRED_PYTHON\."; then
  echo "ERROR: Python $REQUIRED_PYTHON is required but no python$REQUIRED_PYTHON was found on this host." >&2
  echo "The required version comes from the Pipfile; Django needs it. Install it first, e.g.:" >&2
  echo "  pyenv install \"\$(pyenv latest -k $REQUIRED_PYTHON)\"" >&2
  echo "  pyenv local \"\$(pyenv latest -k $REQUIRED_PYTHON)\"" >&2
  echo "Nothing has been migrated or restarted; the running deployment is untouched." >&2
  exit 1
fi

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
