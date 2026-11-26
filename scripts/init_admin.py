from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from api.config import get_settings
from api.models import Base, User
from api.security import hash_password_werkzeug


def init_admin(login: str = "admin", password: str = "admin123") -> None:
    settings = get_settings()
    engine = create_engine(settings.sync_database_url)
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        user = session.execute(select(User).where(User.login == login)).scalar_one_or_none()
        werkzeug_hash = hash_password_werkzeug(password)
        if user:
            user.pwd_hash = werkzeug_hash
            user.salt = ""
            user.role = "admin"
            user.is_active = True
            action = "updated"
        else:
            user = User(
                login=login,
                salt="",
                pwd_hash=werkzeug_hash,
                role="admin",
                is_active=True,
                subscription_status="none",
            )
            session.add(user)
            action = "created"
        session.commit()
        print(f"Admin user '{login}' {action} (id={user.id}).")

    engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or update the first admin user.")
    parser.add_argument("--login", default="admin")
    parser.add_argument("--password", default="admin123")
    args = parser.parse_args()
    init_admin(login=args.login, password=args.password)


if __name__ == "__main__":
    main()
