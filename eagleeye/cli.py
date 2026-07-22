"""Eagle Eye command-line entry point."""

import argparse
import sys

from . import __app_name__, __version__
from . import config as config_mod
from .clock import day_str, fmt_secs
from .storage import db


def cmd_status(cfg, args):
    day = args.day or day_str()
    if not cfg.db_path.exists():
        print(f"{__app_name__}: no database yet at {cfg.db_path}")
        return
    conn = db.connect(cfg.db_path)
    c = db.today_counts(conn, day)
    print(f"{__app_name__} — {day}")
    print(f"  app segments : {c['segments']} ({c['apps']} distinct apps)")
    print(f"  keystrokes   : {c['keys']}")
    print(f"  screenshots  : {c['shots']} ({c['captioned']} captioned)")
    tops = db.top_apps(conn, day)
    if tops:
        print("  top apps by active time:")
        for app, secs in tops:
            print(f"    {fmt_secs(secs):>7}  {app}")


def cmd_run(cfg, args):
    from .app import run  # lazy: pulls in rumps/pyobjc only when running
    run(cfg)


def cmd_dashboard(cfg, args):
    import time
    import webbrowser

    from .analysis import dashboard
    url = dashboard.serve(cfg)
    print(f"dashboard: {url}  (Ctrl-C to stop)")
    webbrowser.open(url)
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        pass


def cmd_compile(cfg, args):
    from .analysis import compile as comp
    out = comp.build(cfg, args.day or day_str())
    print(f"wrote {out}")


def cmd_analyze(cfg, args):
    from .analysis import runner
    runner.run(cfg, args.day or day_str())


def cmd_migrate(cfg, args):
    from .analysis import migrate
    migrate.run(cfg)


def main(argv=None):
    p = argparse.ArgumentParser(prog="eagleeye", description=f"{__app_name__} tracker")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    ps = sub.add_parser("status", help="show today's capture counts")
    ps.add_argument("--day")
    ps.set_defaults(func=cmd_status)

    pr = sub.add_parser("run", help="run the menu-bar tracker")
    pr.set_defaults(func=cmd_run)

    pd = sub.add_parser("dashboard", help="serve the live web dashboard")
    pd.set_defaults(func=cmd_dashboard)

    pc = sub.add_parser("compile", help="build the daily timeline markdown")
    pc.add_argument("--day")
    pc.set_defaults(func=cmd_compile)

    pa = sub.add_parser("analyze", help="run the Claude analysis loop")
    pa.add_argument("--day")
    pa.set_defaults(func=cmd_analyze)

    pm = sub.add_parser("migrate", help="import legacy ~/keylog data into the DB")
    pm.set_defaults(func=cmd_migrate)

    args = p.parse_args(argv)
    cfg = config_mod.load()
    cfg.ensure_dirs()
    return args.func(cfg, args)


if __name__ == "__main__":
    sys.exit(main())
