"""App-usage sampler: polls frontmost context, coalesces into dwell segments.

Measures time-per-window-context (even when you don't type) and subtracts idle:
an idle gap breaks the current segment, so each stored segment is one continuous
active span. Complements the keylogger (which records what you typed per app).
"""

import threading
import time

from .. import clock
from ..storage.models import AppSegment
from . import frontmost


class Sampler(threading.Thread):
    def __init__(self, cfg, writer, idle_monitor, running: threading.Event,
                 paused: threading.Event):
        super().__init__(daemon=True, name="sampler")
        self._cfg = cfg
        self._w = writer
        self._idle = idle_monitor
        self._running = running
        self._paused = paused
        self._poll = float(cfg.get("capture", "poll_interval", default=1.5))
        self._idle_threshold = float(cfg.get("capture", "idle_threshold", default=60))
        self._browsers = cfg.get("browsers", default={}) or {}
        self._url_cache = {}
        self._open = None  # dict: app,title,url,ts_start,ts_end

    def _ctx_key(self, ctx):
        return (ctx.app, ctx.title, ctx.url)

    def _finalize(self):
        o = self._open
        if o and o["ts_end"] > o["ts_start"]:
            self._w.insert(AppSegment(
                day=clock.day_str(o["ts_start"]),
                app=o["app"], title=o["title"], url=o["url"],
                ts_start=o["ts_start"], ts_end=o["ts_end"],
                duration=o["ts_end"] - o["ts_start"], was_idle=0,
            ))
        self._open = None

    def run(self):
        while self._running.is_set():
            try:
                if self._paused.is_set():
                    self._finalize()
                    self._sleep()
                    continue
                now = clock.now()
                if self._idle.seconds > self._idle_threshold:
                    self._finalize()          # away — stop accruing
                    self._sleep()
                    continue
                ctx = frontmost.read(self._browsers, self._url_cache)
                if ctx.app is None:
                    self._sleep()
                    continue
                if self._open and self._ctx_key(ctx) == (
                        self._open["app"], self._open["title"], self._open["url"]):
                    self._open["ts_end"] = now       # extend
                else:
                    if self._open:                   # attribute time up to the change
                        self._open["ts_end"] = now
                    self._finalize()                 # context changed
                    self._open = {
                        "app": ctx.app, "title": ctx.title, "url": ctx.url,
                        "ts_start": now, "ts_end": now,
                    }
            except Exception:
                pass
            self._sleep()
        self._finalize()

    def _sleep(self):
        # Chunked sleep so a stop (running cleared) is picked up promptly.
        step = 0.25
        waited = 0.0
        while waited < self._poll and self._running.is_set():
            time.sleep(step)
            waited += step
