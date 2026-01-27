"""Репозитории пользователей/сессий/инвайтов на SQLite."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from app.infrastructure.persistence.app_db import db_cursor, fetch_all, fetch_one
from app.infrastructure.auth.security import new_id, utcnow_iso, expires_iso


@dataclass(frozen=True)
class User:
    id: str
    username: str
    password_hash: str
    role: str
    is_active: bool
    created_at: str
    last_login_at: Optional[str] = None


def ensure_db_safe() -> None:
    """
    Не инициализируем БД на import-time (в dev sandbox может быть запрещено писать в data/).
    В реальном запуске init_db будет вызываться из main lifespan.
    """
    try:
        from app.infrastructure.persistence.app_db import init_db
        init_db()
    except Exception as e:
        # Не падаем на import, но логируем
        logger.warning(f"Auth DB init skipped/failed: {e}")


def get_user_by_username(username: str) -> Optional[User]:
    ensure_db_safe()
    with db_cursor() as cur:
        row = fetch_one(cur, "SELECT * FROM users WHERE username = ?", (username,))
        if not row:
            return None
        return User(
            id=row["id"],
            username=row["username"],
            password_hash=row["password_hash"],
            role=row["role"],
            is_active=bool(row["is_active"]),
            created_at=row["created_at"],
            last_login_at=row.get("last_login_at"),
        )


def get_user_by_id(user_id: str) -> Optional[User]:
    ensure_db_safe()
    with db_cursor() as cur:
        row = fetch_one(cur, "SELECT * FROM users WHERE id = ?", (user_id,))
        if not row:
            return None
        return User(
            id=row["id"],
            username=row["username"],
            password_hash=row["password_hash"],
            role=row["role"],
            is_active=bool(row["is_active"]),
            created_at=row["created_at"],
            last_login_at=row.get("last_login_at"),
        )


def create_user(username: str, password_hash: str, role: str = "user") -> User:
    ensure_db_safe()
    user_id = new_id()
    now = utcnow_iso()
    with db_cursor() as cur:
        cur.execute(
            "INSERT INTO users(id, username, password_hash, role, is_active, created_at) VALUES (?, ?, ?, ?, 1, ?)",
            (user_id, username, password_hash, role, now),
        )
    return User(
        id=user_id,
        username=username,
        password_hash=password_hash,
        role=role,
        is_active=True,
        created_at=now,
        last_login_at=None,
    )


def create_invite(role: str, expires_at: str, code: Optional[str] = None) -> str:
    ensure_db_safe()
    invite_code = code or new_id().replace("-", "")[:12]
    with db_cursor() as cur:
        cur.execute(
            "INSERT INTO invites(code, role, expires_at) VALUES (?, ?, ?)",
            (invite_code, role, expires_at),
        )
    return invite_code


def get_invite(code: str) -> Optional[Dict[str, Any]]:
    ensure_db_safe()
    with db_cursor() as cur:
        return fetch_one(cur, "SELECT * FROM invites WHERE code = ?", (code,))


def mark_invite_used(code: str, user_id: str) -> None:
    ensure_db_safe()
    with db_cursor() as cur:
        cur.execute(
            "UPDATE invites SET used_by_user_id = ?, used_at = ? WHERE code = ? AND used_at IS NULL",
            (user_id, utcnow_iso(), code),
        )


def set_last_login(user_id: str) -> None:
    ensure_db_safe()
    with db_cursor() as cur:
        cur.execute("UPDATE users SET last_login_at = ? WHERE id = ?", (utcnow_iso(), user_id))


def set_user_role(username: str, role: str) -> bool:
    ensure_db_safe()
    with db_cursor() as cur:
        cur.execute("UPDATE users SET role = ? WHERE username = ?", (role, username))
        return cur.rowcount > 0


def set_user_password_hash(username: str, password_hash: str) -> bool:
    ensure_db_safe()
    with db_cursor() as cur:
        cur.execute("UPDATE users SET password_hash = ? WHERE username = ?", (password_hash, username))
        return cur.rowcount > 0


def create_session(user_id: str, ttl_days: int = 30) -> str:
    ensure_db_safe()
    sid = new_id()
    now = utcnow_iso()
    exp = expires_iso(days=ttl_days)
    with db_cursor() as cur:
        cur.execute(
            "INSERT INTO sessions(id, user_id, created_at, expires_at, last_seen_at) VALUES (?, ?, ?, ?, ?)",
            (sid, user_id, now, exp, now),
        )
    return sid


def delete_session(session_id: str) -> None:
    ensure_db_safe()
    with db_cursor() as cur:
        cur.execute("DELETE FROM sessions WHERE id = ?", (session_id,))


def get_session_user(session_id: str) -> Optional[User]:
    ensure_db_safe()
    with db_cursor() as cur:
        row = fetch_one(
            cur,
            """
            SELECT u.*,
                   s.expires_at AS session_expires_at
            FROM sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.id = ?
            """,
            (session_id,),
        )
        if not row:
            return None

        # Проверяем expiry (ISOZ)
        try:
            exp = row.get("session_expires_at")
            if exp:
                dt = datetime.fromisoformat(exp.replace("Z", "+00:00"))
                if dt <= datetime.now(dt.tzinfo):
                    delete_session(session_id)
                    return None
        except Exception:
            pass

        # touch
        cur.execute("UPDATE sessions SET last_seen_at = ? WHERE id = ?", (utcnow_iso(), session_id))

        return User(
            id=row["id"],
            username=row["username"],
            password_hash=row["password_hash"],
            role=row["role"],
            is_active=bool(row["is_active"]),
            created_at=row["created_at"],
            last_login_at=row.get("last_login_at"),
        )


def create_telegram_link_code(user_id: str, expires_at: str) -> str:
    ensure_db_safe()
    code = new_id().replace("-", "")[:10]
    with db_cursor() as cur:
        cur.execute(
            "INSERT INTO telegram_link_codes(code, user_id, expires_at) VALUES (?, ?, ?)",
            (code, user_id, expires_at),
        )
    return code


def get_telegram_link_code(code: str) -> Optional[Dict[str, Any]]:
    ensure_db_safe()
    with db_cursor() as cur:
        return fetch_one(cur, "SELECT * FROM telegram_link_codes WHERE code = ?", (code,))


def mark_telegram_link_code_used(code: str) -> None:
    ensure_db_safe()
    with db_cursor() as cur:
        cur.execute(
            "UPDATE telegram_link_codes SET used_at = ? WHERE code = ? AND used_at IS NULL",
            (utcnow_iso(), code),
        )


def upsert_telegram_link(user_id: str, chat_id: str, enabled: bool = True, min_priority: str = "LOW") -> None:
    ensure_db_safe()
    now = utcnow_iso()
    with db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO telegram_links(user_id, chat_id, enabled, min_priority, created_at, verified_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
              chat_id=excluded.chat_id,
              enabled=excluded.enabled,
              min_priority=excluded.min_priority,
              verified_at=excluded.verified_at
            """,
            (user_id, chat_id, 1 if enabled else 0, min_priority, now, now),
        )


def get_telegram_link(user_id: str) -> Optional[Dict[str, Any]]:
    ensure_db_safe()
    with db_cursor() as cur:
        return fetch_one(cur, "SELECT * FROM telegram_links WHERE user_id = ?", (user_id,))


def list_telegram_links(enabled_only: bool = True) -> List[Dict[str, Any]]:
    ensure_db_safe()
    with db_cursor() as cur:
        if enabled_only:
            return fetch_all(cur, "SELECT * FROM telegram_links WHERE enabled = 1", ())
        return fetch_all(cur, "SELECT * FROM telegram_links", ())


def get_poller_state() -> int:
    ensure_db_safe()
    with db_cursor() as cur:
        row = fetch_one(cur, "SELECT last_update_id FROM telegram_poller_state WHERE id = 1", ())
        return int(row["last_update_id"]) if row else 0


def set_poller_state(last_update_id: int) -> None:
    ensure_db_safe()
    with db_cursor() as cur:
        cur.execute("UPDATE telegram_poller_state SET last_update_id = ? WHERE id = 1", (int(last_update_id),))

