"""Add deleted_at column to platform_users for soft-delete

Revision ID: 0008
Revises: 0007
Create Date: 2026-05-12 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "platform_users",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_platform_users_not_deleted",
        "platform_users",
        ["deleted_at"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_platform_users_not_deleted", table_name="platform_users")
    op.drop_column("platform_users", "deleted_at")
