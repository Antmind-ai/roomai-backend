import uuid

from pydantic import BaseModel, Field


class GenerationQuotaResponse(BaseModel):
    user_id: uuid.UUID
    has_active_subscription: bool
    plan_type: str | None = None
    quota_scope: str
    free_lifetime_generation_limit: int = Field(..., ge=0)
    free_lifetime_generations_used: int = Field(..., ge=0)
    free_lifetime_generations_remaining: int = Field(..., ge=0)
    daily_generation_limit: int | None = Field(default=None, ge=0)
    daily_generations_used: int = Field(..., ge=0)
    daily_generations_remaining: int | None = Field(default=None, ge=0)
    weekly_generation_limit: int | None = Field(default=None, ge=0)
    weekly_generations_used: int = Field(..., ge=0)
    weekly_generations_remaining: int | None = Field(default=None, ge=0)
