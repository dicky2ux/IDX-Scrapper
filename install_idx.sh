#!/usr/bin/env bash
# Install helper for the `idx` CLI wrapper
# Tries /usr/local/bin first (may require sudo), falls back to ~/.local/bin

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$SCRIPT_DIR/idx"

if [[ ! -f "$SRC" ]]; then
  echo "Error: idx script not found at $SRC"
  exit 1
fi

TARGET_DIR="/usr/local/bin"
INSTALL_PATH="$TARGET_DIR/idx"

if [[ -w "$TARGET_DIR" ]]; then
  echo "Installing to $TARGET_DIR"
  ln -sf "$SRC" "$INSTALL_PATH"
  chmod +x "$INSTALL_PATH"
  echo "Installed idx -> $INSTALL_PATH"
  exit 0
fi

USER_BIN="$HOME/.local/bin"
mkdir -p "$USER_BIN"
INSTALL_PATH="$USER_BIN/idx"
ln -sf "$SRC" "$INSTALL_PATH"
chmod +x "$INSTALL_PATH"
echo "Installed idx -> $INSTALL_PATH"

echo
echo "If $USER_BIN is not in your PATH, add it (example for bash/zsh):"
echo "  export PATH=\"$HOME/.local/bin:\$PATH\""
echo "You can add that line to ~/.profile or ~/.bashrc or ~/.zshrc"
