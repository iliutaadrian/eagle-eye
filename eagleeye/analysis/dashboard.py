"""Small live dashboard: a stdlib HTTP server that renders today's activity
from the SQLite DB on each request. Screenshots are served from the data dir.
"""

import html
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from .. import __app_name__, clock
from ..storage import db

PORT = 8899
_server = None


def render_html(cfg, day: str) -> str:
    conn = db.connect(cfg.db_path)
    counts = db.today_counts(conn, day)
    tops = db.top_apps(conn, day, limit=12)
    keys_by_app = conn.execute(
        "SELECT app, SUM(n_keys) k FROM keystroke WHERE day=? AND app<>'' "
        "GROUP BY app ORDER BY k DESC LIMIT 10", (day,)).fetchall()
    nvim_modes = conn.execute(
        "SELECT mode, SUM(n_keys) k FROM keystroke WHERE day=? AND source='nvim' "
        "GROUP BY mode ORDER BY k DESC", (day,)).fetchall()
    shots = conn.execute(
        "SELECT ts, file, desc FROM screen_capture WHERE day=? ORDER BY ts DESC "
        "LIMIT 24", (day,)).fetchall()
    klog = conn.execute(
        "SELECT ts, source, app, mode, tokens, n_keys FROM keystroke WHERE day=? "
        "ORDER BY ts DESC LIMIT 120", (day,)).fetchall()
    conn.close()

    max_secs = max([s for _, s in tops], default=1) or 1
    max_keys = max([r["k"] for r in keys_by_app], default=1) or 1

    def bars(rows, label, val, fmt, mx):
        out = []
        for r in rows:
            name = html.escape(str(label(r)))
            v = val(r)
            pct = int(100 * v / mx)
            out.append(
                f'<div class=row><span class=lbl>{name}</span>'
                f'<span class=bar><i style="width:{pct}%"></i></span>'
                f'<span class=val>{fmt(v)}</span></div>')
        return "".join(out) or '<div class=empty>none yet</div>'

    apps_html = bars(tops, lambda r: r[0], lambda r: r[1], clock.fmt_secs, max_secs)
    keys_html = bars(keys_by_app, lambda r: r["app"], lambda r: r["k"],
                     lambda v: str(int(v)), max_keys)
    modes = " · ".join(f"{r['mode']}: {int(r['k'])}" for r in nvim_modes) or "no nvim keys"

    cards = []
    for r in shots:
        cap = html.escape(r["desc"] or "(not captioned)")
        src = "/" + html.escape(r["file"])
        cards.append(
            f'<figure><img src="{src}" loading=lazy onclick="zoom(this.src)">'
            f'<figcaption><b>{clock.hms(r["ts"])}</b> {cap}</figcaption></figure>')
    cards_html = "".join(cards) or '<div class=empty>no screenshots yet</div>'

    klog_rows = []
    for r in klog:
        if r["source"] == "nvim":
            tag = f'nvim:{r["mode"]}'
        else:
            tag = html.escape(r["app"] or "global")
        toks = html.escape(r["tokens"])
        klog_rows.append(
            f'<div class=krow><span class=kt>{clock.hms(r["ts"])}</span>'
            f'<span class=ka>{tag}</span>'
            f'<span class=kk>{toks}</span></div>')
    klog_html = "".join(klog_rows) or '<div class=empty>no keystrokes yet</div>'

    return f"""<!doctype html><html><head><meta charset=utf-8>
<title>{__app_name__} — {day}</title>
<style>
:root{{color-scheme:dark}}
body{{font:14px -apple-system,system-ui,sans-serif;background:#0d1117;color:#e6edf3;
margin:0;padding:24px;max-width:900px;margin:auto}}
h1{{font-size:20px;margin:0 0 4px}} .sub{{color:#8b949e;margin-bottom:20px}}
.tiles{{display:flex;gap:12px;margin-bottom:24px;flex-wrap:wrap}}
.tile{{background:#161b22;border:1px solid #21262d;border-radius:10px;padding:14px 18px;flex:1;min-width:120px}}
.tile b{{font-size:24px;display:block}} .tile span{{color:#8b949e;font-size:12px}}
h2{{font-size:14px;color:#8b949e;text-transform:uppercase;letter-spacing:.5px;margin:24px 0 10px}}
.row{{display:flex;align-items:center;gap:10px;margin:5px 0}}
.lbl{{width:150px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex-shrink:0}}
.bar{{flex:1;background:#21262d;border-radius:5px;height:14px;overflow:hidden}}
.bar i{{display:block;height:100%;background:linear-gradient(90deg,#2f81f7,#a371f7)}}
.val{{width:64px;text-align:right;color:#8b949e;font-variant-numeric:tabular-nums}}
.empty{{color:#8b949e;font-style:italic}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:14px}}
figure{{margin:0;background:#161b22;border:1px solid #21262d;border-radius:10px;overflow:hidden}}
figure img{{width:100%;display:block;aspect-ratio:16/10;object-fit:cover;cursor:zoom-in}}
figcaption{{padding:8px 10px;font-size:12px;color:#c9d1d9;line-height:1.4}}
.klog{{background:#161b22;border:1px solid #21262d;border-radius:10px;padding:8px 12px;
max-height:420px;overflow:auto;font:12px ui-monospace,SFMono-Regular,Menlo,monospace}}
.krow{{display:flex;gap:10px;padding:3px 0;border-bottom:1px solid #1b2028}}
.kt{{color:#8b949e;flex-shrink:0}} .ka{{color:#a371f7;width:130px;flex-shrink:0;
overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.kk{{color:#e6edf3;word-break:break-all}}
#lb{{position:fixed;inset:0;background:rgba(0,0,0,.92);display:none;align-items:center;
justify-content:center;cursor:zoom-out;z-index:99}}
#lb.open{{display:flex}} #lb img{{max-width:96%;max-height:96%;box-shadow:0 0 40px #000}}
</style></head><body>
<div id=lb onclick="this.classList.remove('open')"><img id=lbimg></div>
<h1>{__app_name__}</h1><div class=sub>{day} · auto-refreshes every 15s</div>
<div class=tiles>
<div class=tile><b>{counts['apps']}</b><span>apps</span></div>
<div class=tile><b>{counts['segments']}</b><span>segments</span></div>
<div class=tile><b>{counts['keys']}</b><span>keystrokes</span></div>
<div class=tile><b>{counts['shots']}</b><span>screenshots</span></div>
<div class=tile><b>{counts['captioned']}</b><span>captioned</span></div>
</div>
<h2>Top apps by active time</h2>{apps_html}
<h2>Keystrokes by app</h2>{keys_html}
<h2>nvim modes</h2><div class=sub>{modes}</div>
<h2>Recent keystrokes</h2><div class=klog>{klog_html}</div>
<h2>Recent screenshots</h2><div class=grid>{cards_html}</div>
<script>
function zoom(src){{var i=document.getElementById('lbimg');i.src=src;
document.getElementById('lb').classList.add('open');}}
document.addEventListener('keydown',function(e){{if(e.key==='Escape')
document.getElementById('lb').classList.remove('open');}});
// auto-refresh every 15s, but not while a screenshot is zoomed
setInterval(function(){{
  if(!document.getElementById('lb').classList.contains('open')) location.reload();
}},15000);
</script>
</body></html>"""


def _make_handler(cfg):
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=str(cfg.data_dir), **k)

        def do_GET(self):
            if self.path in ("/", "/index.html", "/dashboard"):
                body = render_html(cfg, clock.day_str()).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                super().do_GET()  # serve screenshot files from data_dir

        def log_message(self, *a):
            pass  # quiet

    return Handler


def serve(cfg, port: int = PORT):
    """Start the dashboard server once (idempotent). Returns the URL."""
    global _server
    if _server is None:
        _server = ThreadingHTTPServer(("127.0.0.1", port), _make_handler(cfg))
        threading.Thread(target=_server.serve_forever, daemon=True,
                         name="dashboard").start()
    return f"http://127.0.0.1:{port}/"
