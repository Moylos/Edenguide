from collections.abc import AsyncGenerator

from sqlalchemy import create_engine as create_sync_engine, event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session, sessionmaker

from api.config import get_settings


def create_engine(database_url: str | None = None) -> AsyncEngine:
    """Create an async SQLAlchemy engine. Enables SQLite pragmas when needed."""
    url = database_url or get_settings().database_url
    connect_args: dict = {}
    engine_kwargs: dict = {"echo": False}

    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    else:
        # Avoid long hangs when PostgreSQL is unavailable in local/dev.
        connect_args["timeout"] = 5
        engine_kwargs["pool_timeout"] = 5
        engine_kwargs["pool_pre_ping"] = True

    engine_kwargs["connect_args"] = connect_args
    async_engine = create_async_engine(url, **engine_kwargs)

    if url.startswith("sqlite"):
        @event.listens_for(async_engine.sync_engine, "connect")
        def _set_sqlite_pragmas(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return async_engine


def create_session_factory(async_engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(async_engine, expire_on_commit=False, class_=AsyncSession)


engine: AsyncEngine = create_engine()
SessionLocal = create_session_factory(engine)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


# --- Sync engine/session for Flask-Admin (runs in WSGI context) ---

_sync_engine = None
_SyncSessionLocal = None


def get_sync_engine():
    global _sync_engine
    if _sync_engine is None:
        url = get_settings().sync_database_url
        connect_args: dict = {}
        engine_kwargs: dict = {"echo": False}
        if url.startswith("sqlite"):
            connect_args["check_same_thread"] = False
        else:
            connect_args["connect_timeout"] = 5
            engine_kwargs["pool_timeout"] = 5
            engine_kwargs["pool_pre_ping"] = True
        engine_kwargs["connect_args"] = connect_args
        _sync_engine = create_sync_engine(url, **engine_kwargs)
        if url.startswith("sqlite"):
            @event.listens_for(_sync_engine, "connect")
            def _set_sqlite_pragmas(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()
    return _sync_engine


def get_sync_session_factory():
    global _SyncSessionLocal
    if _SyncSessionLocal is None:
        _SyncSessionLocal = sessionmaker(
            bind=get_sync_engine(),
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
            class_=Session,
        )
    return _SyncSessionLocal
