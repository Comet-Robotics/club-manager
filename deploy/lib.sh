#!/usr/bin/env bash
# Helpers shared by init.sh and run.sh. Sourced, never executed directly.

DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$DEPLOY_DIR")"
ENV_FILE="$REPO_DIR/.env"

# Reads one value out of .env. The file uses `KEY = 'value'` spacing, which bash cannot
# source, and this deliberately avoids python-dotenv: init.sh runs before the virtualenv
# exists, and run.sh needs these values before `pipenv install`. The tradeoff is that
# dotenv's ${VAR} interpolation is not expanded, so use this only for plain values --
# every SENTRY_* setting is one.
read_env_var() {
  [[ -f "$ENV_FILE" ]] || return 0
  sed -n "s/^[[:space:]]*$1[[:space:]]*=[[:space:]]*//p" "$ENV_FILE" \
    | head -n 1 \
    | sed -e "s/^['\"]//" -e "s/['\"][[:space:]]*\$//" -e "s/[[:space:]]*\$//"
}

# Mirrors strtobool() in clubManager/settings.py so a value means the same thing whether
# bash or Django reads it.
is_truthy() {
  case "$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')" in
    y | yes | t | true | on | 1) return 0 ;;
    *) return 1 ;;
  esac
}

# Whether this instance should have sentry-cli installed and kept around.
#
# Inferred from SENTRY_AUTH_TOKEN rather than gated behind a hostname check: an instance
# that has a release token is an instance that wants releases registered, which is an
# instance that needs the CLI. Comet Robotics' production deployment has the token, so it
# always gets the CLI; a club running its own copy sets no token and is left alone.
# SENTRY_CLI_INSTALL forces the decision either way when that inference is wrong.
sentry_cli_wanted() {
  local override
  override="$(read_env_var SENTRY_CLI_INSTALL)"
  if [[ -n "$override" ]]; then
    is_truthy "$override"
    return
  fi

  [[ -n "$(read_env_var SENTRY_AUTH_TOKEN)" ]]
}

# Installs sentry-cli if this instance wants it and it isn't already there, then checks
# the token actually works. Idempotent: a no-op on every deploy after the first.
#
# Returns 0 when sentry-cli is present and usable, non-zero otherwise. Callers treat a
# non-zero return as "skip the Sentry steps", never as a reason to fail the deploy.
ensure_sentry_cli() {
  if ! sentry_cli_wanted; then
    echo "Sentry CLI: not managed here (no SENTRY_AUTH_TOKEN in .env, and SENTRY_CLI_INSTALL is unset)."
    return 1
  fi

  if command -v sentry-cli >/dev/null 2>&1; then
    return 0
  fi

  echo "Sentry CLI: not installed, installing it now (one time)."
  # The official installer, which drops a binary in /usr/local/bin and asks sudo for it.
  # Pin it with SENTRY_CLI_VERSION in .env if an unattended deploy shouldn't track latest.
  local version
  version="$(read_env_var SENTRY_CLI_VERSION)"
  # Tolerated rather than checked: whether the binary ended up on PATH is the real
  # success criterion, and testing that directly avoids depending on `set -e` being
  # suspended for this function's body.
  if [[ -n "$version" ]]; then
    curl -sL https://sentry.io/get-cli/ | SENTRY_CLI_VERSION="$version" sh || true
  else
    curl -sL https://sentry.io/get-cli/ | sh || true
  fi

  if ! command -v sentry-cli >/dev/null 2>&1; then
    echo "WARNING: installing sentry-cli failed. Releases won't be registered on this deploy." >&2
    echo "         Install it by hand and the next deploy will pick it up:" >&2
    echo "         curl -sL https://sentry.io/get-cli/ | sh" >&2
    return 1
  fi

  echo "Sentry CLI: installed $(sentry-cli --version 2>/dev/null || echo 'unknown version')."

  # Only on a fresh install, so a bad or expired token is reported once at setup time
  # rather than costing a network round trip on every deploy afterwards.
  local token org
  token="$(read_env_var SENTRY_AUTH_TOKEN)"
  org="$(read_env_var SENTRY_ORG)"
  if [[ -n "$token" ]]; then
    if SENTRY_AUTH_TOKEN="$token" SENTRY_ORG="${org:-comet-robotics}" sentry-cli info >/dev/null 2>&1; then
      echo "Sentry CLI: authenticated."
    else
      echo "WARNING: sentry-cli is installed but SENTRY_AUTH_TOKEN was rejected. Check that the" >&2
      echo "         token is valid and has the project:releases scope. The deploy continues." >&2
      return 1
    fi
  fi

  return 0
}
