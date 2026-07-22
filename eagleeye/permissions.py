"""macOS TCC permission preflight + external-tool discovery.

Accessibility is required: the AX API supplies focused-window titles, and it is
the permission macOS surfaces a grant prompt for. Screen Recording and Input
Monitoring degrade gracefully (blank shots / no keys) but are not gated here.

The `claude` CLI powers screenshot captioning and the analysis loop. A .app
launched from Finder inherits a minimal PATH (/usr/bin:/bin:/usr/sbin:/sbin),
so `shutil.which("claude")` usually misses an npm/nvm/Homebrew install — hence
the explicit candidate sweep.
"""

import os
import shutil
from pathlib import Path
from typing import Optional


def accessibility_trusted(prompt: bool = False) -> bool:
    """True if this process is trusted for the Accessibility API.

    prompt=True asks macOS to register the app in System Settings > Privacy &
    Security > Accessibility and show the grant dialog. On non-macOS or if the
    API is unavailable, returns True so nothing is blocked.
    """
    try:
        from ApplicationServices import (
            AXIsProcessTrustedWithOptions,
            kAXTrustedCheckOptionPrompt,
        )
    except Exception:  # pragma: no cover - non-macOS / API missing
        return True
    return bool(AXIsProcessTrustedWithOptions({kAXTrustedCheckOptionPrompt: bool(prompt)}))


def find_claude() -> Optional[str]:
    """Absolute path to the `claude` CLI, or None if not installed.

    Honors EAGLEEYE_CLAUDE_BIN, then PATH, then the usual install locations
    (Claude Code local, Homebrew, npm-global, nvm, volta, ~/.local/bin).
    """
    env = os.environ.get("EAGLEEYE_CLAUDE_BIN")
    if env:
        p = Path(env).expanduser()
        if p.is_file():
            return str(p)

    hit = shutil.which("claude")
    if hit:
        return hit

    home = Path.home()
    candidates = [
        home / ".claude/local/claude",
        home / ".local/bin/claude",
        Path("/opt/homebrew/bin/claude"),
        Path("/usr/local/bin/claude"),
        home / ".npm-global/bin/claude",
        home / ".volta/bin/claude",
        home / "bin/claude",
    ]
    nvm = home / ".nvm/versions/node"
    if nvm.is_dir():
        for d in sorted(nvm.iterdir(), reverse=True):
            candidates.append(d / "bin/claude")
    for c in candidates:
        if c.is_file():
            return str(c)
    return None
