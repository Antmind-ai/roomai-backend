from __future__ import annotations

import asyncio
from collections.abc import Mapping
import logging
from typing import Any

from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert

from app.core.database import async_session_factory
from discover_catalog_seed_data import (
    DISCOVER_ASSET_ID_TO_R2_KEY,
    DISCOVER_CATEGORIES_TEMPLATE,
)
from app.services.platform.models import DiscoverAsset, DiscoverCard

ALLOWED_DISCOVER_CATEGORY_KEYS = ("home", "garden", "exterior")
logger = logging.getLogger(__name__)


def _build_asset_rows() -> list[dict[str, str]]:
    return [
        {
            "asset_id": asset_id,
            "r2_key": r2_key,
        }
        for asset_id, r2_key in DISCOVER_ASSET_ID_TO_R2_KEY.items()
    ]


def _build_card_rows() -> list[dict[str, Any]]:
    category_keys = tuple(DISCOVER_CATEGORIES_TEMPLATE.keys())
    if category_keys != ALLOWED_DISCOVER_CATEGORY_KEYS:
        raise ValueError(
            "Discover category keys/order must exactly match "
            f"{ALLOWED_DISCOVER_CATEGORY_KEYS}; got {category_keys}"
        )

    card_rows: list[dict[str, Any]] = []
    seen_rows: set[tuple[str, str, str]] = set()
    seen_sections_by_category: dict[str, set[str]] = {}

    for category_order, (category_key, category_data_raw) in enumerate(
        DISCOVER_CATEGORIES_TEMPLATE.items()
    ):
        if category_key not in ALLOWED_DISCOVER_CATEGORY_KEYS:
            raise ValueError(f"Unsupported discover category key: {category_key}")

        category_data = _expect_mapping(category_data_raw, f"category:{category_key}")
        category_label = _expect_str(
            category_data.get("label"),
            f"category:{category_key}.label",
        )

        sections_raw = category_data.get("sections")
        if not isinstance(sections_raw, list):
            raise ValueError(f"Discover catalog sections must be a list | category={category_key}")

        for section_order, section_data_raw in enumerate(sections_raw):
            section_data = _expect_mapping(
                section_data_raw,
                f"category:{category_key}.section:{section_order}",
            )
            section_id = _expect_str(
                section_data.get("id"),
                f"category:{category_key}.section:{section_order}.id",
            )
            category_sections = seen_sections_by_category.setdefault(category_key, set())
            if section_id in category_sections:
                raise ValueError(
                    "Duplicate discover section id in seed data | "
                    f"category={category_key} section={section_id}"
                )
            category_sections.add(section_id)
            section_title = _expect_str(
                section_data.get("title"),
                f"category:{category_key}.section:{section_order}.title",
            )

            cards_raw = section_data.get("cards")
            if not isinstance(cards_raw, list):
                raise ValueError(
                    "Discover section cards must be a list | "
                    f"category={category_key} section={section_id}"
                )

            for card_order, card_data_raw in enumerate(cards_raw):
                card_data = _expect_mapping(
                    card_data_raw,
                    (
                        f"category:{category_key}.section:{section_id}."
                        f"card:{card_order}"
                    ),
                )
                card_id = _expect_str(
                    card_data.get("id"),
                    (
                        f"category:{category_key}.section:{section_id}."
                        f"card:{card_order}.id"
                    ),
                )
                image_asset_id = _expect_str(
                    card_data.get("image_asset_id"),
                    (
                        f"category:{category_key}.section:{section_id}."
                        f"card:{card_order}.image_asset_id"
                    ),
                )

                if image_asset_id not in DISCOVER_ASSET_ID_TO_R2_KEY:
                    raise ValueError(
                        "Discover card references unknown image asset id | "
                        f"category={category_key} section={section_id} card={card_id} "
                        f"asset_id={image_asset_id}"
                    )

                dedupe_key = (category_key, section_id, card_id)
                if dedupe_key in seen_rows:
                    raise ValueError(
                        "Duplicate discover card primary key in seed data | "
                        f"category={category_key} section={section_id} card={card_id}"
                    )
                seen_rows.add(dedupe_key)

                card_rows.append(
                    {
                        "category_key": category_key,
                        "section_id": section_id,
                        "card_id": card_id,
                        "category_label": category_label,
                        "category_order": category_order,
                        "section_title": section_title,
                        "section_order": section_order,
                        "card_order": card_order,
                        "image_asset_id": image_asset_id,
                    }
                )

    return card_rows


def _expect_mapping(value: object, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"Expected mapping at {field}")
    return value


def _expect_str(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"Expected non-empty string at {field}")
    return value


async def seed_discover_catalog() -> None:
    asset_rows = _build_asset_rows()
    card_rows = _build_card_rows()

    logger.info(
        "Seeding discover catalog | assets=%s cards=%s",
        len(asset_rows),
        len(card_rows),
    )

    async with async_session_factory() as session:
        try:
            await session.execute(delete(DiscoverCard))
            await session.execute(delete(DiscoverAsset))
            await session.execute(insert(DiscoverAsset), asset_rows)
            await session.execute(insert(DiscoverCard), card_rows)
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    logger.info("Discover catalog seed completed")


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    asyncio.run(seed_discover_catalog())


if __name__ == "__main__":
    main()
