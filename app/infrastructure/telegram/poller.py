"""Polling Telegram getUpdates для привязки чатов по коду."""

from __future__ import annotations

import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import requests
from loguru import logger

from app.infrastructure.auth.repositories import (
    get_telegram_link_code,
    mark_telegram_link_code_used,
    upsert_telegram_link,
    get_poller_state,
    set_poller_state,
)


LINK_RE = re.compile(r"^/link\s+([A-Za-z0-9]{6,32})\s*$", re.IGNORECASE)


def _bot_token() -> Optional[str]:
    return os.getenv("TELEGRAM_BOT_TOKEN")


def poll_once(timeout_sec: int = 10) -> int:
    """
    Один цикл polling getUpdates.

    Returns:
        int: сколько обновлений обработано
    """
    token = _bot_token()
    if not token:
        return 0

    offset = get_poller_state() + 1
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    try:
        resp = requests.get(url, params={"timeout": timeout_sec, "offset": offset}, timeout=timeout_sec + 5)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("ok"):
            return 0
        updates = data.get("result") or []
        processed = 0
        max_update_id = None
        for upd in updates:
            processed += 1
            uid = upd.get("update_id")
            if uid is not None:
                max_update_id = uid if max_update_id is None else max(max_update_id, uid)

            msg = upd.get("message") or upd.get("edited_message") or {}
            text = (msg.get("text") or "").strip()
            chat = msg.get("chat") or {}
            chat_id = chat.get("id")
            if not text or not chat_id:
                continue

            m = LINK_RE.match(text)
            if not m:
                continue
            code = m.group(1)

            rec = get_telegram_link_code(code)
            if not rec:
                continue
            if rec.get("used_at"):
                continue

            # expiry
            try:
                exp = datetime.fromisoformat(str(rec["expires_at"]).replace("Z", "+00:00"))
                if exp <= datetime.now(timezone.utc):
                    continue
            except Exception:
                continue

            user_id = rec["user_id"]
            upsert_telegram_link(user_id=user_id, chat_id=str(chat_id), enabled=True, min_priority="LOW")
            mark_telegram_link_code_used(code)
            logger.info(f"Telegram linked: user_id={user_id} chat_id={chat_id}")

        if max_update_id is not None:
            set_poller_state(int(max_update_id))
        return processed
    except Exception as e:
        logger.debug(f"Telegram poll error: {e}")
        return 0

