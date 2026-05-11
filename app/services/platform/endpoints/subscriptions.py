import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from app.core.config import settings
from app.core.database import get_db
from app.services.platform.credit_service import get_credit_balance
from app.services.platform.endpoints.auth import get_current_user_id
from app.services.platform.models.subscription import PurchaseRecord
from app.services.platform.schemas.subscription import (
    SubscriptionMeResponse,
    SubscriptionProductResponse,
    SubscriptionProductsResponse,
)

router = APIRouter(prefix="/subscriptions")


@router.get(
    "/products",
    response_model=SubscriptionProductsResponse,
    summary="List available subscription products",
)
async def list_products() -> SubscriptionProductsResponse:
    products = [
        SubscriptionProductResponse(
            product_id=settings.subscription_weekly_product_id,
            plan_type="weekly",
            credit_amount=settings.subscription_weekly_credits,
        ),
        SubscriptionProductResponse(
            product_id=settings.subscription_yearly_product_id,
            plan_type="yearly",
            credit_amount=settings.subscription_yearly_credits,
        ),
    ]
    return SubscriptionProductsResponse(products=products)


@router.get(
    "/me",
    response_model=SubscriptionMeResponse,
    summary="Get current user's subscription status and balance",
)
async def subscription_me(
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> SubscriptionMeResponse:
    try:
        balance = await get_credit_balance(db, current_user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    result = await db.execute(
        select(PurchaseRecord)
        .where(PurchaseRecord.user_id == current_user_id)
        .where(PurchaseRecord.is_active_subscription.is_(True))
        .order_by(PurchaseRecord.created_at.desc())
        .limit(1)
    )
    latest_purchase = result.scalar_one_or_none()

    if latest_purchase is None:
        return SubscriptionMeResponse(
            user_id=current_user_id,
            has_active_subscription=False,
            balance=balance,
        )

    plan_type = (
        "weekly"
        if latest_purchase.revenuecat_product_id == settings.subscription_weekly_product_id
        else "yearly"
        if latest_purchase.revenuecat_product_id == settings.subscription_yearly_product_id
        else "unknown"
    )

    credit_amount = (
        settings.subscription_weekly_credits
        if plan_type == "weekly"
        else settings.subscription_yearly_credits
    )

    return SubscriptionMeResponse(
        user_id=current_user_id,
        has_active_subscription=True,
        product_id=latest_purchase.revenuecat_product_id,
        plan_type=plan_type,
        credit_amount=credit_amount,
        expires_at=latest_purchase.expires_at.isoformat() if latest_purchase.expires_at else None,
        balance=balance,
    )
