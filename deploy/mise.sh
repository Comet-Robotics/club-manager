#!/usr/bin/env bash

MISE_SYSTEM_PATH="/usr/local/bin/mise"

ensure_mise() {
  if MISE="$(command -v mise 2>/dev/null)"; then
    return
  fi

  echo "mise was not found; installing it to $MISE_SYSTEM_PATH ..."
  if ! curl -fsSL https://mise.run | MISE_INSTALL_PATH="$MISE_SYSTEM_PATH" sh; then
    echo "ERROR: could not install mise from https://mise.run." >&2
    echo "Install it by hand (see https://mise.jdx.dev/getting-started.html) and re-run this script." >&2
    exit 1
  fi
  MISE="$MISE_SYSTEM_PATH"
}

install_toolchain() {
  "$MISE" trust
  "$MISE" install
}

mise_exec() {
  "$MISE" exec -- "$@"
}

python_bin() {
  echo "$("$MISE" where python)/bin/python"
}
