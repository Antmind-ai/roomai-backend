from datetime import UTC, datetime
import json
import logging
import secrets
import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services.platform.models.subscription import PurchaseRecord

logger = logging.getLogger(__name__)


def verify_webhook_secret(secret_header: str | None) -> bool:
    configured = settings.revenuecat_webhook_secret
    if not configured:
        logger.warning("RevenueCat webhook secret not configured")
        return False
    if not secret_header:
        return False
    return secrets.compare_digest(secret_header, configured)


async def is_duplicate_event(
    db: AsyncSession,
    event_id: str,
) -> bool:
    result = await db.execute(
        select(PurchaseRecord.id).where(
            PurchaseRecord.revenuecat_event_id == event_id
        )
    )
    return result.scalar_one_or_none() is not None


def parse_event(raw_body: bytes) -> dict | None:
    try:
        return json.loads(raw_body)
    except json.JSONDecodeError:
        logger.error("Failed to parse RevenueCat webhook body")
        return None


def extract_event_fields(event: dict) -> tuple[str, str, str, str | None, str | None, str | None]:
    event_type = event.get("event", {}).get("type", "")
    event_id = event.get("event", {}).get("id", "")
    product_id = event.get("event", {}).get("product_id", "")
    transaction_id = event.get("event", {}).get("transaction_id", event_id)
    environment = event.get("event", {}).get("environment")
    app_user_id = event.get("event", {}).get("app_user_id")
    return event_type, event_id, product_id, transaction_id, environment, app_user_id


def get_plan_type_for_product(product_id: str) -> str:
    if product_id == settings.subscription_weekly_product_id:
        return "weekly"
    if product_id == settings.subscription_yearly_product_id:
        return "yearly"
    logger.warning("Unknown subscription product_id: %s", product_id)
    return "unknown"


def parse_user_id(app_user_id: str | None) -> uuid.UUID | None:
    if not app_user_id:
        return None
    try:
        return uuid.UUID(app_user_id)
    except ValueError:
        logger.warning("Invalid RevenueCat app_user_id (not a UUID): %s", app_user_id)
        return None


async def record_purchase_event(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    event_id: str,
    event_type: str,
    product_id: str,
    transaction_id: str,
    environment: str | None,
    is_active: bool,
    purchased_at: datetime | None,
    expires_at: datetime | None,
    raw_payload: dict,
) -> PurchaseRecord:
    await clear_active_subscription_records(db, user_id=user_id)

    record = PurchaseRecord(
        user_id=user_id,
        revenuecat_event_id=event_id,
        revenuecat_transaction_id=transaction_id,
        revenuecat_product_id=product_id,
        event_type=event_type,
        environment=environment,
        is_active_subscription=is_active,
        purchased_at=purchased_at,
        expires_at=expires_at,
        raw_payload=raw_payload,
    )
    db.add(record)
    await db.flush()
    return record


async def clear_active_subscription_records(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> None:
    await db.execute(
        update(PurchaseRecord)
        .where(PurchaseRecord.user_id == user_id)
        .where(PurchaseRecord.is_active_subscription.is_(True))
        .values(is_active_subscription=False)
    )


async def get_current_subscription_record(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> PurchaseRecord | None:
    result = await db.execute(
        select(PurchaseRecord)
        .where(PurchaseRecord.user_id == user_id)
        .order_by(PurchaseRecord.created_at.desc())
        .limit(1)
    )
    record = result.scalar_one_or_none()
    if record is None or not record.is_active_subscription:
        return None
    if record.expires_at is not None and record.expires_at <= datetime.now(UTC):
        return None
    return record
