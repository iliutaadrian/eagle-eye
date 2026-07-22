"""Supervisor: owns the DB connection, writer, and all capture watchers.

One process, watchers as threads. Start order: DB -> writer -> idle monitor ->
sampler/screenshot/keylog. rumps runs the main-thread NSApplication loop on top.
"""

import threading

from . import clock
from .capture.keylog import KeyLogger
from .capture.nvim_ingest import NvimIngest
from .capture.sampler import Sampler
from .capture.screenshot import ScreenShooter
from .storage import db
from .storage.writer import Writer


class Supervisor:
    def __init__(self, cfg):
        self.cfg = cfg
        self.running = threading.Event()
        self.paused = threading.Event()
        self.conn = None
        self.writer = None
        self.idle = None
        self.screenshot = None
        self._threads = []
        self._keylog = None

    def start(self):
        if self.running.is_set():
            return
        self.cfg.ensure_dirs()
        self.conn = db.connect(self.cfg.db_path)
        db.init_schema(self.conn)
        self.running.set()

        self.writer = Writer(self.conn)
        self.writer.start()

        self.idle = clock.IdleMonitor()
        self.idle.start()

        self._threads = []
        self._threads.append(
            Sampler(self.cfg, self.writer, self.idle, self.running, self.paused))
        if self.cfg.get("screenshot", "enabled", default=True):
            self.screenshot = ScreenShooter(
                self.cfg, self.writer, self.idle, self.running, self.paused)
            self._threads.append(self.screenshot)
        self._threads.append(NvimIngest(self.cfg, self.writer, self.running))
        for t in self._threads:
            t.start()

        if self.cfg.get("keylog", "enabled", default=True):
            self._keylog = KeyLogger(self.cfg, self.writer, self.running, self.paused)
            self._keylog.start()

    def stop(self):
        if not self.running.is_set():
            return
        self.running.clear()
        if self._keylog:
            self._keylog.stop()
            self._keylog = None
        for t in self._threads:
            t.join(timeout=3)
        self._threads = []
        self.screenshot = None
        if self.idle:
            self.idle.stop()
        if self.writer:
            self.writer.stop()
            self.writer.join(timeout=3)
        if self.conn:
            try:
                self.conn.close()
            except Exception:
                pass
            self.conn = None

    def set_paused(self, on: bool):
        if on:
            self.paused.set()
        else:
            self.paused.clear()

    # read-only status (safe under WAL via a fresh short-lived connection)
    def status(self, day: str = None):
        day = day or clock.day_str()
        conn = db.connect(self.cfg.db_path)
        try:
            counts = db.today_counts(conn, day)
            tops = db.top_apps(conn, day)
        finally:
            conn.close()
        return counts, tops
