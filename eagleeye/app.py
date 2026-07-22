"""Menu-bar app (rumps). Owns the Supervisor; rumps owns the main run loop."""

import subprocess
import threading

import rumps

from . import __app_name__, clock
from .clock import fmt_secs
from .supervisor import Supervisor

MODELS = ["haiku", "sonnet", "opus"]
INTERVALS = [5, 10, 30]


class EagleEyeApp(rumps.App):
    def __init__(self, cfg):
        super().__init__(__app_name__, title="●", quit_button=None)
        self.cfg = cfg
        self.sup = Supervisor(cfg)

        self.status_item = rumps.MenuItem("Starting…")
        self.status_item.set_callback(None)  # disabled, display-only
        self.top_apps = rumps.MenuItem("Top apps")
        self.start_stop = rumps.MenuItem("Stop", callback=self.toggle_run)
        self.pause_item = rumps.MenuItem("Pause", callback=self.toggle_pause)

        self.model_menu = self._build_choice_menu(
            "Model", MODELS, cfg.get("analysis", "model", default="haiku"),
            self.set_model)
        self.interval_menu = self._build_choice_menu(
            "Screenshot interval", INTERVALS,
            int(cfg.get("screenshot", "interval", default=10)), self.set_interval,
            fmt=lambda v: f"{v}s")

        self.menu = [
            self.status_item,
            self.top_apps,
            None,
            self.start_stop,
            self.pause_item,
            self.model_menu,
            self.interval_menu,
            None,
            rumps.MenuItem("Open dashboard", callback=self.open_dashboard),
            rumps.MenuItem("Open data folder", callback=self.open_folder),
            rumps.MenuItem("Run analysis", callback=self.run_analysis),
            None,
            rumps.MenuItem("Quit", callback=self.quit_app),
        ]

        self.sup.start()
        self._refresh_timer = rumps.Timer(self.refresh, 5)
        self._refresh_timer.start()

    # --- choice submenus (model, interval) ---

    def _build_choice_menu(self, title, values, current, on_pick, fmt=str):
        parent = rumps.MenuItem(title)
        for v in values:
            item = rumps.MenuItem(
                fmt(v), callback=lambda sender, val=v: on_pick(val, sender))
            item.state = 1 if v == current else 0
            item._eagle_value = v
            parent.add(item)
        return parent

    def _mark(self, parent, value):
        for item in parent.values():
            item.state = 1 if getattr(item, "_eagle_value", None) == value else 0

    def set_model(self, value, sender=None):
        self.cfg.set("analysis", "model", value)
        if self.sup.screenshot:
            self.sup.screenshot._model = value
        self._mark(self.model_menu, value)

    def set_interval(self, value, sender=None):
        self.cfg.set("screenshot", "interval", value)
        if self.sup.screenshot:
            self.sup.screenshot._interval = float(value)
        self._mark(self.interval_menu, value)

    # --- status refresh ---

    def refresh(self, _=None):
        try:
            counts, tops = self.sup.status()
        except Exception:
            return
        if self.sup.paused.is_set():
            state = "paused"
        elif self.sup.running.is_set():
            state = "▶"
        else:
            state = "stopped"
        self.status_item.title = (
            f"{state}  {counts['apps']} apps · {counts['keys']} keys · "
            f"{counts['shots']} shots")
        self.top_apps.title = "Top apps"
        # rebuild submenu (its NSMenu doesn't exist until it has children)
        try:
            self.top_apps.clear()
        except AttributeError:
            pass
        for app, secs in tops:
            item = rumps.MenuItem(f"{fmt_secs(secs):>7}  {app}")
            item.set_callback(None)
            self.top_apps.add(item)
        if not tops:
            none_item = rumps.MenuItem("(none yet)")
            none_item.set_callback(None)
            self.top_apps.add(none_item)
        self.title = "○" if (self.sup.paused.is_set()
                             or not self.sup.running.is_set()) else "●"

    # --- menu actions ---

    def toggle_run(self, sender):
        if self.sup.running.is_set():
            self.sup.stop()
            sender.title = "Start"
        else:
            self.sup.start()
            sender.title = "Stop"
        self.refresh()

    def toggle_pause(self, sender):
        on = sender.state == 0
        self.sup.set_paused(on)
        sender.state = 1 if on else 0
        self.refresh()

    def open_dashboard(self, _):
        from .analysis import dashboard
        url = dashboard.serve(self.cfg)
        subprocess.run(["open", url])

    def open_folder(self, _):
        subprocess.run(["open", str(self.cfg.data_dir)])

    def run_analysis(self, _):
        def work():
            try:
                from .analysis import runner
                runner.run(self.cfg, clock.day_str())
                rumps.notification(__app_name__, "Analysis complete",
                                   "Ledger updated. See data folder.")
            except Exception as e:
                rumps.notification(__app_name__, "Analysis failed", str(e))
        threading.Thread(target=work, daemon=True).start()
        rumps.notification(__app_name__, "Analysis started", "Running in background…")

    def quit_app(self, _):
        self.sup.stop()
        rumps.quit_application()


def run(cfg):
    # Menu-bar only: hide the Dock icon + app menu even when launched outside an
    # LSUIElement .app bundle (e.g. straight from the venv via a LaunchAgent).
    try:
        from AppKit import NSApplication, NSApplicationActivationPolicyAccessory
        NSApplication.sharedApplication().setActivationPolicy_(
            NSApplicationActivationPolicyAccessory)
    except Exception:
        pass
    EagleEyeApp(cfg).run()
