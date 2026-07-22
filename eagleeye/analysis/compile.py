"""Build a daily timeline markdown from the SQLite DB (for Claude analysis)."""

from ..clock import fmt_secs, hms
from ..storage import db


def build(cfg, day: str):
    conn = db.connect(cfg.db_path)
    events = []  # (ts, src, text)

    for r in conn.execute(
        "SELECT ts_start,app,title,url,duration FROM app_usage WHERE day=? "
        "ORDER BY ts_start", (day,)
    ):
        ctx = r["app"] or "?"
        if r["title"]:
            ctx += f" · {r['title']}"
        if r["url"]:
            ctx += f" · {r['url']}"
        events.append((r["ts_start"], "app", f"{ctx}  ({fmt_secs(r['duration'])})"))

    for r in conn.execute(
        "SELECT ts,source,app,mode,tokens FROM keystroke WHERE day=? ORDER BY ts", (day,)
    ):
        tag = r["source"] + (f":{r['mode']}" if r["mode"] else "")
        app = f"[{r['app']}] " if r["app"] else ""
        events.append((r["ts"], tag, app + r["tokens"]))

    for r in conn.execute(
        "SELECT ts,desc,file FROM screen_capture WHERE day=? ORDER BY ts", (day,)
    ):
        events.append((r["ts"], "screen", r["desc"] or r["file"]))

    counts = db.today_counts(conn, day)
    tops = db.top_apps(conn, day, limit=12)
    conn.close()

    events.sort(key=lambda e: e[0])
    out = cfg.data_dir / f"tracking-{day}.md"
    with out.open("w") as f:
        f.write(f"# Tracking — {day}\n\n")
        f.write(f"- app segments: {counts['segments']} ({counts['apps']} apps)\n")
        f.write(f"- keystrokes: {counts['keys']}\n")
        f.write(f"- screenshots: {counts['shots']} ({counts['captioned']} captioned)\n\n")
        if tops:
            f.write("## Top apps by active time\n\n")
            for app, secs in tops:
                f.write(f"- {fmt_secs(secs):>7}  {app}\n")
            f.write("\n")
        f.write("## Timeline\n\n| time | src | event |\n|------|-----|-------|\n")
        for ts, src, text in events:
            text = str(text).replace("|", "\\|")
            f.write(f"| {hms(ts)} | {src} | `{text}` |\n")
    return out
