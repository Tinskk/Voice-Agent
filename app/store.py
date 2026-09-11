"""SQLite-backed tool-call dedupe + short-term per-call scratch state.

Known tradeoff (see README.md): on Render's default disk this file does not
survive a redeploy or restart, resetting dedupe state. Acceptable for v1 —
each call's full context also lives in Vapi for the duration of that call
regardless, and dedupe only matters for retries within a single live call.

Idempotency matters more here than in a simple chat bot: a duplicate
`create_order`/`book_appointment` from a Vapi retry would be a real
double-write, not just a UI glitch, so every tool call is deduped by
`toolCallId` before dispatch.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

import config

_SCHEMA = """
CREATE TABLE IF NOT EXISTS seen_tool_calls (
    tool_call_id TEXT PRIMARY KEY,
    result_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS call_sessions (
    call_id TEXT PRIMARY KEY,
    customer_number TEXT,
    session_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


def _db_path() -> Path:
    path = Path(config.AGENT_DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(_db_path())
    try:
        conn.executescript(_SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def get_cached_result(tool_call_id: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT result_json FROM seen_tool_calls WHERE tool_call_id = ?", (tool_call_id,)
        ).fetchone()
        return json.loads(row[0]) if row else None


def cache_result(tool_call_id: str, result: dict) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO seen_tool_calls (tool_call_id, result_json, created_at) VALUES (?, ?, ?)",
            (tool_call_id, json.dumps(result, default=str), datetime.now(timezone.utc).isoformat()),
        )


def get_session(call_id: str) -> dict:
    with _connect() as conn:
        row = conn.execute(
            "SELECT session_json FROM call_sessions WHERE call_id = ?", (call_id,)
        ).fetchone()
        return json.loads(row[0]) if row else {}


def save_session(call_id: str, customer_number: str | None, session: dict) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO call_sessions (call_id, customer_number, session_json, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(call_id) DO UPDATE SET
                customer_number = excluded.customer_number,
                session_json = excluded.session_json,
                updated_at = excluded.updated_at
            """,
            (call_id, customer_number, json.dumps(session, default=str), datetime.now(timezone.utc).isoformat()),
        )
