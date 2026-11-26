from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select

from api.db import SessionLocal, engine
from api.models import Archetype, Base, User
from api.security import hash_password


ARCHETYPES = [
    {"slug": "divers", "name": "Divers", "description": "???????"},
    {"slug": "brawlers", "name": "Brawlers", "description": "????????"},
    {"slug": "pokers", "name": "Pokers", "description": "???????"},
    {"slug": "universals", "name": "Universals", "description": "??????????"},
]

DEMO_USERS = [
    {"login": "admin", "password": "admin123", "role": "admin"},
    {"login": "student", "password": "student123", "role": "user"},
    {"login": "guest", "password": "guest123", "role": "user"},
]


async def seed(recreate: bool = False) -> None:
    if recreate:
        # Explicitly allowed by project brief for dev DB reset via this script.
        db_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/app.db")
        if db_url.startswith("sqlite+aiosqlite:///"):
            db_path = db_url.replace("sqlite+aiosqlite:///", "", 1)
            p = Path(db_path)
            if not p.is_absolute():
                p = (ROOT / p).resolve()
            for suffix in ("", "-wal", "-shm"):
                fp = Path(str(p) + suffix)
                if fp.exists():
                    fp.unlink()
                    print(f"Removed {fp}")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    else:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as session:
        for data in ARCHETYPES:
            result = await session.execute(select(Archetype).where(Archetype.slug == data["slug"]))
            obj = result.scalar_one_or_none()
            if obj:
                obj.name = data["name"]
                obj.description = data["description"]
            else:
                session.add(Archetype(**data))

        for data in DEMO_USERS:
            result = await session.execute(select(User).where(User.login == data["login"]))
            user = result.scalar_one_or_none()
            salt, pwd_hash = hash_password(data["password"])
            if user:
                user.salt = salt
                user.pwd_hash = pwd_hash
                user.role = data["role"]
                user.is_active = True
            else:
                session.add(
                    User(
                        login=data["login"],
                        salt=salt,
                        pwd_hash=pwd_hash,
                        role=data["role"],
                        is_active=True,
                        subscription_status="none",
                    )
                )
        await session.commit()
    print("Seed completed.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--recreate", action="store_true", help="Recreate dev DB before seeding")
    args = parser.parse_args()
    asyncio.run(seed(recreate=args.recreate))


if __name__ == "__main__":
    main()
