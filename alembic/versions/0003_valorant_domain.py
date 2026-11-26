"""valorant domain tables

Revision ID: 0003_valorant_domain
Revises: 0002_tierlist_state
Create Date: 2026-05-26 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003_valorant_domain"
down_revision: Union[str, Sequence[str], None] = "0002_tierlist_state"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(insp, name: str) -> bool:
    return name in insp.get_table_names()


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if not _has_table(insp, "roles"):
        op.create_table(
            "roles",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(length=128), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.UniqueConstraint("name", name="uq_roles_name"),
        )

    insp = sa.inspect(bind)
    if not _has_table(insp, "sides"):
        op.create_table(
            "sides",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(length=64), nullable=False),
            sa.UniqueConstraint("name", name="uq_sides_name"),
        )

    insp = sa.inspect(bind)
    if not _has_table(insp, "maps"):
        op.create_table(
            "maps",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(length=128), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.UniqueConstraint("name", name="uq_maps_name"),
        )

    insp = sa.inspect(bind)
    if not _has_table(insp, "characters"):
        op.create_table(
            "characters",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(length=128), nullable=False),
            sa.Column(
                "role_id",
                sa.Integer(),
                sa.ForeignKey("roles.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("icon_url", sa.String(length=512), nullable=True),
            sa.UniqueConstraint("name", name="uq_characters_name"),
        )
        op.create_index("ix_characters_role_id", "characters", ["role_id"], unique=False)

    insp = sa.inspect(bind)
    if not _has_table(insp, "articles"):
        op.create_table(
            "articles",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("content", sa.Text(), nullable=True),
            sa.Column(
                "map_id",
                sa.Integer(),
                sa.ForeignKey("maps.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "side_id",
                sa.Integer(),
                sa.ForeignKey("sides.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "role_id",
                sa.Integer(),
                sa.ForeignKey("roles.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
        )
        op.create_index("ix_articles_map_id", "articles", ["map_id"], unique=False)
        op.create_index("ix_articles_side_id", "articles", ["side_id"], unique=False)
        op.create_index("ix_articles_role_id", "articles", ["role_id"], unique=False)

    insp = sa.inspect(bind)
    if not _has_table(insp, "article_characters"):
        op.create_table(
            "article_characters",
            sa.Column(
                "article_id",
                sa.Integer(),
                sa.ForeignKey("articles.id", ondelete="CASCADE"),
                primary_key=True,
            ),
            sa.Column(
                "character_id",
                sa.Integer(),
                sa.ForeignKey("characters.id", ondelete="CASCADE"),
                primary_key=True,
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    for table in ["article_characters", "articles", "characters", "maps", "sides", "roles"]:
        if _has_table(insp, table):
            op.drop_table(table)
            insp = sa.inspect(bind)
