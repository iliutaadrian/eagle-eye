#!/usr/bin/env bash
# Eagle Eye dev setup: venv, dependencies (editable install), nvim plugin, config.
#
#   scripts/install.sh
#
# Then either run it in the foreground:
#   .venv/bin/python -m eagleeye run
# or install the production menu-bar app (autostart at login, no terminal):
#   scripts/build-app.sh            # build + install /Applications/EagleEye.app
#   scripts/install-agent.sh --app  # register the login LaunchAgent
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${PYTHON:-python3}"

echo "==> venv + dependencies"
[ -d "$ROOT/.venv" ] || "$PY" -m venv "$ROOT/.venv"
PIP_USER=0 "$ROOT/.venv/bin/pip" install -q --upgrade pip
# editable install pulls runtime + dev deps straight from setup.py
PIP_USER=0 "$ROOT/.venv/bin/pip" install -q -e "$ROOT[dev]"

echo "==> config"
CFG="$HOME/.config/eagleeye/config.toml"
if [ ! -f "$CFG" ]; then
  mkdir -p "$(dirname "$CFG")"
  cp "$ROOT/config.example.toml" "$CFG"
  echo "    seeded $CFG"
else
  echo "    kept existing $CFG"
fi

echo "==> nvim plugin (mode-aware logging)"
"$ROOT/editor/nvim/install.sh" | sed 's/^/    /'

echo
echo "Done."
echo "Dev run:       $ROOT/.venv/bin/python -m eagleeye run"
echo "Production app: scripts/build-app.sh && scripts/install-agent.sh --app"
