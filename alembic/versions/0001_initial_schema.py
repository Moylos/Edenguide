"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-05-20 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001_initial_schema"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(insp, name: str) -> bool:
    return name in insp.get_table_names()


def _has_column(insp, table: str, column: str) -> bool:
    return any(c["name"] == column for c in insp.get_columns(table))


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if not _has_table(insp, "users"):
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("login", sa.String(length=64), nullable=False),
            sa.Column("email", sa.String(length=255), nullable=True),
            sa.Column("salt", sa.String(length=64), nullable=False),
            sa.Column("pwd_hash", sa.String(length=128), nullable=False),
            sa.Column("role", sa.String(length=32), nullable=False, server_default="user"),
            sa.Column("telegram_id", sa.String(length=64), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("subscription_status", sa.String(length=32), nullable=False, server_default="none"),
            sa.Column("subscription_until", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.UniqueConstraint("login", name="uq_users_login"),
        )
        op.create_index("ix_users_login", "users", ["login"], unique=False)
    else:
        # Preserve existing users/passwords; extend schema if needed.
        existing_cols = {c["name"] for c in insp.get_columns("users")}
        additions = [
            ("email", sa.Column("email", sa.String(length=255), nullable=True)),
            ("telegram_id", sa.Column("telegram_id", sa.String(length=64), nullable=True)),
            ("is_active", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true())),
            ("subscription_status", sa.Column("subscription_status", sa.String(length=32), nullable=False, server_default="none")),
            ("subscription_until", sa.Column("subscription_until", sa.DateTime(timezone=True), nullable=True)),
            ("created_at", sa.Column("created_at", sa.DateTime(timezone=True), nullable=True)),
        ]
        for name, col in additions:
            if name not in existing_cols:
                op.add_column("users", col)
        existing_indexes = {i["name"] for i in insp.get_indexes("users")}
        if "ix_users_login" not in existing_indexes:
            op.create_index("ix_users_login", "users", ["login"], unique=False)

    insp = sa.inspect(bind)
    if not _has_table(insp, "archetypes"):
        op.create_table(
            "archetypes",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("slug", sa.String(length=64), nullable=False),
            sa.Column("name", sa.String(length=128), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.UniqueConstraint("slug", name="uq_archetypes_slug"),
        )

    insp = sa.inspect(bind)
    if not _has_table(insp, "tags"):
        op.create_table(
            "tags",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("slug", sa.String(length=64), nullable=False),
            sa.Column("name", sa.String(length=128), nullable=False),
            sa.UniqueConstraint("slug", name="uq_tags_slug"),
        )

    insp = sa.inspect(bind)
    if not _has_table(insp, "content_items"):
        op.create_table(
            "content_items",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("slug", sa.String(length=160), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("summary", sa.Text(), nullable=True),
            sa.Column("body_md", sa.Text(), nullable=True),
            sa.Column("archetype_id", sa.Integer(), sa.ForeignKey("archetypes.id", ondelete="SET NULL"), nullable=True),
            sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("is_premium", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )
        op.create_index("ix_content_items_slug", "content_items", ["slug"], unique=True)

    insp = sa.inspect(bind)
    if not _has_table(insp, "content_chunks"):
        op.create_table(
            "content_chunks",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("content_item_id", sa.Integer(), sa.ForeignKey("content_items.id", ondelete="CASCADE"), nullable=False),
            sa.Column("chunk_index", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("text", sa.Text(), nullable=False),
            sa.Column("embedding", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )
        op.create_index("ix_content_chunks_content_item_id", "content_chunks", ["content_item_id"], unique=False)

    insp = sa.inspect(bind)
    if not _has_table(insp, "content_tags"):
        op.create_table(
            "content_tags",
            sa.Column("content_item_id", sa.Integer(), sa.ForeignKey("content_items.id", ondelete="CASCADE"), primary_key=True),
            sa.Column("tag_id", sa.Integer(), sa.ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
        )

    insp = sa.inspect(bind)
    if not _has_table(insp, "leads"):
        op.create_table(
            "leads",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(length=128), nullable=False),
            sa.Column("contact", sa.String(length=255), nullable=False),
            sa.Column("message", sa.Text(), nullable=True),
            sa.Column("source", sa.String(length=64), nullable=False, server_default="web"),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="new"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )
        op.create_index("ix_leads_status", "leads", ["status"], unique=False)
        op.create_index("ix_leads_created_at", "leads", ["created_at"], unique=False)

    insp = sa.inspect(bind)
    if not _has_table(insp, "notifications"):
        op.create_table(
            "notifications",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("channel", sa.String(length=32), nullable=False, server_default="telegram"),
            sa.Column("recipient", sa.String(length=255), nullable=True),
            sa.Column("payload", sa.Text(), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
            sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("last_error", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_notifications_status", "notifications", ["status"], unique=False)

    insp = sa.inspect(bind)
    if not _has_table(insp, "chat_sessions"):
        op.create_table(
            "chat_sessions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("title", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )
        op.create_index("ix_chat_sessions_user_id", "chat_sessions", ["user_id"], unique=False)

    insp = sa.inspect(bind)
    if not _has_table(insp, "chat_messages"):
        op.create_table(
            "chat_messages",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("session_id", sa.Integer(), sa.ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False),
            sa.Column("role", sa.String(length=32), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("sources_json", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )
        op.create_index("ix_chat_messages_session_id", "chat_messages", ["session_id"], unique=False)

    insp = sa.inspect(bind)
    if not _has_table(insp, "content_views"):
        op.create_table(
            "content_views",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("content_item_id", sa.Integer(), sa.ForeignKey("content_items.id", ondelete="SET NULL"), nullable=True),
            sa.Column("viewed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )
        op.create_index("ix_content_views_user_id", "content_views", ["user_id"], unique=False)
        op.create_index("ix_content_views_content_item_id", "content_views", ["content_item_id"], unique=False)

    insp = sa.inspect(bind)
    if not _has_table(insp, "audit_log"):
        op.create_table(
            "audit_log",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("action", sa.String(length=128), nullable=False),
            sa.Column("entity_type", sa.String(length=64), nullable=True),
            sa.Column("entity_id", sa.String(length=64), nullable=True),
            sa.Column("details", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )
        op.create_index("ix_audit_log_user_id", "audit_log", ["user_id"], unique=False)

    insp = sa.inspect(bind)
    if not _has_table(insp, "rate_limits"):
        op.create_table(
            "rate_limits",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("key", sa.String(length=255), nullable=False),
            sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
            sa.Column("count", sa.Integer(), nullable=False, server_default="0"),
            sa.UniqueConstraint("key", "window_start", name="uq_rate_limits_key_window"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    for table in [
        "rate_limits", "audit_log", "content_views", "chat_messages", "chat_sessions",
        "notifications", "leads", "content_tags", "content_chunks", "content_items",
        "tags", "archetypes",
    ]:
        if _has_table(insp, table):
            op.drop_table(table)
            insp = sa.inspect(bind)
    # users table is preserved intentionally to avoid data loss.
