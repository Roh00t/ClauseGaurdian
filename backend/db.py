"""
backend/db.py
Single-file SQLite for ClauseGuard v2 — one data/data.db, three tables.

All connections use check_same_thread=False + timeout=10 so concurrent
requests under uvicorn don't hit "database is locked" (PM7). Every query
elsewhere must use parameterised statements (RT8).
"""
import os
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "data.db"


def get_conn() -> sqlite3.Connection:
    """Return a SQLite connection safe to use from FastAPI worker threads."""
    os.makedirs(DB_PATH.parent, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create all three tables if they don't already exist (idempotent — PM10)."""
    conn = get_conn()
    try:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS regulations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL UNIQUE,
                title TEXT,
                content TEXT,
                category TEXT,
                scraped_at TEXT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                created_at TEXT,
                filenames TEXT,
                doc_count INTEGER,
                overall_severity TEXT,
                analysis TEXT,
                regulation_source TEXT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS scrape_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT,
                status TEXT,
                method TEXT,
                chars INTEGER,
                scraped_at TEXT
            )
        """)
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
    print(f"DB ok -> {DB_PATH}")
