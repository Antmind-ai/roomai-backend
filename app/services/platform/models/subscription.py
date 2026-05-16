from datetime import datetime
import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SubscriptionProduct(Base):
    __tablename__ = "platform_subscription_products"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    product_id: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    plan_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )
    credit_amount: Mapped[int] = mapped_column(
        Integer, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class PurchaseRecord(Base):
    __tablename__ = "platform_purchase_records"
    __table_args__ = (
        Index(
            "ux_platform_purchase_records_event_id",
            "revenuecat_event_id",
            unique=True,
        ),
        Index("ix_platform_purchase_records_user_id", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("platform_users.id", ondelete="CASCADE"),
        nullable=False,
    )
    revenuecat_event_id: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    revenuecat_transaction_id: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    revenuecat_product_id: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    event_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )
    environment: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )
    credit_amount_granted: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    is_active_subscription: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    purchased_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    raw_payload: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
