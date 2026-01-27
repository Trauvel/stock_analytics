"""
Bootstrap admin user in data/app.db.

Usage:
  python scripts/create_admin.py --username admin --password "secret"
  python scripts/create_admin.py --username admin --password "secret" --reset-password
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


# Добавляем корень проекта в sys.path, чтобы работали импорты `app.*`
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.infrastructure.persistence.app_db import init_db
from app.infrastructure.auth.security import hash_password
from app.infrastructure.auth.repositories import (
    get_user_by_username,
    create_user,
    set_user_role,
    set_user_password_hash,
)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--username", required=True)
    p.add_argument("--password", required=True)
    p.add_argument("--reset-password", action="store_true", help="Reset password if user exists")
    args = p.parse_args()

    init_db()

    u = get_user_by_username(args.username)
    if not u:
        create_user(args.username, hash_password(args.password), role="admin")
        print(f"OK: created admin user '{args.username}'")
        return 0

    # promote to admin
    set_user_role(args.username, "admin")
    if args.reset_password:
        set_user_password_hash(args.username, hash_password(args.password))
        print(f"OK: promoted to admin and reset password for '{args.username}'")
    else:
        print(f"OK: promoted to admin '{args.username}' (password unchanged; use --reset-password to change)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

