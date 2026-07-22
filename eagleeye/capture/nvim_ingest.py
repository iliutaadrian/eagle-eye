"""Ingest the nvim mode-aware log (written by editor/nvim/keylog.lua) into the DB.

The nvim plugin appends to <data_dir>/nvim-YYYY-MM-DD.log lines like:
    [HH:MM:SS] n   ciwhello<Esc>
    --- file: /path/to/file
This tailer converts new lines into keystroke rows (source='nvim') so nvim keys
live in the same store, joined to app-usage by timestamp.
"""

import re
import threading
import time
from datetime import datetime

from .. import clock
from ..storage.models import Keyburst, count_keys

LINE = re.compile(r"^\[(\d{2}:\d{2}:\d{2})\]\s+(\S+)\s+(.*)$")


class NvimIngest(threading.Thread):
    def __init__(self, cfg, writer, running: threading.Event):
        super().__init__(daemon=True, name="nvim-ingest")
        self._w = writer
        self._running = running
        self._dir = cfg.data_dir      # nvim plugin writes here too
        self._pos = 0
        self._day = None
        self._path = None

    def _today_path(self):
        return self._dir / f"nvim-{clock.day_str()}.log"

    def run(self):
        # Start at end-of-file for today so we don't re-import old content.
        self._path = self._today_path()
        self._day = clock.day_str()
        if self._path.exists():
            self._pos = self._path.stat().st_size
        while self._running.is_set():
            try:
                self._tick()
            except Exception:
                pass
            self._sleep(2.0)

    def _tick(self):
        # Roll over at midnight.
        if clock.day_str() != self._day:
            self._path = self._today_path()
            self._day = clock.day_str()
            self._pos = 0
        if not self._path.exists():
            return
        size = self._path.stat().st_size
        if size <= self._pos:
            return
        with open(self._path, "r", errors="replace") as f:
            f.seek(self._pos)
            chunk = f.read()
            self._pos = f.tell()
        for line in chunk.splitlines():
            m = LINE.match(line.rstrip())
            if not m:
                continue
            hms_s, mode, tokens = m.groups()
            if not tokens or mode == "---":
                continue
            ts = self._epoch(hms_s)
            self._w.insert(Keyburst(
                day=self._day, ts=ts, source="nvim", app="", mode=mode,
                tokens=tokens, n_keys=count_keys(tokens),
            ))

    def _epoch(self, hms_s: str) -> float:
        h, m, s = (int(x) for x in hms_s.split(":"))
        base = datetime.now().replace(hour=h, minute=m, second=s, microsecond=0)
        return base.timestamp()

    def _sleep(self, secs):
        waited = 0.0
        while waited < secs and self._running.is_set():
            time.sleep(0.5)
            waited += 0.5
