"""Clean environment for subprocesses spawned from a frozen (PyInstaller) app.

PyInstaller injects DYLD_LIBRARY_PATH / DYLD_FRAMEWORK_PATH (and friends) so the
bundled interpreter finds its own libs. Child programs like the `claude` CLI
(a Node binary) inherit those and fail to load. PyInstaller stashes the original
values as <VAR>_ORIG; restore them (or drop the var) before spawning, so external
tools run in a pristine environment. A no-op when running unfrozen from source.
"""

import os
import sys

_VARS = ("DYLD_LIBRARY_PATH", "DYLD_FRAMEWORK_PATH", "LD_LIBRARY_PATH")


def clean_env(extra: dict = None) -> dict:
    env = dict(os.environ)
    if getattr(sys, "frozen", False):
        for v in _VARS:
            orig = env.pop(v + "_ORIG", None)
            if orig is not None:
                env[v] = orig
            else:
                env.pop(v, None)
    if extra:
        env.update(extra)
    return env
