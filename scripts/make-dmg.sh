#!/usr/bin/env bash
# Package dist/EagleEye.app into a drag-to-Applications .dmg.
#
# Run scripts/build-app.sh first so dist/EagleEye.app exists. This produces
# dist/EagleEye-<version>.dmg, ready to upload to a GitHub Release. Uses only
# the built-in hdiutil (no Homebrew, no signing cert).
#
#   scripts/make-dmg.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP="$ROOT/dist/EagleEye.app"
# read version straight from setup.py (version="X.Y.Z")
VERSION="$(sed -n 's/.*version="\([^"]*\)".*/\1/p' "$ROOT/setup.py" | head -1)"
VOL="EagleEye"
DMG="$ROOT/dist/EagleEye-${VERSION}.dmg"
STAGE="$ROOT/build/dmg"

[ -d "$APP" ] || { echo "$APP missing — run scripts/build-app.sh first"; exit 1; }

echo "==> staging"
rm -rf "$STAGE" "$DMG"
mkdir -p "$STAGE"
cp -R "$APP" "$STAGE/"
# symlink so users drag the app onto /Applications inside the mounted .dmg
ln -s /Applications "$STAGE/Applications"

echo "==> building $DMG"
hdiutil create \
  -volname "$VOL" \
  -srcfolder "$STAGE" \
  -fs HFS+ \
  -format UDZO \
  -ov \
  "$DMG" >/dev/null

rm -rf "$STAGE"
echo "Done. $DMG"
echo "Size: $(du -h "$DMG" | cut -f1)"
echo
echo "Next: upload to a GitHub Release, e.g."
echo "  gh release create v${VERSION} \"$DMG\" --title \"v${VERSION}\" --notes \"...\""
