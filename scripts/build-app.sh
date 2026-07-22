#!/usr/bin/env bash
# Build a real "EagleEye.app" with PyInstaller and install it to /Applications.
#
# PyInstaller embeds the Python interpreter *in-process*, so the bundle's
# executable stays named "EagleEye" — which is what macOS TCC keys on. That's
# why Screen Recording / Accessibility then list it as "EagleEye" (not
# "python3.9"), and the grant is stable across restarts.
#
# (py2app is the more traditional macOS bundler but is currently broken on
# macOS 15 with the system Python 3.9 toolchain — it builds for a 10.9 target
# and dyld rejects the 15.x universal2 wheels.)
#
#   scripts/build-app.sh             # build dist/EagleEye.app only
#   scripts/build-app.sh --install   # build + install to /Applications
set -euo pipefail

INSTALL=0
[ "${1:-}" = "--install" ] && INSTALL=1

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$ROOT/.venv/bin/python"
APP_SRC="$ROOT/dist/EagleEye.app"
APP_DST="/Applications/EagleEye.app"

[ -x "$PY" ] || { echo "venv missing at $PY — run scripts/install.sh first"; exit 1; }
export PIP_USER=0
"$PY" -c "import PyInstaller" 2>/dev/null || "$ROOT/.venv/bin/pip" install -q pyinstaller

echo "==> building EagleEye.app (PyInstaller)"
cd "$ROOT"
rm -rf build dist EagleEye.spec
"$ROOT/.venv/bin/pyinstaller" --noconfirm --clean --windowed --name EagleEye \
  --osx-bundle-identifier com.eagleeye.agent \
  --collect-all rumps --collect-all pynput --collect-all PIL \
  --collect-submodules Quartz --collect-submodules AppKit \
  --collect-submodules Foundation --collect-submodules ApplicationServices \
  --add-data "eagleeye/analysis/ANALYZE.template.md:eagleeye/analysis" \
  --add-data "eagleeye/analysis/ledger.template.md:eagleeye/analysis" \
  eagleeye_launch.py

echo "==> marking as a menu-bar agent (LSUIElement)"
/usr/libexec/PlistBuddy -c "Add :LSUIElement bool true" "$APP_SRC/Contents/Info.plist" \
  2>/dev/null || /usr/libexec/PlistBuddy -c "Set :LSUIElement true" "$APP_SRC/Contents/Info.plist"

echo "==> ad-hoc code-signing (stable TCC identity)"
codesign --force --deep -s - "$APP_SRC"

if [ "$INSTALL" -eq 0 ]; then
  echo "Done. $APP_SRC built (not installed)."
  exit 0
fi

echo "==> installing to /Applications"
rm -rf "$APP_DST"
cp -R "$APP_SRC" "$APP_DST"

echo "Done. $APP_DST built + installed."
echo "Point the LaunchAgent at it:  scripts/install-agent.sh --app"
echo "Then grant Screen Recording + Accessibility to EagleEye."
