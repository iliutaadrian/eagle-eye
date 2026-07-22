<h1>Eagle Eye 🦅</h1>

A local-only macOS menu-bar app that watches **your own** workflow so you can find
what to optimize — the shortcuts you're missing, the actions you repeat, the tools
you're overpaying for. Inspired by "watch your screen → summarize → suggest fixes",
but grounded in exact keystroke + app-time data, not just screenshots.

Everything stays on your machine.

## What it captures

| Stream | Detail |
|--------|--------|
| **App time** | which app / window title / browser URL, for how long, idle-subtracted (like ActivityWatch) |
| **Keystrokes** | every key, tagged by focused app, modifiers decoded (`<C-w>`, `<D-t>`), stored as bursts |
| **Neovim** | keys **with mode** (n/i/v/c) via a tiny plugin — context the OS can't see |
| **Screenshots** | every N seconds, each captioned to one line by a cheap model (headless Claude Code); perceptually-identical frames are skipped (no disk, no caption) |

It all lands in one SQLite DB. A built-in analysis loop compiles a daily timeline
and asks Claude to maintain an "inefficiency ledger" with ranked, concrete fixes.

## Install

```bash
git clone https://github.com/iliutaadrian/eagle-eye.git && cd eagle-eye
scripts/install.sh                 # venv + deps + nvim plugin + config
.venv/bin/python -m eagleeye run   # menu-bar app (grant permissions on first run)
```

**Production (autostart at login, no terminal):**

```bash
scripts/build-app.sh               # build + install /Applications/EagleEye.app (PyInstaller)
scripts/install-agent.sh --app     # register the login LaunchAgent
```

Then grant permissions (see [Permissions](#permissions)).

## Use

- Menu bar: Start/Stop, Pause, **Model** (haiku/sonnet/opus), **Screenshot interval**
  (5/10/30s), **Open dashboard**, **Run analysis**.
- Dashboard: `http://127.0.0.1:8899/` — top apps, keystrokes, nvim modes, screenshot
  grid with click-to-zoom.
- CLI:
  ```bash
  .venv/bin/python -m eagleeye status     # today's counts
  .venv/bin/python -m eagleeye dashboard  # live web UI
  .venv/bin/python -m eagleeye analyze    # Claude updates the ledger with fixes
  ```

## Permissions

Granted once in **System Settings → Privacy & Security**:

- **Screen Recording** — for screenshots.
- **Accessibility** — for the global keystroke logger and window titles.
- **Automation** (per browser) — to read the active tab URL.

Grant them to whatever launches the app: the `EagleEye` bundle if you used
`build-app.sh`, otherwise the Python binary. macOS keys permissions to the exact
binary, so a fresh build may need re-granting.

## Config

Optional `~/.config/eagleeye/config.toml` (seeded from
[`config.example.toml`](config.example.toml)). Tunables: screenshot interval /
dedup, caption model, keylog idle gap, browser dialects.

## Neovim plugin

Mode-aware keystroke logging — see [editor/nvim/README.md](editor/nvim/README.md).

## Privacy

This is a keylogger + screen recorder. It records passwords, 2FA, and private text
into a **local** database under `~/Library/Application Support/EagleEye/`. Nothing is
uploaded (the only network call is your local `claude` CLI for captions). The data
dir is git-ignored. See [docs/PERMISSIONS.md](docs/PERMISSIONS.md).

## Layout

```
eagleeye/           Python package (menu bar, capture, storage, analysis)
eagleeye_launch.py  app entry point
editor/nvim/        Neovim mode-aware plugin
scripts/            install.sh · build-app.sh · install-agent.sh · uninstall.sh
setup.py            packaging + dependencies
config.example.toml default config
```

## License

MIT — see [LICENSE](LICENSE).
