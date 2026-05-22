import uuid

from pydantic import BaseModel

from app.services.platform.schemas.generation import GenerationQuotaResponse


class SubscriptionProductResponse(BaseModel):
    product_id: str
    plan_type: str
    daily_generation_limit: int
    weekly_generation_limit: int


class SubscriptionProductsResponse(BaseModel):
    products: list[SubscriptionProductResponse]


class RestoreResponse(BaseModel):
    user_id: uuid.UUID
    has_active_subscription: bool
    product_id: str | None = None
    plan_type: str | None = None
    expires_at: str | None = None
    quota: GenerationQuotaResponse


class SubscriptionMeResponse(BaseModel):
    user_id: uuid.UUID
    has_active_subscription: bool
    product_id: str | None = None
    plan_type: str | None = None
    expires_at: str | None = None
    quota: GenerationQuotaResponse
