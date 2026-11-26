from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    secret_key: str = "change-me-in-production"
    # PostgreSQL is the target DB. For local dev you can override with SQLite, e.g.:
    # DATABASE_URL=sqlite+aiosqlite:///./data/app.db
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/edenguide"
    telegram_bot_token: str = ""
    telegram_admin_chat_id: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def sync_database_url(self) -> str:
        """Sync SQLAlchemy URL for Alembic/Flask-Admin."""
        url = self.database_url
        if url.startswith("sqlite+aiosqlite"):
            return url.replace("sqlite+aiosqlite", "sqlite", 1)
        if url.startswith("postgresql+asyncpg"):
            return url.replace("postgresql+asyncpg", "postgresql+psycopg", 1)
        if url.startswith("postgres+asyncpg"):
            return url.replace("postgres+asyncpg", "postgresql+psycopg", 1)
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()
