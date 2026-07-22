# Changelog

## 0.1.0

Initial release.

- Single-process macOS menu-bar tracker (rumps + pynput + pyobjc).
- App-usage sampler: app + window title + browser URL, idle-subtracted.
- Global keystroke logger (app-tagged bursts, modifier decoding).
- Neovim mode-aware keystroke plugin (`editor/nvim/keylog.lua`).
- Screenshots every N seconds, each captioned by headless Claude Code (worker pool).
- SQLite storage (WAL) with a single writer thread.
- Live web dashboard: top apps, keystrokes, nvim modes, screenshot grid with click-to-zoom.
- Menu-bar submenus for model (haiku/sonnet/opus) and screenshot interval (5/10/30s), live + persisted.
- Analysis loop: compile daily timeline → Claude updates the inefficiency ledger.
- CLI: `run | status | dashboard | compile | analyze | migrate`.
- Installer/uninstaller scripts; py2app bundle + LaunchAgent autostart.
