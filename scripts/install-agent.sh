#!/usr/bin/env bash
# Install Eagle Eye as a login LaunchAgent: a menu-bar app that autostarts at
# login, restarts on crash, needs no open terminal, and shows no Dock icon.
#
# Prefer --app (runs /Applications/EagleEye.app, built by scripts/build-app.sh):
# it gives a stable, named identity so macOS lists it as "EagleEye" in the
# Privacy panes. Without --app it runs the venv python directly (shows as
# python3.9 in those panes) — handy for quick dev iteration.
#
#   scripts/install-agent.sh            # run the venv directly (shows as python3.9 in TCC)
#   scripts/install-agent.sh --app      # run via /Applications/EagleEye.app (shows as EagleEye)
#   scripts/install-agent.sh --uninstall
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$ROOT/.venv/bin/python"
APP="/Applications/EagleEye.app"
LABEL="com.eagleeye.agent"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
LOG_DIR="$HOME/Library/Logs/EagleEye"

if [ "${1:-}" = "--uninstall" ]; then
  launchctl unload "$PLIST" 2>/dev/null || true
  rm -f "$PLIST"
  echo "uninstalled $LABEL (data kept)"
  exit 0
fi

mkdir -p "$HOME/Library/LaunchAgents" "$LOG_DIR"

# --app: launch the named .app bundle so TCC lists it as "EagleEye".
# default: launch the venv python directly.
if [ "${1:-}" = "--app" ]; then
  [ -x "$APP/Contents/MacOS/EagleEye" ] || { echo "$APP missing — run scripts/build-app.sh first"; exit 1; }
  PROGRAM_ARGS="    <string>$APP/Contents/MacOS/EagleEye</string>"
else
  [ -x "$PY" ] || { echo "venv missing at $PY — run scripts/install.sh first"; exit 1; }
  PROGRAM_ARGS="    <string>$PY</string>
    <string>-m</string>
    <string>eagleeye</string>
    <string>run</string>"
fi

cat > "$PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
$PROGRAM_ARGS
  </array>
  <key>WorkingDirectory</key><string>$ROOT</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key><string>$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
  </dict>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><dict><key>Crashed</key><true/></dict>
  <key>ProcessType</key><string>Interactive</string>
  <key>StandardOutPath</key><string>$LOG_DIR/agent.out.log</string>
  <key>StandardErrorPath</key><string>$LOG_DIR/agent.err.log</string>
</dict>
</plist>
PLIST

launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"
echo "loaded $LABEL"
echo "logs: $LOG_DIR/agent.{out,err}.log"
echo
echo "First launch will prompt for Screen Recording + Accessibility."
if [ "${1:-}" = "--app" ]; then
  echo "Grant them to: EagleEye ($APP)"
else
  echo "Grant them to the Python at: $(readlink -f "$PY")"
fi
echo "See README (Permissions)."
