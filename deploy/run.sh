#!/usr/bin/env bash

set -e

deploy_started_at=$SECONDS

# Reads a single value out of .env. The file uses `KEY = 'value'` spacing, which bash
# cannot source, so it goes through python-dotenv the same way MEDIA_ROOT does below.
read_env_var() {
  pipenv run python -c \
    'import os, sys; from dotenv import load_dotenv; load_dotenv(); print(os.getenv(sys.argv[1], ""))' \
    "$1" 2>/dev/null | tail -n 1
}

# Telling Sentry about a release is what turns a stack trace into "this broke in the
# commit that shipped 20 minutes ago". Entirely optional: an instance without a Sentry
# auth token, or without sentry-cli installed, deploys exactly as it did before, and a
# Sentry outage is never allowed to fail a deploy.
SENTRY_AUTH_TOKEN="$(read_env_var SENTRY_AUTH_TOKEN)"
SENTRY_ORG="$(read_env_var SENTRY_ORG)"
SENTRY_PROJECT="$(read_env_var SENTRY_PROJECT)"
SENTRY_ENVIRONMENT="$(read_env_var SENTRY_ENVIRONMENT)"
# Defaults mirror DEFAULT_SENTRY_DSN in clubManager/observability.py: an instance that
# hasn't pointed itself elsewhere reports to Comet Robotics' project.
SENTRY_ORG="${SENTRY_ORG:-comet-robotics}"
SENTRY_PROJECT="${SENTRY_PROJECT:-club-manager}"
SENTRY_ENVIRONMENT="${SENTRY_ENVIRONMENT:-production}"
# Taken from git rather than `sentry-cli releases propose-version` so that it cannot
# disagree with what the SDK reports: with no SENTRY_RELEASE set, the SDK auto-detects
# the release as this same full commit SHA, read from the repo the services run out of.
SENTRY_RELEASE="$(git rev-parse HEAD)"

sentry_releases_enabled=1
if [[ -z "$SENTRY_AUTH_TOKEN" ]]; then
  echo "Skipping Sentry release registration: SENTRY_AUTH_TOKEN is not set in .env."
  sentry_releases_enabled=0
elif ! command -v sentry-cli >/dev/null 2>&1; then
  echo "Skipping Sentry release registration: sentry-cli is not installed (see README)."
  sentry_releases_enabled=0
fi

if [[ "$sentry_releases_enabled" == 1 ]]; then
  export SENTRY_AUTH_TOKEN SENTRY_ORG SENTRY_PROJECT
  # --ignore-missing: set-commits otherwise fails outright when the previous release's
  # commit isn't in this checkout's history, which happens after a force-push or on a
  # shallow clone. Losing the commit range is not a reason to fail a deploy.
  if sentry-cli releases new "$SENTRY_RELEASE" \
    && sentry-cli releases set-commits "$SENTRY_RELEASE" --auto --ignore-missing \
    && sentry-cli releases finalize "$SENTRY_RELEASE"; then
    echo "Registered Sentry release $SENTRY_RELEASE."
  else
    echo "WARNING: registering the Sentry release failed. Continuing with the deploy; errors will" >&2
    echo "         still be tagged with the release, just without commit association." >&2
    sentry_releases_enabled=0
  fi
fi

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

# Recorded last, once the services are actually back up, so the timestamp in Sentry marks
# when this code started serving rather than when the deploy began. The release itself is
# already registered above, so a failure here costs only the deploy marker.
if [[ "$sentry_releases_enabled" == 1 ]]; then
  if sentry-cli deploys new --release "$SENTRY_RELEASE" -e "$SENTRY_ENVIRONMENT" \
    -t "$((SECONDS - deploy_started_at))"; then
    echo "Recorded Sentry deploy of $SENTRY_RELEASE to $SENTRY_ENVIRONMENT."
  else
    echo "WARNING: recording the Sentry deploy failed; the release itself is registered." >&2
  fi
fi
