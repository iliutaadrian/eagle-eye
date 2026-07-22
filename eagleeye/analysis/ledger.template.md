# Observations Ledger

Persistent, append-only record of workflow inefficiencies detected across days.
One row per distinct pattern. `count` increments each day the pattern reappears.
A pattern at **count >= 3** is a confirmed inefficiency worth fixing.

Status: `open` (unfixed) | `fixed` (resolved) | `wontfix` (accepted).

| pattern | source | count | first seen | last seen | status | suggested fix |
|---------|--------|-------|-----------|-----------|--------|---------------|
| _example: arrow keys used for nvim motion instead of hjkl_ | nvim | 0 | - | - | open | remap / build hjkl habit |
