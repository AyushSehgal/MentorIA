"""SQLite persistence. Tables store a JSON document plus a few indexed columns."""
from __future__ import annotations

import json
import sqlite3
import threading
from typing import Any, Iterable, Optional

from .config import settings

_lock = threading.RLock()
_conn: Optional[sqlite3.Connection] = None
_conn_path: Optional[str] = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS source_records (
  id TEXT PRIMARY KEY, student_id TEXT, provider TEXT, external_id TEXT, kind TEXT, data TEXT,
  UNIQUE(student_id, provider, external_id));
CREATE TABLE IF NOT EXISTS observations (
  event_id TEXT PRIMARY KEY, student_id TEXT, concept_id TEXT, event_type TEXT, occurred_at TEXT, data TEXT);
CREATE TABLE IF NOT EXISTS beliefs (id TEXT PRIMARY KEY, student_id TEXT, key TEXT, data TEXT);
CREATE TABLE IF NOT EXISTS belief_updates (seq INTEGER PRIMARY KEY AUTOINCREMENT, student_id TEXT, data TEXT);
CREATE TABLE IF NOT EXISTS propositions (id TEXT PRIMARY KEY, student_id TEXT, data TEXT);
CREATE TABLE IF NOT EXISTS recommendations (id TEXT PRIMARY KEY, student_id TEXT, status TEXT, data TEXT);
CREATE TABLE IF NOT EXISTS documents (id TEXT PRIMARY KEY, student_id TEXT, data TEXT);
CREATE TABLE IF NOT EXISTS doc_pages (doc_id TEXT, student_id TEXT, page INTEGER, text TEXT, PRIMARY KEY(doc_id, page));
CREATE TABLE IF NOT EXISTS connector_status (provider TEXT PRIMARY KEY, data TEXT);
CREATE TABLE IF NOT EXISTS action_log (id TEXT PRIMARY KEY, recommendation_id TEXT UNIQUE, data TEXT);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
"""

TABLES = ["source_records", "observations", "beliefs", "belief_updates", "propositions",
          "recommendations", "documents", "doc_pages", "connector_status", "action_log", "meta"]


def conn() -> sqlite3.Connection:
    global _conn, _conn_path
    path = str(settings.db_path)
    with _lock:
        if _conn is None or _conn_path != path:
            settings.db_path.parent.mkdir(parents=True, exist_ok=True)
            _conn = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
            _conn.row_factory = sqlite3.Row
            _conn.execute("PRAGMA journal_mode=WAL")
            _conn.executescript(SCHEMA)
            _conn_path = path
        return _conn


def close() -> None:
    global _conn, _conn_path
    with _lock:
        if _conn is not None:
            _conn.close()
        _conn, _conn_path = None, None


def execute(sql: str, params: Iterable[Any] = ()) -> sqlite3.Cursor:
    with _lock:
        return conn().execute(sql, tuple(params))


def query(sql: str, params: Iterable[Any] = ()) -> list[sqlite3.Row]:
    with _lock:
        return conn().execute(sql, tuple(params)).fetchall()


def dumps(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, default=str)


def loads(s: str) -> Any:
    return json.loads(s)


def reset_all() -> None:
    with _lock:
        for t in TABLES:
            if t == "meta":
                conn().execute("DELETE FROM meta WHERE key != 'llm_mode'")  # the user's privacy choice survives a demo reset
            else:
                conn().execute(f"DELETE FROM {t}")


def bump_state_version() -> int:
    with _lock:
        v = get_state_version() + 1
        conn().execute("INSERT OR REPLACE INTO meta(key, value) VALUES('state_version', ?)", (str(v),))
        return v


def get_state_version() -> int:
    rows = query("SELECT value FROM meta WHERE key='state_version'")
    return int(rows[0]["value"]) if rows else 0


def ping() -> bool:
    try:
        query("SELECT 1")
        return True
    except Exception:
        return False
