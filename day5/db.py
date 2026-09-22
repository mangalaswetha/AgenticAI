"""SQLite helpers for the students database."""

from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "students.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def fetch_student(student_id: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM students WHERE student_id = ?",
            (student_id.strip().upper(),),
        ).fetchone()
        if row is None:
            # try original casing
            row = conn.execute(
                "SELECT * FROM students WHERE student_id = ?",
                (student_id.strip(),),
            ).fetchone()
        return dict(row) if row else None
