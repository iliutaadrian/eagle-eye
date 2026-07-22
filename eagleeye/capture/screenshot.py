"""Screenshot watcher: periodic capture -> screen_capture rows + JPEG files,
with throttled, single-flight captioning via headless Claude Code (cheap model).
"""

import queue
import subprocess
import threading

from .. import clock
from ..storage.models import Capture
from ..subproc import clean_env
from . import frontmost, imagehash

# Marks headless Claude calls so the user's Stop hook can skip its ding.
_HEADLESS = {"EAGLEEYE_HEADLESS": "1"}

# Ground truth (real foreground app/title) prevents the model guessing "VS Code"
# for what is actually Neovim in a terminal.
DESC_PROMPT = (
    "Screenshot at {path}. Ground truth: the foreground app is \"{app}\""
    " (window title: \"{title}\"). Trust this for the app name; do NOT guess a "
    "different editor. If the app is a terminal (Ghostty/iTerm/Terminal/Alacritty/"
    "kitty/WezTerm) or tmux, any code editor shown is Neovim/Vim, never VS Code.\n"
    "Reply ONE line only, format: app | activity | "
    "repeated-or-low-value-action-signal. No preamble."
)


class ScreenShooter(threading.Thread):
    def __init__(self, cfg, writer, idle_monitor, running: threading.Event,
                 paused: threading.Event):
        super().__init__(daemon=True, name="screenshot")
        self._cfg = cfg
        self._w = writer
        self._idle = idle_monitor
        self._running = running
        self._paused = paused
        sc = cfg["screenshot"]
        self._interval = float(sc["interval"])
        self._idle_skip = float(sc["idle_skip"])
        self._max_width = int(sc["max_width"])
        self._quality = str(sc["jpeg_quality"])
        self._describe = bool(sc["describe"])
        # Concurrent caption workers: every frame is captioned (describe interval
        # == capture interval). Enough workers to keep up if one caption is slower
        # than the capture interval, so no frame is skipped.
        self._workers_n = int(sc.get("describe_workers", 3))
        self._model = cfg.get("analysis", "model", default="haiku")
        self._flags = cfg.get("analysis", "claude_flags", default=[]) or []
        # Dedup: drop a frame that's perceptually identical to the last kept one
        # (no JPEG kept, no caption) — saves disk + the headless Claude call.
        self._dedup = bool(sc.get("dedup", True))
        self._dedup_threshold = int(sc.get("dedup_threshold", 3))
        self._dedup_max_skips = int(sc.get("dedup_max_skips", 30))
        self._prev_hash = None
        self._skips = 0
        self._screens_dir = cfg.screens_dir
        self._data_dir = cfg.data_dir
        self._queue = queue.Queue()
        self._workers = []

    def _capture(self):
        now = clock.now()
        day = clock.day_str(now)
        day_dir = self._screens_dir / day
        day_dir.mkdir(parents=True, exist_ok=True)
        name = clock.hms(now).replace(":", "-") + ".jpg"
        path = day_dir / name
        subprocess.run(["screencapture", "-x", "-t", "jpg", str(path)],
                       stderr=subprocess.DEVNULL)
        if not path.exists():
            return None, None, None, None, None
        subprocess.run(["sips", "-Z", str(self._max_width),
                        "-s", "formatOptions", self._quality, str(path)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if self._is_duplicate(path):
            path.unlink(missing_ok=True)   # identical to last kept frame — drop it
            self._skips += 1
            return None, None, None, None, None
        app, title = frontmost.app_and_title()
        rel = str(path.relative_to(self._data_dir))
        cid = self._w.insert_capture(Capture(day=day, ts=now, file=rel)).get()
        return cid, path, now, app, title

    def _is_duplicate(self, path) -> bool:
        """True if this frame matches the last kept one within the dedup
        threshold. A heartbeat (`dedup_max_skips`) forces a fresh frame after a
        long static stretch so subtle drift and long idle screens still refresh.
        On any hash failure, keep the frame (fail open)."""
        if not self._dedup:
            return False
        h = imagehash.dhash(path)
        if h is None:
            self._prev_hash = None       # unknown — anchor resets, keep frame
            self._skips = 0
            return False
        dup = (
            self._prev_hash is not None
            and imagehash.hamming(h, self._prev_hash) <= self._dedup_threshold
            and self._skips < self._dedup_max_skips
        )
        if not dup:
            self._prev_hash = h          # this frame becomes the new anchor
            self._skips = 0
        return dup

    def _caption_worker(self):
        """Pull captured frames off the queue and caption each one."""
        while self._running.is_set():
            try:
                job = self._queue.get(timeout=1.0)
            except queue.Empty:
                continue
            cid, path, app, title = job
            prompt = DESC_PROMPT.format(path=path, app=app or "unknown",
                                        title=title or "")
            try:
                out = subprocess.check_output(
                    ["claude", "-p", prompt, "--model", self._model, *self._flags],
                    text=True, timeout=120, stderr=subprocess.DEVNULL,
                    env=clean_env(_HEADLESS),
                ).strip()
                if out:
                    self._w.update_caption(cid, out, clock.now())
            except Exception:
                pass

    def run(self):
        if self._describe:
            for i in range(self._workers_n):
                t = threading.Thread(target=self._caption_worker, daemon=True,
                                     name=f"caption-{i}")
                t.start()
                self._workers.append(t)
        while self._running.is_set():
            try:
                if not self._paused.is_set() and self._idle.seconds < self._idle_skip:
                    cid, path, now, app, title = self._capture()
                    if cid and self._describe:
                        self._queue.put((cid, path, app, title))  # caption every frame
            except Exception:
                pass
            self._sleep()

    def _sleep(self):
        step, waited = 0.5, 0.0
        while waited < self._interval and self._running.is_set():
            import time
            time.sleep(step)
            waited += step
