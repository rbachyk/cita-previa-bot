import sqlite3
from pathlib import Path
from app.config import DB_PATH


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def setup_database() -> None:
    conn = get_connection()
    with conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS discovery_runs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id      TEXT NOT NULL,
                step        INTEGER NOT NULL,
                url         TEXT,
                page_title  TEXT,
                saved_at    TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS monitor_checks (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                checked_at  TEXT NOT NULL DEFAULT (datetime('now')),
                status      TEXT NOT NULL,
                slots_found INTEGER NOT NULL DEFAULT 0,
                raw_json    TEXT
            );

            CREATE TABLE IF NOT EXISTS notifications_sent (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                sent_at     TEXT NOT NULL DEFAULT (datetime('now')),
                message     TEXT NOT NULL
            );
        """)
    conn.close()
    print(f"[db] Database ready at {DB_PATH}")
