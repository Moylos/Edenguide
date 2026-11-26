import asyncio
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from api.config import get_settings
from api.db import get_session
from api.main import create_app
from api.models import Base, User
from api.security import hash_password


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def test_db(tmp_path: Path):
    db_path = tmp_path / "test.db"
    db_url = f"sqlite+aiosqlite:///{db_path.as_posix()}"
    engine = create_async_engine(db_url, connect_args={"check_same_thread": False})

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        yield session_factory
    finally:
        await engine.dispose()


@pytest.fixture
async def seed_users(test_db):
    async with test_db() as session:
        users = [
            User(login="admin", role="admin", is_active=True, subscription_status="none",
                 **dict(zip(["salt", "pwd_hash"], hash_password("admin123")))),
            User(login="student", role="user", is_active=True, subscription_status="none",
                 **dict(zip(["salt", "pwd_hash"], hash_password("student123")))),
            User(login="guest", role="user", is_active=True, subscription_status="none",
                 **dict(zip(["salt", "pwd_hash"], hash_password("guest123")))),
        ]
        session.add_all(users)
        await session.commit()
    return test_db


@pytest.fixture
async def client(test_db, monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")
    get_settings.cache_clear()

    app = create_app()

    async def override_get_session():
        async with test_db() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    app.dependency_overrides.clear()
    get_settings.cache_clear()
