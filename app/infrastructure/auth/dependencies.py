"""FastAPI зависимости для авторизации и ролей."""

from __future__ import annotations

import os
from typing import Optional

from fastapi import Cookie, Depends, HTTPException, status

from app.infrastructure.auth.repositories import User, get_session_user


SESSION_COOKIE_NAME = "sa_session"


def users_auth_enabled() -> bool:
    return os.getenv("AUTH_USERS_ENABLED", "false").lower() == "true"


def get_current_user(session_id: Optional[str] = Cookie(default=None, alias=SESSION_COOKIE_NAME)) -> Optional[User]:
    if not users_auth_enabled():
        return None
    if not session_id:
        return None
    return get_session_user(session_id)


def require_user(user: Optional[User] = Depends(get_current_user)) -> User:
    if not users_auth_enabled():
        # В режиме без пользователей эндпоинты auth не используются
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Users auth is disabled")
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return user


def require_admin(user: User = Depends(require_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    return user

