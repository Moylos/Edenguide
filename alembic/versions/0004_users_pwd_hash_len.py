"""widen users.pwd_hash for werkzeug hashes

Revision ID: 0004_users_pwd_hash_len
Revises: 0003_valorant_domain
Create Date: 2026-05-26 00:01:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0004_users_pwd_hash_len"
down_revision: Union[str, Sequence[str], None] = "0003_valorant_domain"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "pwd_hash",
            existing_type=sa.String(length=128),
            type_=sa.String(length=256),
            existing_nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "pwd_hash",
            existing_type=sa.String(length=256),
            type_=sa.String(length=128),
            existing_nullable=False,
        )
