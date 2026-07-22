"""Frontmost context: app name, focused window title (AX), browser tab URL."""

import subprocess
from collections import namedtuple

from AppKit import NSWorkspace

Context = namedtuple("Context", "app bundle pid title url")

# Accessibility API (window titles). Optional — NULL title if unavailable/denied.
try:
    from ApplicationServices import (
        AXUIElementCopyAttributeValue,
        AXUIElementCreateApplication,
    )
    _AX = True
except Exception:  # pragma: no cover
    _AX = False

_AX_FOCUSED_WINDOW = "AXFocusedWindow"
_AX_TITLE = "AXTitle"


def app_name():
    """Lightweight frontmost app name only (for per-keystroke tagging)."""
    try:
        a = NSWorkspace.sharedWorkspace().frontmostApplication()
        return a.localizedName() if a else None
    except Exception:
        return None


def app_and_title():
    """Frontmost app name + focused window title (for grounding captions)."""
    fa = _front_app()
    if fa is None:
        return None, None
    app, _bundle, pid = fa
    return app, _window_title(pid)


def _front_app():
    try:
        a = NSWorkspace.sharedWorkspace().frontmostApplication()
        if a is None:
            return None
        return (a.localizedName(), a.bundleIdentifier(), int(a.processIdentifier()))
    except Exception:
        return None


def _window_title(pid: int):
    if not _AX:
        return None
    try:
        app_el = AXUIElementCreateApplication(pid)
        err, win = AXUIElementCopyAttributeValue(app_el, _AX_FOCUSED_WINDOW, None)
        if err or win is None:
            return None
        err, title = AXUIElementCopyAttributeValue(win, _AX_TITLE, None)
        if err or not title:
            return None
        return str(title)
    except Exception:
        return None


# Per-browser osascript to read the active tab URL.
_SAFARI = 'tell application "Safari" to get URL of front document'
_CHROMIUM = 'tell application "{app}" to get URL of active tab of front window'


def _browser_url(app_name: str, dialect: str):
    try:
        if dialect == "safari":
            script = _SAFARI
        elif dialect == "chromium":
            script = _CHROMIUM.format(app=app_name)
        else:
            return None
        out = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=2,
        )
        url = out.stdout.strip()
        return url or None
    except Exception:
        return None


def read(browsers: dict, url_cache: dict = None) -> Context:
    """Read current context. `browsers` maps app localizedName -> dialect.

    url_cache: optional {app: (title, url)} so callers can skip osascript when
    the (app,title) hasn't changed (osascript is expensive).
    """
    fa = _front_app()
    if fa is None:
        return Context(None, None, None, None, None)
    app, bundle, pid = fa
    title = _window_title(pid)
    url = None
    if app in browsers:
        key = (app, title)
        if url_cache is not None and url_cache.get("key") == key:
            url = url_cache.get("url")
        else:
            url = _browser_url(app, browsers[app])
            if url_cache is not None:
                url_cache["key"] = key
                url_cache["url"] = url
    return Context(app, bundle, pid, title, url)
