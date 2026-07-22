"""Single DB-writer thread: all INSERT/UPDATE go through one queue.

SQLite is single-writer; funneling every mutation through one thread avoids
lock contention. Watchers only ever call the thread-safe enqueue helpers.
"""

import queue
import threading

_SENTINEL = object()


class Writer(threading.Thread):
    def __init__(self, conn, flush_every: int = 1):
        super().__init__(daemon=True, name="db-writer")
        self._conn = conn
        self._q = queue.Queue()
        self._flush_every = flush_every

    # --- producer API (thread-safe) ---

    def insert(self, model):
        """Enqueue a model dataclass (AppSegment/Keyburst/Capture)."""
        self._q.put(("insert", model.table, model.row()))

    def insert_capture(self, model) -> "CaptureRef":
        """Insert a capture and get a ref whose id resolves after the write."""
        ref = CaptureRef()
        self._q.put(("insert_capture", model.table, model.row(), ref))
        return ref

    def update_caption(self, capture_id: int, desc: str, described_at: float):
        self._q.put(("update_caption", capture_id, desc, described_at))

    def stop(self):
        self._q.put((_SENTINEL,))

    # --- consumer loop ---

    def run(self):
        n = 0
        while True:
            item = self._q.get()
            if item[0] is _SENTINEL:
                self._conn.commit()
                break
            try:
                self._apply(item)
                n += 1
                if n % self._flush_every == 0:
                    self._conn.commit()
            except Exception:
                pass  # never let one bad row kill the writer

    def _apply(self, item):
        op = item[0]
        if op == "insert":
            _, table, data = item
            self._insert(table, data)
        elif op == "insert_capture":
            _, table, data, ref = item
            cur = self._insert(table, data)
            ref.set(cur.lastrowid)
        elif op == "update_caption":
            _, cid, desc, described_at = item
            self._conn.execute(
                "UPDATE screen_capture SET desc=?, described_at=? WHERE id=?",
                (desc, described_at, cid),
            )

    def _insert(self, table, data):
        cols = ",".join(data.keys())
        ph = ",".join("?" for _ in data)
        return self._conn.execute(
            f"INSERT INTO {table} ({cols}) VALUES ({ph})", tuple(data.values())
        )


class CaptureRef:
    """Resolves to a capture row id once the writer has inserted it."""

    def __init__(self):
        self._id = None
        self._ev = threading.Event()

    def set(self, cid):
        self._id = cid
        self._ev.set()

    def get(self, timeout: float = 5.0):
        self._ev.wait(timeout)
        return self._id
