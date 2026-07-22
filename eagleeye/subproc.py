"""Clean environment for subprocesses spawned from a frozen (PyInstaller) app.

PyInstaller injects DYLD_LIBRARY_PATH / DYLD_FRAMEWORK_PATH (and friends) so the
bundled interpreter finds its own libs. Child programs like the `claude` CLI
(a Node binary) inherit those and fail to load. PyInstaller stashes the original
values as <VAR>_ORIG; restore them (or drop the var) before spawning, so external
tools run in a pristine environment. A no-op when running unfrozen from source.
"""

import os
import sys
from pathlib import Path

_VARS = ("DYLD_LIBRARY_PATH", "DYLD_FRAMEWORK_PATH", "LD_LIBRARY_PATH")

# A Finder-launched .app inherits a bare PATH, so the `claude` launcher (a Node
# script) can't find `node`. Prepend the usual node/tool install dirs.
_BIN_DIRS = (
    "~/.claude/local",
    "/opt/homebrew/bin",
    "/usr/local/bin",
    "~/.local/bin",
    "~/.npm-global/bin",
    "~/.volta/bin",
)


def _augment_path(env: dict) -> None:
    extra = [str(Path(p).expanduser()) for p in _BIN_DIRS]
    nvm = Path("~/.nvm/versions/node").expanduser()
    if nvm.is_dir():
        for d in sorted(nvm.iterdir(), reverse=True):
            extra.append(str(d / "bin"))
    cur = env.get("PATH", "").split(":") if env.get("PATH") else []
    seen = set(cur)
    env["PATH"] = ":".join(cur + [d for d in extra if d not in seen])


def clean_env(extra: dict = None) -> dict:
    env = dict(os.environ)
    if getattr(sys, "frozen", False):
        for v in _VARS:
            orig = env.pop(v + "_ORIG", None)
            if orig is not None:
                env[v] = orig
            else:
                env.pop(v, None)
    _augment_path(env)
    if extra:
        env.update(extra)
    return env
