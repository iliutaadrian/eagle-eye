"""Run the Claude analysis loop: compile the day, then have headless Claude Code
update the observations ledger with detected inefficiencies + suggestions.
"""

import subprocess

from ..permissions import find_claude
from ..subproc import clean_env
from . import compile as comp
from . import ledger

PROMPT = """You are analyzing a personal workflow-tracking log to find inefficiencies.

Read the daily timeline: {timeline}
Follow the runbook: {analyze}
Update the observations ledger in place: {ledger}

Steps:
1. From the timeline (app segments, keystrokes by app, nvim modes, screen
   captions), find repeated low-value actions and workflow inefficiencies.
2. For each: if it already exists in the ledger, increment its count and update
   last-seen; else append a new row. Flag any pattern at count >= 3 as confirmed.
3. Print the top 3 fixes ranked by time saved, each concrete (exact remap, alias,
   macro, script, or extension).

Be concise. Edit {ledger} directly.
"""


def run(cfg, day: str):
    ledger.ensure_seeded(cfg)
    timeline = comp.build(cfg, day)
    model = cfg.get("analysis", "model", default="haiku")
    flags = cfg.get("analysis", "claude_flags", default=[]) or []
    prompt = PROMPT.format(
        timeline=timeline,
        analyze=ledger.analyze_doc_path(cfg),
        ledger=ledger.ledger_path(cfg),
    )
    result = subprocess.run(
        [find_claude() or "claude", "-p", prompt, "--model", model, *flags],
        cwd=str(cfg.data_dir), text=True, capture_output=True, timeout=600,
        env=clean_env({"EAGLEEYE_HEADLESS": "1"}),
    )
    out = (result.stdout or "").strip()
    print(out)
    return out
