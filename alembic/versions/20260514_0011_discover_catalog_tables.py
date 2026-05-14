"""Add discover catalog tables

Revision ID: 0011
Revises: 0010
Create Date: 2026-05-14 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "platform_discover_assets",
        sa.Column("asset_id", sa.String(length=120), nullable=False),
        sa.Column("r2_key", sa.String(length=500), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("asset_id"),
        sa.UniqueConstraint("r2_key"),
    )

    op.create_table(
        "platform_discover_cards",
        sa.Column("category_key", sa.String(length=40), nullable=False),
        sa.Column("section_id", sa.String(length=120), nullable=False),
        sa.Column("card_id", sa.String(length=120), nullable=False),
        sa.Column("category_label", sa.String(length=120), nullable=False),
        sa.Column("category_order", sa.Integer(), nullable=False),
        sa.Column("section_title", sa.String(length=120), nullable=False),
        sa.Column("section_order", sa.Integer(), nullable=False),
        sa.Column("card_order", sa.Integer(), nullable=False),
        sa.Column("image_asset_id", sa.String(length=120), nullable=False),
        sa.CheckConstraint(
            "category_key IN ('home', 'garden', 'exterior')",
            name="ck_platform_discover_cards_category_key",
        ),
        sa.CheckConstraint(
            "category_order >= 0",
            name="ck_platform_discover_cards_category_order_nonnegative",
        ),
        sa.CheckConstraint(
            "section_order >= 0",
            name="ck_platform_discover_cards_section_order_nonnegative",
        ),
        sa.CheckConstraint(
            "card_order >= 0",
            name="ck_platform_discover_cards_card_order_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["image_asset_id"],
            ["platform_discover_assets.asset_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("category_key", "section_id", "card_id"),
    )

    op.create_index(
        "ix_platform_discover_cards_category_order",
        "platform_discover_cards",
        ["category_order", "section_order", "card_order"],
        unique=False,
    )
    op.create_index(
        "ix_platform_discover_cards_image_asset_id",
        "platform_discover_cards",
        ["image_asset_id"],
        unique=False,
    )
    op.create_index(
        "ux_platform_discover_cards_category_section_card_order",
        "platform_discover_cards",
        ["category_key", "section_id", "card_order"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ux_platform_discover_cards_category_section_card_order",
        table_name="platform_discover_cards",
    )
    op.drop_index(
        "ix_platform_discover_cards_image_asset_id",
        table_name="platform_discover_cards",
    )
    op.drop_index(
        "ix_platform_discover_cards_category_order",
        table_name="platform_discover_cards",
    )
    op.drop_table("platform_discover_cards")
    op.drop_table("platform_discover_assets")
