"""Add RevenueCat subscription tables

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-11 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "platform_subscription_products",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("product_id", sa.String(length=255), nullable=False),
        sa.Column("plan_type", sa.String(length=20), nullable=False),
        sa.Column("credit_amount", sa.Integer(), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_platform_subscription_products_product_id",
        "platform_subscription_products",
        ["product_id"],
        unique=True,
    )

    op.create_table(
        "platform_purchase_records",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("revenuecat_event_id", sa.String(length=255), nullable=False),
        sa.Column(
            "revenuecat_transaction_id", sa.String(length=255), nullable=False
        ),
        sa.Column(
            "revenuecat_product_id", sa.String(length=255), nullable=False
        ),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("environment", sa.String(length=20), nullable=True),
        sa.Column(
            "credit_amount_granted",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "is_active_subscription",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("purchased_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["platform_users.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ux_platform_purchase_records_event_id",
        "platform_purchase_records",
        ["revenuecat_event_id"],
        unique=True,
    )
    op.create_index(
        "ix_platform_purchase_records_user_id",
        "platform_purchase_records",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_platform_purchase_records_user_id",
        table_name="platform_purchase_records",
    )
    op.drop_index(
        "ux_platform_purchase_records_event_id",
        table_name="platform_purchase_records",
    )
    op.drop_table("platform_purchase_records")
    op.drop_index(
        "ix_platform_subscription_products_product_id",
        table_name="platform_subscription_products",
    )
    op.drop_table("platform_subscription_products")
