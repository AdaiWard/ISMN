from __future__ import annotations

import argparse
import getpass

from sqlalchemy import select

from app.core.security import hash_password
from app.db.models import Role, User
from app.db.session import SessionLocal


def main() -> None:
    parser = argparse.ArgumentParser(description="Create the first ISMN administrator")
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", help="Avoid this option in shared shell history; omit for a secure prompt")
    args = parser.parse_args()
    password = args.password or getpass.getpass("New administrator password: ")
    if len(password) < 12:
        raise SystemExit("Password must contain at least 12 characters")
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.username == args.username)):
            raise SystemExit("User already exists")
        user = User(username=args.username, password_hash=hash_password(password), role=Role.admin.value)
        db.add(user)
        db.commit()
        print(f"Administrator '{args.username}' created. No password was printed or stored in plaintext.")


if __name__ == "__main__":
    main()

