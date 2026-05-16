from datetime import UTC, datetime
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.platform import revenuecat_service
from app.services.platform.credit_service import add_credits

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/revenuecat")


@router.post(
    "/webhook",
    summary="Receive RevenueCat purchase events",
    status_code=status.HTTP_200_OK,
)
async def revenuecat_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    authorization: str | None = Header(default=None),
) -> dict:
    if not revenuecat_service.verify_webhook_secret(authorization):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook credentials",
        )

    raw_body = await request.body()
    event = revenuecat_service.parse_event(raw_body)
    if event is None:
        return {"status": "ignored", "reason": "invalid_json"}

    (
        event_type,
        event_id,
        product_id,
        transaction_id,
        environment,
        app_user_id,
    ) = revenuecat_service.extract_event_fields(event)

    if not event_id or not event_type:
        return {"status": "ignored", "reason": "missing_event_fields"}

    user_id = revenuecat_service.parse_user_id(app_user_id)
    if user_id is None:
        logger.warning("RevenueCat event without valid app_user_id: %s", event_id)
        return {"status": "ignored", "reason": "invalid_app_user_id"}

    try:
        if await revenuecat_service.is_duplicate_event(db, event_id):
            return {"status": "ok", "result": "idempotent_skip"}

        credit_amount = revenuecat_service.get_credit_amount_for_product(product_id)

        is_active = False
        purchased_at = None
        expires_at = None
        expiry_raw = event.get("event", {}).get("expiration_at_ms")
        purchase_raw = event.get("event", {}).get("purchased_at_ms")

        if expiry_raw:
            expires_at = datetime.fromtimestamp(
                expiry_raw / 1000, tz=UTC
            )

        if purchase_raw:
            purchased_at = datetime.fromtimestamp(
                purchase_raw / 1000, tz=UTC
            )

        if event_type in ("INITIAL_PURCHASE", "RENEWAL", "NON_RENEWING_PURCHASE"):
            is_active = True

            if credit_amount > 0:
                await add_credits(
                    db,
                    user_id=user_id,
                    credits=credit_amount,
                    source="subscription",
                    reason=f"{event_type}: {product_id}",
                    reference_id=transaction_id,
                    idempotency_key=f"rc:{event_id}",
                )

        elif event_type in ("CANCELLATION", "EXPIRATION"):
            is_active = False

        await revenuecat_service.record_purchase_event(
            db,
            user_id=user_id,
            event_id=event_id,
            event_type=event_type,
            product_id=product_id,
            transaction_id=transaction_id or event_id,
            environment=environment,
            credit_amount=credit_amount,
            is_active=is_active,
            purchased_at=purchased_at,
            expires_at=expires_at,
            raw_payload=event,
        )

        await db.commit()

        logger.info(
            "RevenueCat event processed: type=%s product=%s credits=%d user=%s",
            event_type,
            product_id,
            credit_amount,
            str(user_id),
        )

        return {"status": "ok", "result": "processed"}

    except Exception:
        await db.rollback()
        raise
