"""Минимальный SQLite слой для auth/настроек/журнала."""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

from loguru import logger


def _project_root() -> Path:
    return Path(__file__).parent.parent.parent.parent


def get_db_path() -> Path:
    # Можно переопределить через env
    p = os.getenv("APP_DB_PATH", "data/app.db")
    return _project_root() / p


def connect() -> sqlite3.Connection:
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # Включаем FK
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


@contextmanager
def db_cursor() -> Iterator[sqlite3.Cursor]:
    conn = connect()
    try:
        cur = conn.cursor()
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Создать таблицы, если их нет."""
    with db_cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
              id TEXT PRIMARY KEY,
              username TEXT UNIQUE NOT NULL,
              password_hash TEXT NOT NULL,
              role TEXT NOT NULL,
              is_active INTEGER NOT NULL DEFAULT 1,
              created_at TEXT NOT NULL,
              last_login_at TEXT
            );
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS invites (
              code TEXT PRIMARY KEY,
              role TEXT NOT NULL,
              expires_at TEXT NOT NULL,
              used_by_user_id TEXT,
              used_at TEXT,
              FOREIGN KEY (used_by_user_id) REFERENCES users(id)
            );
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
              id TEXT PRIMARY KEY,
              user_id TEXT NOT NULL,
              created_at TEXT NOT NULL,
              expires_at TEXT NOT NULL,
              last_seen_at TEXT NOT NULL,
              FOREIGN KEY (user_id) REFERENCES users(id)
            );
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS user_settings (
              user_id TEXT PRIMARY KEY,
              json TEXT NOT NULL,
              FOREIGN KEY (user_id) REFERENCES users(id)
            );
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS telegram_links (
              user_id TEXT PRIMARY KEY,
              chat_id TEXT NOT NULL,
              enabled INTEGER NOT NULL DEFAULT 1,
              min_priority TEXT NOT NULL DEFAULT 'LOW',
              created_at TEXT NOT NULL,
              verified_at TEXT,
              FOREIGN KEY (user_id) REFERENCES users(id)
            );
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS telegram_link_codes (
              code TEXT PRIMARY KEY,
              user_id TEXT NOT NULL,
              expires_at TEXT NOT NULL,
              used_at TEXT,
              FOREIGN KEY (user_id) REFERENCES users(id)
            );
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS job_runs (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              job TEXT NOT NULL,
              event TEXT NOT NULL,
              run_id TEXT NOT NULL,
              success INTEGER,
              user_id TEXT,
              role TEXT,
              payload_json TEXT,
              ts TEXT NOT NULL,
              FOREIGN KEY (user_id) REFERENCES users(id)
            );
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS telegram_poller_state (
              id INTEGER PRIMARY KEY CHECK (id = 1),
              last_update_id INTEGER NOT NULL DEFAULT 0
            );
            """
        )
        # ensure row exists
        cur.execute("INSERT OR IGNORE INTO telegram_poller_state(id, last_update_id) VALUES (1, 0);")

    logger.info(f"SQLite app db initialized at {get_db_path()}")


def fetch_one(cur: sqlite3.Cursor, sql: str, params: Tuple[Any, ...] = ()) -> Optional[Dict[str, Any]]:
    cur.execute(sql, params)
    row = cur.fetchone()
    return dict(row) if row else None


def fetch_all(cur: sqlite3.Cursor, sql: str, params: Tuple[Any, ...] = ()) -> List[Dict[str, Any]]:
    cur.execute(sql, params)
    rows = cur.fetchall()
    return [dict(r) for r in rows]

