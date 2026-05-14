from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DiscoverAsset(Base):
    __tablename__ = "platform_discover_assets"

    asset_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    r2_key: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class DiscoverCard(Base):
    __tablename__ = "platform_discover_cards"
    __table_args__ = (
        CheckConstraint(
            "category_key IN ('home', 'garden', 'exterior')",
            name="ck_platform_discover_cards_category_key",
        ),
        CheckConstraint(
            "category_order >= 0",
            name="ck_platform_discover_cards_category_order_nonnegative",
        ),
        CheckConstraint(
            "section_order >= 0",
            name="ck_platform_discover_cards_section_order_nonnegative",
        ),
        CheckConstraint(
            "card_order >= 0",
            name="ck_platform_discover_cards_card_order_nonnegative",
        ),
        Index(
            "ix_platform_discover_cards_category_order",
            "category_order",
            "section_order",
            "card_order",
        ),
        Index(
            "ix_platform_discover_cards_image_asset_id",
            "image_asset_id",
        ),
        Index(
            "ux_platform_discover_cards_category_section_card_order",
            "category_key",
            "section_id",
            "card_order",
            unique=True,
        ),
    )

    category_key: Mapped[str] = mapped_column(String(40), primary_key=True)
    section_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    card_id: Mapped[str] = mapped_column(String(120), primary_key=True)

    category_label: Mapped[str] = mapped_column(String(120), nullable=False)
    category_order: Mapped[int] = mapped_column(Integer, nullable=False)

    section_title: Mapped[str] = mapped_column(String(120), nullable=False)
    section_order: Mapped[int] = mapped_column(Integer, nullable=False)

    card_order: Mapped[int] = mapped_column(Integer, nullable=False)

    image_asset_id: Mapped[str] = mapped_column(
        String(120),
        ForeignKey("platform_discover_assets.asset_id", ondelete="RESTRICT"),
        nullable=False,
    )
