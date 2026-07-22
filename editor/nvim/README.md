# Eagle Eye — Neovim plugin

Mode-aware keystroke logger. The OS keylogger sees nvim keys but not the *mode*
(normal/insert/visual). This plugin adds that context, which is the most useful
signal for editing-workflow analysis.

It writes to `~/Documents/EagleEye/nvim-YYYY-MM-DD.log`; the app
tails that file into the database automatically.

## Install

```bash
cp editor/nvim/keylog.lua ~/.config/nvim/lua/eagleeye.lua
```

Then add to your `init.lua`:

```lua
require("eagleeye")
```

(For a Vimscript config: `lua require("eagleeye")` in your `init.vim`.)

The installer script (`scripts/install.sh`) does this for you.

## Uninstall

Remove `require("eagleeye")` from `init.lua` and delete
`~/.config/nvim/lua/eagleeye.lua`.

## Notes

- Log format: `[HH:MM:SS] <mode> <keys>` plus `--- file: <path>` markers.
- Flushes every 3s and on exit, so nothing is lost if nvim is killed.
- Requires Neovim 0.7+ (`vim.on_key`, `vim.fn.keytrans`).
