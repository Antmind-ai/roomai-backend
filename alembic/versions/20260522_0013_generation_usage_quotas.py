"""Replace credits with generation usage quotas

Revision ID: 0013
Revises: 0012
Create Date: 2026-05-22 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "platform_generation_usage",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("generation_type", sa.String(length=40), nullable=False),
        sa.Column("reference_id", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="reserved"),
        sa.Column(
            "reserved_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('reserved', 'completed', 'released')",
            name="ck_platform_generation_usage_status",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["platform_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_platform_generation_usage_user_status_reserved",
        "platform_generation_usage",
        ["user_id", "status", "reserved_at"],
        unique=False,
    )
    op.create_index(
        "ix_platform_generation_usage_user_reference",
        "platform_generation_usage",
        ["user_id", "generation_type", "reference_id"],
        unique=False,
    )

    op.execute(
        sa.text(
            """
            INSERT INTO platform_generation_usage (
                id,
                user_id,
                generation_type,
                reference_id,
                status,
                reserved_at,
                completed_at
            )
            SELECT
                uuid_generate_v4(),
                user_id,
                'design_request',
                id::text,
                'completed',
                COALESCE(submitted_at, completed_at, now()),
                COALESCE(completed_at, submitted_at, now())
            FROM platform_design_requests
            WHERE status = 'completed'
              AND deleted_at IS NULL
            """
        )
    )

    op.drop_index(
        "ix_platform_device_credit_grants_first_user_id",
        table_name="platform_device_credit_grants",
    )
    op.drop_table("platform_device_credit_grants")

    op.drop_index(
        "ux_platform_credit_ledger_user_id_idempotency_key",
        table_name="platform_credit_ledger",
    )
    op.drop_index(
        "ix_platform_credit_ledger_user_id_created_at",
        table_name="platform_credit_ledger",
    )
    op.drop_index("ix_platform_credit_ledger_user_id", table_name="platform_credit_ledger")
    op.drop_table("platform_credit_ledger")

    op.drop_column("platform_users", "credit_balance")
    op.drop_column("platform_subscription_products", "credit_amount")
    op.drop_column("platform_purchase_records", "credit_amount_granted")


def downgrade() -> None:
    op.add_column(
        "platform_purchase_records",
        sa.Column(
            "credit_amount_granted",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "platform_subscription_products",
        sa.Column("credit_amount", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "platform_users",
        sa.Column("credit_balance", sa.Integer(), nullable=False, server_default="0"),
    )

    op.create_table(
        "platform_credit_ledger",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("delta", sa.Integer(), nullable=False),
        sa.Column("balance_after", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column("reference_id", sa.String(length=120), nullable=True),
        sa.Column("idempotency_key", sa.String(length=120), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("delta <> 0", name="ck_platform_credit_ledger_delta_nonzero"),
        sa.CheckConstraint(
            "balance_after >= 0",
            name="ck_platform_credit_ledger_balance_after_nonnegative",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["platform_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_platform_credit_ledger_user_id",
        "platform_credit_ledger",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_platform_credit_ledger_user_id_created_at",
        "platform_credit_ledger",
        ["user_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ux_platform_credit_ledger_user_id_idempotency_key",
        "platform_credit_ledger",
        ["user_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )

    op.create_table(
        "platform_device_credit_grants",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("device_id", sa.String(length=255), nullable=False),
        sa.Column("first_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("credits_granted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["first_user_id"],
            ["platform_users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("device_id", name="uq_platform_device_credit_grants_device_id"),
    )
    op.create_index(
        "ix_platform_device_credit_grants_first_user_id",
        "platform_device_credit_grants",
        ["first_user_id"],
        unique=False,
    )

    op.drop_index(
        "ix_platform_generation_usage_user_reference",
        table_name="platform_generation_usage",
    )
    op.drop_index(
        "ix_platform_generation_usage_user_status_reserved",
        table_name="platform_generation_usage",
    )
    op.drop_table("platform_generation_usage")
