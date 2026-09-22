"""Recreate students.db with the assignment data."""

from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "students.db"

ROWS = [
    ("22CS045", "Dhanushya", "Computer Science", 85, 72, 90, 78),
    ("22CS046", "Rahul", "Computer Science", 65, 70, 68, 72),
    ("22CS047", "Priya", "Information Technology", 92, 88, 95, 90),
    ("22CS048", "Arun", "Information Technology", 55, 60, 58, 62),
    ("22CS049", "Meena", "Computer Science", 78, 85, 80, 88),
]


def main() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE students (
            student_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            department TEXT NOT NULL,
            python INTEGER,
            database INTEGER,
            ai INTEGER,
            web INTEGER
        )
        """
    )
    conn.executemany("INSERT INTO students VALUES (?,?,?,?,?,?,?)", ROWS)
    conn.commit()
    conn.close()
    print(f"Created {DB_PATH} with {len(ROWS)} students.")


if __name__ == "__main__":
    main()
