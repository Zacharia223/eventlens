"""Persistence for generated reports.

Tries MySQL first; if the database is unreachable, transparently falls back to
an in-memory store so EventLens keeps working (reports just don't survive a
restart). Use :func:`storage_status` to tell the user which mode is active.
"""

from __future__ import annotations

import json
import threading
from datetime import datetime
from typing import Any

import pymysql

import db

# ---------------------------------------------------------------------------
# In-memory fallback store
# ---------------------------------------------------------------------------
_lock = threading.Lock()
_memory: dict[int, dict[str, Any]] = {}
_next_id = 1

# Set to True once init() confirms MySQL is usable.
_mysql_ok = False


def init() -> bool:
    """Probe the database. Returns True if MySQL persistence is available."""
    global _mysql_ok
    try:
        db.init_db()
        _mysql_ok = True
    except Exception as exc:  # noqa: BLE001 - any failure means "no MySQL"
        _mysql_ok = False
        print(f"[storage] MySQL unavailable ({exc}); using in-memory store.")
    return _mysql_ok


def storage_status() -> dict[str, Any]:
    return {"mysql": _mysql_ok, "mode": "MySQL" if _mysql_ok else "in-memory"}


def save_report(filename: str, report: dict[str, Any]) -> int:
    """Persist a report and return its id."""
    overview = report.get("overview", {})
    row_count = int(overview.get("rows", 0))
    column_count = int(overview.get("columns", 0))

    if _mysql_ok:
        try:
            return _save_mysql(filename, row_count, column_count, report)
        except pymysql.MySQLError as exc:
            print(f"[storage] save failed, falling back to memory: {exc}")

    return _save_memory(filename, row_count, column_count, report)


def list_reports(limit: int = 25) -> list[dict[str, Any]]:
    """Return recent report summaries (no full report_json), newest first."""
    if _mysql_ok:
        try:
            return _list_mysql(limit)
        except pymysql.MySQLError as exc:
            print(f"[storage] list failed: {exc}")

    with _lock:
        rows = sorted(_memory.values(), key=lambda r: r["id"], reverse=True)
    return [_summary(r) for r in rows[:limit]]


def get_report(report_id: int) -> dict[str, Any] | None:
    """Return the full stored record for ``report_id`` or None."""
    if _mysql_ok:
        try:
            return _get_mysql(report_id)
        except pymysql.MySQLError as exc:
            print(f"[storage] get failed: {exc}")

    with _lock:
        return _memory.get(report_id)


def delete_report(report_id: int) -> bool:
    if _mysql_ok:
        try:
            return _delete_mysql(report_id)
        except pymysql.MySQLError as exc:
            print(f"[storage] delete failed: {exc}")

    with _lock:
        return _memory.pop(report_id, None) is not None


# ---------------------------------------------------------------------------
# MySQL implementation
# ---------------------------------------------------------------------------
def _save_mysql(filename, row_count, column_count, report) -> int:
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO reports (filename, row_count, column_count, report_json)
                VALUES (%s, %s, %s, %s)
                """,
                (filename, row_count, column_count, json.dumps(report)),
            )
            new_id = cur.lastrowid
        conn.commit()
        return new_id
    finally:
        conn.close()


def _list_mysql(limit) -> list[dict[str, Any]]:
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, filename, uploaded_at, row_count, column_count
                FROM reports ORDER BY id DESC LIMIT %s
                """,
                (limit,),
            )
            return [_summary(row) for row in cur.fetchall()]
    finally:
        conn.close()


def _get_mysql(report_id) -> dict[str, Any] | None:
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM reports WHERE id = %s", (report_id,))
            row = cur.fetchone()
        if row is None:
            return None
        row["report"] = json.loads(row.pop("report_json"))
        return row
    finally:
        conn.close()


def _delete_mysql(report_id) -> bool:
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            affected = cur.execute("DELETE FROM reports WHERE id = %s", (report_id,))
        conn.commit()
        return affected > 0
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# In-memory implementation
# ---------------------------------------------------------------------------
def _save_memory(filename, row_count, column_count, report) -> int:
    global _next_id
    with _lock:
        report_id = _next_id
        _next_id += 1
        _memory[report_id] = {
            "id": report_id,
            "filename": filename,
            "uploaded_at": datetime.now(),
            "row_count": row_count,
            "column_count": column_count,
            "report": report,
        }
    return report_id


def _summary(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "filename": row["filename"],
        "uploaded_at": row["uploaded_at"],
        "row_count": row["row_count"],
        "column_count": row["column_count"],
    }
