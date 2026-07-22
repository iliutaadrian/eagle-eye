"""Shared clock + idle detection, so every watcher uses one time source."""

import re
import subprocess
import threading
import time
from datetime import datetime


def now() -> float:
    """Single wall-clock epoch source shared by all watchers."""
    return time.time()


def day_str(ts: float = None) -> str:
    """Local YYYY-MM-DD for a timestamp (default: now)."""
    return datetime.fromtimestamp(ts if ts is not None else now()).strftime("%Y-%m-%d")


def hms(ts: float = None) -> str:
    return datetime.fromtimestamp(ts if ts is not None else now()).strftime("%H:%M:%S")


def fmt_secs(s: float) -> str:
    """Human duration: 1h05m / 12m / 8s."""
    s = int(s)
    h, m = s // 3600, (s % 3600) // 60
    if h:
        return f"{h}h{m:02d}m"
    return f"{m}m" if m else f"{s}s"


def _read_idle_seconds() -> float:
    """Seconds since last keyboard/mouse input (macOS HID idle time)."""
    try:
        out = subprocess.check_output(
            ["ioreg", "-c", "IOHIDSystem"], text=True, stderr=subprocess.DEVNULL
        )
        m = re.search(r'"HIDIdleTime"\s*=\s*(\d+)', out)
        if m:
            return int(m.group(1)) / 1_000_000_000
    except Exception:
        pass
    return 0.0


class IdleMonitor(threading.Thread):
    """Polls HID idle time on one thread; other watchers read the cached value."""

    def __init__(self, poll: float = 1.0):
        super().__init__(daemon=True, name="idle-monitor")
        self._poll = poll
        self._seconds = 0.0
        self._stop = threading.Event()

    @property
    def seconds(self) -> float:
        return self._seconds

    def run(self):
        while not self._stop.is_set():
            self._seconds = _read_idle_seconds()
            self._stop.wait(self._poll)

    def stop(self):
        self._stop.set()
