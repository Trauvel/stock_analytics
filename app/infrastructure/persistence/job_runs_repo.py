"""Запись/чтение журнала запусков задач в SQLite (data/app.db)."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from app.infrastructure.persistence.app_db import db_cursor, fetch_all


def append_job_run_record(record: Dict[str, Any]) -> None:
    """
    Сохраняет запись в таблицу job_runs.

    В record ожидаются ключи: job, event, run_id, ts (и опционально success/user_id/role).
    """
    try:
        job = str(record.get("job") or "")
        event = str(record.get("event") or "")
        run_id = str(record.get("run_id") or "")
        ts = str(record.get("ts") or "")
        if not (job and event and run_id and ts):
            return

        success = record.get("success")
        if success is None:
            success_i = None
        else:
            success_i = 1 if bool(success) else 0

        user_id = record.get("user_id")
        role = record.get("role")

        payload_json = json.dumps(record, ensure_ascii=False)

        with db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO job_runs(job, event, run_id, success, user_id, role, payload_json, ts)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job,
                    event,
                    run_id,
                    success_i,
                    str(user_id) if user_id else None,
                    str(role) if role else None,
                    payload_json,
                    ts,
                ),
            )
    except Exception as e:
        logger.debug(f"Failed to append job_run to SQLite: {e}")


def query_job_run_records(
    job: Optional[str],
    limit: int = 50,
    user_id: Optional[str] = None,
    include_all_users: bool = False,
) -> List[Dict[str, Any]]:
    """
    Возвращает список исходных record dict (распакованных из payload_json), отсортированных по времени.
    """
    limit = max(1, min(500, int(limit)))
    try:
        sql = "SELECT payload_json FROM job_runs"
        params: List[Any] = []
        where: List[str] = []
        if job:
            where.append("job = ?")
            params.append(job)
        if (user_id is not None) and (not include_all_users):
            where.append("user_id = ?")
            params.append(user_id)
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY ts DESC, id DESC LIMIT ?"
        params.append(limit)

        with db_cursor() as cur:
            rows = fetch_all(cur, sql, tuple(params))

        out: List[Dict[str, Any]] = []
        for r in rows:
            try:
                payload = json.loads(r.get("payload_json") or "{}")
                if isinstance(payload, dict):
                    out.append(payload)
            except Exception:
                continue
        return out
    except Exception as e:
        logger.debug(f"Failed to query job_runs from SQLite: {e}")
        return []

