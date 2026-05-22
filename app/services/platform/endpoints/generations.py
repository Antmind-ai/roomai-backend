import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.platform.endpoints.auth import get_current_user_id
from app.services.platform.generation_quota_service import (
    get_generation_quota,
    quota_snapshot_payload,
)
from app.services.platform.schemas.generation import GenerationQuotaResponse

router = APIRouter(prefix="/generations")


@router.get(
    "/quota",
    response_model=GenerationQuotaResponse,
    summary="Return current authenticated user's generation quota",
)
async def generation_quota_me(
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> GenerationQuotaResponse:
    try:
        snapshot = await get_generation_quota(db, current_user_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        ) from exc

    return GenerationQuotaResponse(**quota_snapshot_payload(snapshot))
