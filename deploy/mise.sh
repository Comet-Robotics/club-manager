#!/usr/bin/env bash
# Shared helper: guarantee mise exists, then make this host's toolchain match mise.toml.
# Sourced by init.sh and run.sh. Not meant to be run directly.

# systemd units cannot rely on a login shell's PATH, and the default PATH for system units is
# /usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin. /usr/local/bin is the only entry
# in there that a non-distro tool belongs in, so that is where the services look for mise.
# Keep this in sync with ExecStart= in the .service files.
MISE_SYSTEM_PATH="/usr/local/bin/mise"

# Resolve mise, installing it if this host has never had it. Sets $MISE to an absolute path.
ensure_mise() {
  if MISE="$(command -v mise 2>/dev/null)"; then
    return
  fi

  echo "mise was not found; installing it to $MISE_SYSTEM_PATH ..."
  # https://mise.jdx.dev/getting-started.html - MISE_INSTALL_PATH picks the destination rather
  # than the default ~/.local/bin, which systemd would not search.
  if ! curl -fsSL https://mise.run | MISE_INSTALL_PATH="$MISE_SYSTEM_PATH" sh; then
    echo "ERROR: could not install mise from https://mise.run." >&2
    echo "Install it by hand (see https://mise.jdx.dev/getting-started.html) and re-run this script." >&2
    exit 1
  fi
  MISE="$MISE_SYSTEM_PATH"
}

# Install the exact Python from .python-version and the pinned pipenv from mise.toml.
# Both are no-ops once the versions are present, so this is cheap on every deploy.
install_toolchain() {
  # mise refuses to read a config it has not been trusted with when running unattended.
  "$MISE" trust
  "$MISE" install
}

# Run a command with the project's toolchain on PATH. Use this instead of calling pipenv or
# python directly, so a deploy can never pick up whatever interpreter happens to be installed.
mise_exec() {
  "$MISE" exec -- "$@"
}
