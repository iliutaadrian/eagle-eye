"""SQLite storage: schema, connection (WAL), and aggregate read queries."""

import sqlite3
from pathlib import Path

SCHEMA_VERSION = "1"

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);

CREATE TABLE IF NOT EXISTS app_usage (
  id        INTEGER PRIMARY KEY,
  day       TEXT NOT NULL,
  app       TEXT NOT NULL,
  title     TEXT,
  url       TEXT,
  ts_start  REAL NOT NULL,
  ts_end    REAL NOT NULL,
  duration  REAL NOT NULL,
  was_idle  INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ix_usage_day   ON app_usage(day);
CREATE INDEX IF NOT EXISTS ix_usage_start ON app_usage(ts_start);
CREATE INDEX IF NOT EXISTS ix_usage_app   ON app_usage(day, app);

CREATE TABLE IF NOT EXISTS keystroke (
  id      INTEGER PRIMARY KEY,
  day     TEXT NOT NULL,
  ts      REAL NOT NULL,
  source  TEXT NOT NULL,
  app     TEXT,
  mode    TEXT,
  tokens  TEXT NOT NULL,
  n_keys  INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_key_day    ON keystroke(day);
CREATE INDEX IF NOT EXISTS ix_key_ts     ON keystroke(ts);
CREATE INDEX IF NOT EXISTS ix_key_source ON keystroke(day, source);

CREATE TABLE IF NOT EXISTS screen_capture (
  id           INTEGER PRIMARY KEY,
  day          TEXT NOT NULL,
  ts           REAL NOT NULL,
  file         TEXT NOT NULL,
  desc         TEXT,
  described_at REAL
);
CREATE INDEX IF NOT EXISTS ix_shot_day ON screen_capture(day);
CREATE INDEX IF NOT EXISTS ix_shot_ts  ON screen_capture(ts);
"""


def connect(db_path: Path) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_schema(conn: sqlite3.Connection):
    conn.executescript(SCHEMA)
    conn.execute(
        "INSERT INTO meta(key,value) VALUES('schema_version',?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (SCHEMA_VERSION,),
    )
    conn.commit()


# --- aggregate read queries (menu bar / cli status; safe under WAL) ---

def today_counts(conn: sqlite3.Connection, day: str) -> dict:
    def scalar(sql, *a):
        return conn.execute(sql, a).fetchone()[0]
    return {
        "apps": scalar("SELECT COUNT(DISTINCT app) FROM app_usage WHERE day=?", day),
        "segments": scalar("SELECT COUNT(*) FROM app_usage WHERE day=?", day),
        "keys": scalar("SELECT COALESCE(SUM(n_keys),0) FROM keystroke WHERE day=?", day),
        "shots": scalar("SELECT COUNT(*) FROM screen_capture WHERE day=?", day),
        "captioned": scalar(
            "SELECT COUNT(*) FROM screen_capture WHERE day=? AND desc IS NOT NULL", day),
    }


def top_apps(conn: sqlite3.Connection, day: str, limit: int = 8):
    rows = conn.execute(
        "SELECT app, SUM(duration) AS secs FROM app_usage "
        "WHERE day=? AND was_idle=0 GROUP BY app ORDER BY secs DESC LIMIT ?",
        (day, limit),
    ).fetchall()
    return [(r["app"], r["secs"]) for r in rows]
