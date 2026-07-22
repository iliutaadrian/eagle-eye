"""Global keystroke logger -> keystroke burst rows.

Refactor of the standalone global_keylog: same modifier/special decoding, but
instead of writing a text file it coalesces keys into bursts (flushed on app
change or an idle gap) and enqueues Keyburst rows to the DB writer.

pynput's macOS backend runs its own CFRunLoop on the listener thread, so this
coexists with rumps owning the main-thread NSApplication loop. Needs Input
Monitoring permission.
"""

import threading

from pynput import keyboard

from .. import clock
from ..storage.models import Keyburst
from .frontmost import app_name

SPECIAL = {
    keyboard.Key.enter: "<CR>", keyboard.Key.tab: "<Tab>",
    keyboard.Key.space: " ", keyboard.Key.backspace: "<BS>",
    keyboard.Key.esc: "<Esc>", keyboard.Key.delete: "<Del>",
    keyboard.Key.up: "<Up>", keyboard.Key.down: "<Down>",
    keyboard.Key.left: "<Left>", keyboard.Key.right: "<Right>",
    keyboard.Key.home: "<Home>", keyboard.Key.end: "<End>",
    keyboard.Key.page_up: "<PgUp>", keyboard.Key.page_down: "<PgDn>",
}
MODS = {
    keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r,
    keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r,
    keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r,
    keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r,
}
_CMD = (keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r)
_CTRL = (keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r)
_ALT = (keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r)


class KeyLogger:
    def __init__(self, cfg, writer, running: threading.Event, paused: threading.Event):
        self._w = writer
        self._running = running
        self._paused = paused
        self._idle_gap = float(cfg.get("keylog", "idle_gap", default=1.0))
        self._held = set()
        self._lock = threading.Lock()
        self._buf = []          # tokens in current burst
        self._app = None
        self._start = 0.0
        self._last = 0.0
        self._listener = None
        self._flusher = None
        self._stop_flush = threading.Event()

    # --- burst handling ---

    def _flush_locked(self):
        if self._buf:
            self._w.insert(Keyburst(
                day=clock.day_str(self._start), ts=self._start,
                source="global", app=self._app, mode=None,
                tokens="".join(self._buf), n_keys=len(self._buf),
            ))
        self._buf = []
        self._app = None

    def _record(self, token: str, app: str):
        now = clock.now()
        with self._lock:
            if self._buf and (app != self._app or now - self._last > self._idle_gap):
                self._flush_locked()
            if not self._buf:
                self._start = now
                self._app = app
            self._buf.append(token)
            self._last = now

    def _render(self, key) -> str:
        prefix = ""
        if any(k in self._held for k in _CMD):
            prefix += "D-"
        if any(k in self._held for k in _CTRL):
            prefix += "C-"
        if any(k in self._held for k in _ALT):
            prefix += "M-"
        if isinstance(key, keyboard.KeyCode) and key.char is not None:
            ch = key.char
            if len(ch) == 1 and ord(ch) < 0x20 and "C-" in prefix:
                ch = chr(ord(ch) + 96)
            return "<%s%s>" % (prefix, ch) if prefix else ch
        tok = SPECIAL.get(key) or ("<%s>" % str(key).replace("Key.", ""))
        if prefix and tok != " ":
            inner = tok[1:-1] if tok.startswith("<") else tok
            return "<%s%s>" % (prefix, inner)
        return tok

    def _on_press(self, key):
        if key in MODS:
            self._held.add(key)
            return
        if self._paused.is_set():
            return
        try:
            self._record(self._render(key), app_name())
        except Exception:
            pass

    def _on_release(self, key):
        self._held.discard(key)

    def _flush_loop(self):
        # Flush a trailing burst once it goes idle, without waiting for next key.
        while not self._stop_flush.is_set():
            self._stop_flush.wait(self._idle_gap)
            with self._lock:
                if self._buf and clock.now() - self._last > self._idle_gap:
                    self._flush_locked()

    # --- lifecycle ---

    def start(self):
        self._listener = keyboard.Listener(
            on_press=self._on_press, on_release=self._on_release)
        self._listener.start()
        self._flusher = threading.Thread(
            target=self._flush_loop, daemon=True, name="keylog-flush")
        self._flusher.start()

    def stop(self):
        self._stop_flush.set()
        if self._listener:
            self._listener.stop()
        with self._lock:
            self._flush_locked()
