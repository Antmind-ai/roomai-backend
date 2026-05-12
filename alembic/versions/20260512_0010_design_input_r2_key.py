"""Add input_r2_key column to platform_design_requests

Revision ID: 0010
Revises: 0009
Create Date: 2026-05-12 00:00:00.000002

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "platform_design_requests",
        sa.Column(
            "input_r2_key",
            sa.String(length=500),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("platform_design_requests", "input_r2_key")
