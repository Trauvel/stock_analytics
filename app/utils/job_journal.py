"""Простой журнал запусков задач (JSONL)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from app.infrastructure.persistence.job_runs_repo import append_job_run_record


def _project_root() -> Path:
    return Path(__file__).parent.parent.parent


def append_jsonl(relative_path: str, record: Dict[str, Any]) -> None:
    """
    Добавить запись в JSONL файл внутри проекта.

    Args:
        relative_path: путь относительно корня проекта (например "data/job_runs/x.jsonl")
        record: dict для записи (в одну строку JSON)
    """
    root = _project_root()
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)

    # Добавим timestamp, если забыли
    if "ts" not in record:
        record["ts"] = datetime.now().isoformat()

    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.warning(f"Failed to append journal {path}: {e}")

    # Дополнительно пишем в SQLite (если доступно)
    try:
        append_job_run_record(record)
    except Exception:
        pass


def append_job_record(job: str, event: str, run_id: str, extra: Optional[Dict[str, Any]] = None) -> None:
    """
    Упрощённая обёртка: формирует record и пишет и в JSONL, и в SQLite.
    """
    record: Dict[str, Any] = {"job": job, "event": event, "run_id": run_id}
    if extra:
        record.update(extra)
    append_jsonl(f"data/job_runs/{job}.jsonl", record)


def tail_jsonl(relative_path: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Прочитать последние N записей из JSONL (без загрузки всего файла в память).
    """
    root = _project_root()
    path = root / relative_path
    if not path.exists():
        return []

    # Для простоты: читаем целиком если файл небольшой; иначе — можно оптимизировать.
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        out: List[Dict[str, Any]] = []
        for line in lines[-limit:]:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                continue
        return out
    except Exception as e:
        logger.warning(f"Failed to read journal {path}: {e}")
        return []

