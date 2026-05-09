"""Add design requests table for queued create-flow jobs

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-09 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "platform_design_requests",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("input_upload_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("input_filename", sa.String(length=255), nullable=True),
        sa.Column("example_photo_id", sa.String(length=120), nullable=True),
        sa.Column("building_type", sa.String(length=80), nullable=False),
        sa.Column("style_id", sa.String(length=80), nullable=False),
        sa.Column("palette_id", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="queued"),
        sa.Column("queue_job_id", sa.String(length=120), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "source IN ('upload', 'example')",
            name="ck_platform_design_requests_source",
        ),
        sa.CheckConstraint(
            "status IN ('queued', 'processing', 'completed', 'failed')",
            name="ck_platform_design_requests_status",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["platform_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_platform_design_requests_user_id_submitted_at",
        "platform_design_requests",
        ["user_id", "submitted_at"],
        unique=False,
    )
    op.create_index(
        "ix_platform_design_requests_status",
        "platform_design_requests",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_platform_design_requests_queue_job_id",
        "platform_design_requests",
        ["queue_job_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_platform_design_requests_queue_job_id", table_name="platform_design_requests")
    op.drop_index("ix_platform_design_requests_status", table_name="platform_design_requests")
    op.drop_index(
        "ix_platform_design_requests_user_id_submitted_at",
        table_name="platform_design_requests",
    )
    op.drop_table("platform_design_requests")
