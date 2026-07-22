#!/usr/bin/env bash
# Eagle Eye uninstaller. Removes the app, LaunchAgent, and nvim plugin.
# Your captured data in ~/Documents/EagleEye is kept unless
# you pass --purge.
#
#   scripts/uninstall.sh            # remove app + autostart + nvim plugin
#   scripts/uninstall.sh --purge    # also delete all captured data
set -euo pipefail

PURGE=0
[ "${1:-}" = "--purge" ] && PURGE=1

echo "==> stopping + removing LaunchAgent"
PLIST="$HOME/Library/LaunchAgents/com.eagleeye.agent.plist"
launchctl unload "$PLIST" 2>/dev/null || true
rm -f "$PLIST"

echo "==> removing app"
rm -rf "/Applications/EagleEye.app"
pkill -f "eagleeye" 2>/dev/null || true

echo "==> removing nvim plugin"
rm -f "$HOME/.config/nvim/lua/eagleeye.lua"
INIT="$HOME/.config/nvim/init.lua"
[ -f "$INIT" ] && sed -i '' '/require("eagleeye")/d; /Eagle Eye keystroke logger/d' "$INIT" 2>/dev/null || true

if [ "$PURGE" = "1" ]; then
  echo "==> purging data"
  rm -rf "$HOME/Documents/EagleEye"
  rm -rf "$HOME/.config/eagleeye"
  echo "    all data deleted"
else
  echo "Data kept: ~/Documents/EagleEye  (use --purge to delete)"
fi

echo "Done."
