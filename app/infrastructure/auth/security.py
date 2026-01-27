"""Хэширование паролей и утилиты безопасности (без внешних зависимостей)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4


PBKDF2_ALGO = "sha256"
PBKDF2_ITERS = 210_000
SALT_BYTES = 16


def hash_password(password: str) -> str:
    salt = os.urandom(SALT_BYTES)
    dk = hashlib.pbkdf2_hmac(PBKDF2_ALGO, password.encode("utf-8"), salt, PBKDF2_ITERS)
    return "pbkdf2_{algo}${iters}${salt}${hash}".format(
        algo=PBKDF2_ALGO,
        iters=PBKDF2_ITERS,
        salt=base64.urlsafe_b64encode(salt).decode("ascii"),
        hash=base64.urlsafe_b64encode(dk).decode("ascii"),
    )


def verify_password(password: str, password_hash: str) -> bool:
    try:
        scheme, iters, salt_b64, hash_b64 = password_hash.split("$", 3)
        if not scheme.startswith("pbkdf2_"):
            return False
        algo = scheme.replace("pbkdf2_", "")
        iters_i = int(iters)
        salt = base64.urlsafe_b64decode(salt_b64.encode("ascii"))
        expected = base64.urlsafe_b64decode(hash_b64.encode("ascii"))
        dk = hashlib.pbkdf2_hmac(algo, password.encode("utf-8"), salt, iters_i)
        return hmac.compare_digest(dk, expected)
    except Exception:
        return False


def new_id() -> str:
    return str(uuid4())


def utcnow_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def expires_iso(days: int = 30) -> str:
    dt = datetime.utcnow() + timedelta(days=days)
    return dt.replace(microsecond=0).isoformat() + "Z"

