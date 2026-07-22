#!/usr/bin/env bash
# Build the .app and package the .dmg WITHOUT installing to /Applications.
#
# For testing the real download/install flow yourself: produces
# dist/EagleEye-<version>.dmg and leaves your machine otherwise untouched
# (nothing copied into /Applications, no LaunchAgent).
#
#   scripts/build-dmg.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

"$ROOT/scripts/build-app.sh"
"$ROOT/scripts/make-dmg.sh"
