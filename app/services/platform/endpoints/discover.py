from __future__ import annotations

from urllib.parse import quote
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.services.platform.endpoints.auth import get_current_user_id
from app.services.platform.models import DiscoverAsset, DiscoverCard
from app.services.platform.schemas.discover import (
    DiscoverCardResponse,
    DiscoverCatalogCategoriesResponse,
    DiscoverCatalogResponse,
    DiscoverCategoryResponse,
    DiscoverSectionResponse,
)

router = APIRouter(prefix="/discover")

DISCOVER_CATALOG_CACHE_MAX_AGE_SECONDS = 86400


def _build_public_r2_url(r2_key: str) -> str:
    base_url = (settings.r2_public_url or "").rstrip("/")
    normalized_key = r2_key.strip("/")
    encoded_key = "/".join(quote(part, safe="") for part in normalized_key.split("/"))
    return f"{base_url}/{encoded_key}"


@router.get(
    "/catalog",
    response_model=DiscoverCatalogResponse,
    summary="Return public discover catalog",
)
async def get_discover_catalog(
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> DiscoverCatalogResponse:
    del current_user_id

    if not settings.r2_public_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Public object storage URL is not configured",
        )

    result = await db.execute(
        select(DiscoverCard, DiscoverAsset)
        .join(
            DiscoverAsset,
            DiscoverAsset.asset_id == DiscoverCard.image_asset_id,
        )
        .order_by(
            DiscoverCard.category_order.asc(),
            DiscoverCard.section_order.asc(),
            DiscoverCard.card_order.asc(),
        )
    )
    catalog_rows = result.all()
    if not catalog_rows:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Discover catalog is not seeded",
        )

    image_url_by_asset_id: dict[str, str] = {}
    category_payloads: dict[str, DiscoverCategoryResponse] = {}
    section_payloads: dict[tuple[str, str], DiscoverSectionResponse] = {}

    for card, asset in catalog_rows:
        category_payload = category_payloads.get(card.category_key)
        if category_payload is None:
            category_payload = DiscoverCategoryResponse(
                label=card.category_label,
                sections=[],
            )
            category_payloads[card.category_key] = category_payload
        elif category_payload.label != card.category_label:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    "Discover catalog seed data is inconsistent for category label | "
                    f"category={card.category_key}"
                ),
            )

        section_key = (card.category_key, card.section_id)
        section_payload = section_payloads.get(section_key)
        if section_payload is None:
            section_payload = DiscoverSectionResponse(
                id=card.section_id,
                title=card.section_title,
                cards=[],
            )
            section_payloads[section_key] = section_payload
            category_payload.sections.append(section_payload)
        elif section_payload.title != card.section_title:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    "Discover catalog seed data is inconsistent for section title | "
                    f"category={card.category_key} section={card.section_id}"
                ),
            )

        if asset.asset_id not in image_url_by_asset_id:
            image_url_by_asset_id[asset.asset_id] = _build_public_r2_url(asset.r2_key)

        section_payload.cards.append(
            DiscoverCardResponse(
                id=card.card_id,
                image_url=image_url_by_asset_id[asset.asset_id],
            )
        )

    required_category_keys = ("home", "garden", "exterior")
    missing_categories = [
        category_key
        for category_key in required_category_keys
        if category_key not in category_payloads
    ]
    if missing_categories:
        missing_value = ", ".join(missing_categories)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Discover catalog seed data is missing categories: {missing_value}",
        )

    return DiscoverCatalogResponse(
        cache_max_age_seconds=DISCOVER_CATALOG_CACHE_MAX_AGE_SECONDS,
        expires_in_seconds=DISCOVER_CATALOG_CACHE_MAX_AGE_SECONDS,
        categories=DiscoverCatalogCategoriesResponse(
            home=category_payloads["home"],
            garden=category_payloads["garden"],
            exterior=category_payloads["exterior"],
        ),
    )
