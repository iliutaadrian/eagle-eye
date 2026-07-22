#!/usr/bin/env bash
# Install the Eagle Eye Neovim keystroke-logger plugin.
#
# Copies keylog.lua to ~/.config/nvim/lua/eagleeye.lua and wires
# require("eagleeye") into init.lua. Safe to re-run (idempotent).
#
#   editor/nvim/install.sh
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NVIM="$HOME/.config/nvim"

if [ ! -d "$NVIM" ]; then
  echo "no $NVIM — skipped (Neovim not set up)"
  exit 0
fi

mkdir -p "$NVIM/lua"
cp "$HERE/keylog.lua" "$NVIM/lua/eagleeye.lua"

INIT="$NVIM/init.lua"
if [ -f "$INIT" ] && ! grep -q 'require("eagleeye")' "$INIT"; then
  printf '\n-- Eagle Eye keystroke logger\nrequire("eagleeye")\n' >> "$INIT"
fi

echo "installed nvim plugin to $NVIM/lua/eagleeye.lua"
