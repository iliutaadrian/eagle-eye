# Analyze Flow (run with Claude Code)

Repeatable daily/weekly workflow-optimization review. Manual: you tell Claude
Code "analyze today" (or a date), and it runs the steps below.

Inspired by the "watch screen -> summarize -> ledger -> suggest" system, but
text-first: keystroke + nvim logs are exact and free; screenshots only fill in
GUI-app context (browser, etc.) that keystrokes can't reveal.

## Inputs (all under ~/keylog/)
- `YYYY-MM-DD.log`       - tmux/shell keystrokes (exact)
- `nvim-YYYY-MM-DD.log`  - nvim keys with mode
- `screens/YYYY-MM-DD/`  - screenshots (JPEG)

## Steps Claude Code performs

1. `python3 compile.py [YYYY-MM-DD]` -> `tracking-YYYY-MM-DD.md` (merged timeline).

2. **Caption screenshots with a small model.** Spawn one Haiku agent per
   screenshot (or batch), model=haiku, each returns ONE line:
   `HH:MM:SS | app/context | activity | inefficiency-signal?`
   Vision only where the keystroke log can't tell what happened (GUI apps).

3. **Detect repeats.** From keystroke log + nvim log + captions, find low-value
   repeated actions:
   - same command retyped / long sequences that a hotkey or alias would shorten
   - nvim: arrow keys instead of hjkl, repeated `jjjj`/`kkkk` instead of counts/`/`search, leaving insert mode to move, no macros for repetitive edits
   - browser/GUI: same page opened many times (batch into a digest), menu-mousing where a hotkey exists
   - a 5-min manual task repeated 3-4x/day (candidate for a script/extension)

4. **Update `ledger.md`.** For each pattern: if it already exists, increment
   `count` and update `last seen`; else append a new row. Flag every row at
   `count >= 3` as confirmed.

5. **Print suggestions**, ranked by time saved. Concrete: the exact remap,
   alias, macro, Raycast script, or Chrome extension. Offer to build the top 1-2.

## Cadence
Daily quick pass, or weekly deeper pass. Each run should end with: confirmed
patterns (count >= 3), and 1-2 fixes to implement now.
