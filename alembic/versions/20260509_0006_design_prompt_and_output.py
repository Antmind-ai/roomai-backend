"""Add prompt and output_preview_url to design requests

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-09 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "platform_design_requests",
        sa.Column("prompt", sa.String(1000), nullable=True),
    )
    op.add_column(
        "platform_design_requests",
        sa.Column("output_preview_url", sa.String(2000), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("platform_design_requests", "output_preview_url")
    op.drop_column("platform_design_requests", "prompt")
