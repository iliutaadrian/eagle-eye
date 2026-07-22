"""Row dataclasses for the capture streams."""

import re
from dataclasses import asdict, dataclass
from typing import Optional

_TOKEN = re.compile(r"<[^>]+>|[^<]")


def count_keys(tokens: str) -> int:
    """Count real keystrokes in a rendered token string: each <Name> is one
    key, each other char is one key. Avoids counting '<C-w>' as five."""
    return len(_TOKEN.findall(tokens))


@dataclass
class AppSegment:
    day: str
    app: str
    title: Optional[str]
    url: Optional[str]
    ts_start: float
    ts_end: float
    duration: float
    was_idle: int = 0

    table = "app_usage"

    def row(self):
        return asdict(self)


@dataclass
class Keyburst:
    day: str
    ts: float
    source: str          # 'global' | 'nvim'
    app: Optional[str]
    mode: Optional[str]  # nvim mode; None for global
    tokens: str
    n_keys: int

    table = "keystroke"

    def row(self):
        return asdict(self)


@dataclass
class Capture:
    day: str
    ts: float
    file: str            # path relative to data_dir
    desc: Optional[str] = None
    described_at: Optional[float] = None

    table = "screen_capture"

    def row(self):
        return asdict(self)
