"""Configuration: TOML loaded over built-in DEFAULTS, with path resolution."""

import json
from pathlib import Path

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib

DEFAULTS = {
    "paths": {
        "data_dir": "~/Library/Application Support/EagleEye",
    },
    "capture": {
        "poll_interval": 1.5,     # app-usage sampler poll (seconds)
        "idle_threshold": 60,     # seconds idle before dwell time stops accruing
    },
    "keylog": {
        "enabled": True,
        "idle_gap": 1.0,          # new keystroke burst after a pause this long
    },
    "screenshot": {
        "enabled": True,
        "interval": 10,           # seconds between shots
        "idle_skip": 60,          # skip shot if idle longer than this
        "max_width": 1024,        # downscale width (px)
        "jpeg_quality": "low",    # sips formatOptions: low/normal/high
        "describe": True,         # caption EVERY frame via headless Claude Code
        "describe_workers": 3,    # concurrent caption workers (keep up with capture)
        "dedup": True,            # skip frames identical to the previous kept one
        "dedup_threshold": 3,     # max dHash bit-distance still counted identical
        "dedup_max_skips": 30,    # after N skips, force a fresh frame (heartbeat)
    },
    "browsers": {                 # frontmost app localizedName -> osascript dialect
        "Safari": "safari",
        "Google Chrome": "chromium",
        "Arc": "chromium",
        "Brave Browser": "chromium",
        "Microsoft Edge": "chromium",
    },
    "analysis": {
        "model": "haiku",
        "claude_flags": ["--dangerously-skip-permissions"],
    },
}

CONFIG_PATH = Path("~/.config/eagleeye/config.toml").expanduser()
# Runtime overrides set from the menu bar (JSON, avoids needing a TOML writer).
OVERRIDES_PATH = Path("~/.config/eagleeye/overrides.json").expanduser()


def _deep_merge(base: dict, over: dict) -> dict:
    out = dict(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


class Config:
    def __init__(self, data: dict, overrides: dict = None):
        self._d = data
        self._overrides = overrides or {}

    def set(self, section: str, key: str, value):
        """Update a setting live and persist it to overrides.json."""
        self._d.setdefault(section, {})[key] = value
        self._overrides.setdefault(section, {})[key] = value
        try:
            OVERRIDES_PATH.parent.mkdir(parents=True, exist_ok=True)
            OVERRIDES_PATH.write_text(json.dumps(self._overrides, indent=2))
        except Exception:
            pass

    def __getitem__(self, key):
        return self._d[key]

    def get(self, *keys, default=None):
        """Nested access: cfg.get('screenshot', 'interval')."""
        cur = self._d
        for k in keys:
            if not isinstance(cur, dict) or k not in cur:
                return default
            cur = cur[k]
        return cur

    @property
    def data_dir(self) -> Path:
        return Path(self._d["paths"]["data_dir"]).expanduser()

    @property
    def db_path(self) -> Path:
        return self.data_dir / "eagleeye.db"

    @property
    def screens_dir(self) -> Path:
        return self.data_dir / "screens"

    def ensure_dirs(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.screens_dir.mkdir(parents=True, exist_ok=True)


def load(path: Path = CONFIG_PATH) -> Config:
    data = DEFAULTS
    if path.expanduser().exists():
        with open(path.expanduser(), "rb") as f:
            data = _deep_merge(DEFAULTS, tomllib.load(f))
    overrides = {}
    if OVERRIDES_PATH.exists():
        try:
            overrides = json.loads(OVERRIDES_PATH.read_text())
            data = _deep_merge(data, overrides)
        except Exception:
            overrides = {}
    return Config(data, overrides)
