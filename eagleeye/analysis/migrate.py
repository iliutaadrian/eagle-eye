"""One-time import of legacy ~/keylog flat-file data into the SQLite DB."""

import json
import re
from datetime import datetime
from pathlib import Path

from ..storage import db
from ..storage.models import Capture, Keyburst, count_keys
from ..storage.writer import Writer

KEYLOG = Path.home() / "keylog"
ALL_TS = re.compile(r"^\[(\d{2}:\d{2}:\d{2})\]\s+(\S.*?)\s{2,}(.*)$")
NVIM_TS = re.compile(r"^\[(\d{2}:\d{2}:\d{2})\]\s+(\S+)\s+(.*)$")


def _epoch(day: str, hms: str) -> float:
    return datetime.strptime(f"{day} {hms}", "%Y-%m-%d %H:%M:%S").timestamp()


def _day_from(name: str) -> str:
    m = re.search(r"(\d{4}-\d{2}-\d{2})", name)
    return m.group(1) if m else ""


def run(cfg):
    cfg.ensure_dirs()
    conn = db.connect(cfg.db_path)
    db.init_schema(conn)
    w = Writer(conn)
    w.start()
    n_key = n_shot = 0

    # global keylog: all-YYYY-MM-DD.log  ->  keystroke(source='global')
    for p in sorted(KEYLOG.glob("all-*.log")):
        day = _day_from(p.name)
        for line in p.read_text(errors="replace").splitlines():
            m = ALL_TS.match(line.rstrip())
            if not m:
                continue
            hms, app, tokens = m.groups()
            if not tokens:
                continue
            w.insert(Keyburst(day, _epoch(day, hms), "global", app.strip(),
                              None, tokens, count_keys(tokens)))
            n_key += 1

    # nvim log: nvim-YYYY-MM-DD.log  ->  keystroke(source='nvim')
    for p in sorted(KEYLOG.glob("nvim-*.log")):
        day = _day_from(p.name)
        for line in p.read_text(errors="replace").splitlines():
            m = NVIM_TS.match(line.rstrip())
            if not m:
                continue
            hms, mode, tokens = m.groups()
            if not tokens or mode == "---":
                continue
            w.insert(Keyburst(day, _epoch(day, hms), "nvim", "", mode,
                              tokens, count_keys(tokens)))
            n_key += 1

    # captions: desc-YYYY-MM-DD.jsonl  ->  screen_capture
    for p in sorted(KEYLOG.glob("desc-*.jsonl")):
        day = _day_from(p.name)
        for line in p.read_text(errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            ts = _epoch(day, r.get("ts", "00:00:00").replace(".", ":")[:8]) \
                if ":" in r.get("ts", "") else _epoch(day, "00:00:00")
            w.insert(Capture(day, ts, f"screens/{day}/{r.get('file','')}",
                             r.get("desc"), ts))
            n_shot += 1

    w.stop()
    w.join()
    print(f"migrated: {n_key} keystroke rows, {n_shot} captions from {KEYLOG}")
    print("note: screenshot JPEGs stay in ~/keylog/screens (not copied).")
