#!/usr/bin/env sh
# Install Lobesync without requiring an activated Python environment.

set -eu

VERSION="${LOBESYNC_VERSION:-}"
UV_INSTALLER_URL="https://astral.sh/uv/install.sh"

fail() {
    printf '%s\n' "Lobesync installer: $*" >&2
    exit 1
}

case "$(uname -s)" in
    Darwin|Linux) ;;
    *) fail "This script supports macOS and Linux. Use install.ps1 on Windows." ;;
esac

if [ -n "$VERSION" ]; then
    case "$VERSION" in
        *[!0-9A-Za-z._-]*) fail "LOBESYNC_VERSION must be a version such as 1.0.0." ;;
    esac
fi

find_uv() {
    if command -v uv >/dev/null 2>&1; then
        command -v uv
    elif [ -x "$HOME/.local/bin/uv" ]; then
        printf '%s\n' "$HOME/.local/bin/uv"
    fi
}

UV="$(find_uv || true)"
if [ -z "$UV" ]; then
    printf '%s\n' "Installing uv, the isolated Python tool manager..."
    if command -v curl >/dev/null 2>&1; then
        curl -LsSf "$UV_INSTALLER_URL" | sh
    elif command -v wget >/dev/null 2>&1; then
        wget -qO- "$UV_INSTALLER_URL" | sh
    else
        fail "Install curl or wget, then run this installer again."
    fi
    UV="$(find_uv || true)"
fi

[ -n "$UV" ] || fail "uv was installed but could not be found. Open a new terminal and try again."

PACKAGE="lobesync"
DISPLAY_VERSION="the latest release"
if [ -n "$VERSION" ]; then
    PACKAGE="lobesync==$VERSION"
    DISPLAY_VERSION="$VERSION"
fi

printf '%s\n' "Installing Lobesync $DISPLAY_VERSION with Python 3.13..."
"$UV" tool install --python 3.13 "$PACKAGE"
"$UV" tool update-shell

TOOL_BIN="$("$UV" tool dir --bin)"
printf '\n%s\n' "Lobesync $DISPLAY_VERSION is installed."
printf '%s\n' "Open a new terminal, then run: lobesync"
printf '%s\n' "Installed command directory: $TOOL_BIN"
