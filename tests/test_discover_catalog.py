from __future__ import annotations

from types import SimpleNamespace
import uuid

from fastapi import HTTPException
import pytest

from app.services.platform.endpoints import discover


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeAsyncSession:
    def __init__(self, rows):
        self._rows = rows
        self.executed_statement = None

    async def execute(self, statement):
        self.executed_statement = statement
        return _FakeResult(self._rows)


def _asset(asset_id: str, r2_key: str):
    return SimpleNamespace(asset_id=asset_id, r2_key=r2_key)


def _card(
    *,
    category_key: str,
    category_label: str,
    section_id: str,
    section_title: str,
    card_id: str,
    image_asset_id: str,
):
    return SimpleNamespace(
        category_key=category_key,
        category_label=category_label,
        section_id=section_id,
        section_title=section_title,
        card_id=card_id,
        image_asset_id=image_asset_id,
    )


@pytest.mark.asyncio
async def test_discover_catalog_groups_orders_and_builds_public_urls(monkeypatch):
    monkeypatch.setattr(discover.settings, "r2_public_url", "https://cdn.example.com/root/")
    rows = [
        (
            _card(
                category_key="home",
                category_label="Home",
                section_id="kitchen",
                section_title="Kitchen",
                card_id="kitchen-1",
                image_asset_id="asset-kitchen",
            ),
            _asset("asset-kitchen", "/assets/3-4/kitchen sample.webp"),
        ),
        (
            _card(
                category_key="home",
                category_label="Home",
                section_id="living-room",
                section_title="Living Room",
                card_id="living-room-1",
                image_asset_id="asset-living",
            ),
            _asset("asset-living", "assets/3-4/living-room.webp"),
        ),
        (
            _card(
                category_key="garden",
                category_label="Garden",
                section_id="garden-main",
                section_title="Garden",
                card_id="garden-main-1",
                image_asset_id="asset-garden",
            ),
            _asset("asset-garden", "assets/3-4/garden.webp"),
        ),
        (
            _card(
                category_key="exterior",
                category_label="Exterior Design",
                section_id="house",
                section_title="House",
                card_id="house-1",
                image_asset_id="asset-house",
            ),
            _asset("asset-house", "assets/3-4/house.webp"),
        ),
    ]
    db = _FakeAsyncSession(rows)

    response = await discover.get_discover_catalog(uuid.uuid4(), db)

    assert response.cache_max_age_seconds == discover.DISCOVER_CATALOG_CACHE_MAX_AGE_SECONDS
    assert response.expires_in_seconds == discover.DISCOVER_CATALOG_CACHE_MAX_AGE_SECONDS
    assert [section.id for section in response.categories.home.sections] == [
        "kitchen",
        "living-room",
    ]
    assert response.categories.home.sections[0].cards[0].id == "kitchen-1"
    assert (
        response.categories.home.sections[0].cards[0].image_url
        == "https://cdn.example.com/root/assets/3-4/kitchen%20sample.webp"
    )
    assert response.categories.garden.sections[0].id == "garden-main"
    assert response.categories.exterior.sections[0].id == "house"
    assert db.executed_statement is not None


@pytest.mark.asyncio
async def test_discover_catalog_requires_public_r2_url(monkeypatch):
    monkeypatch.setattr(discover.settings, "r2_public_url", None)
    db = _FakeAsyncSession([])

    with pytest.raises(HTTPException) as exc_info:
        await discover.get_discover_catalog(uuid.uuid4(), db)

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "Public object storage URL is not configured"
    assert db.executed_statement is None


@pytest.mark.asyncio
async def test_discover_catalog_requires_seeded_rows(monkeypatch):
    monkeypatch.setattr(discover.settings, "r2_public_url", "https://cdn.example.com")

    with pytest.raises(HTTPException) as exc_info:
        await discover.get_discover_catalog(uuid.uuid4(), _FakeAsyncSession([]))

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "Discover catalog is not seeded"


@pytest.mark.asyncio
async def test_discover_catalog_requires_all_categories(monkeypatch):
    monkeypatch.setattr(discover.settings, "r2_public_url", "https://cdn.example.com")
    rows = [
        (
            _card(
                category_key="home",
                category_label="Home",
                section_id="kitchen",
                section_title="Kitchen",
                card_id="kitchen-1",
                image_asset_id="asset-kitchen",
            ),
            _asset("asset-kitchen", "assets/3-4/kitchen.webp"),
        )
    ]

    with pytest.raises(HTTPException) as exc_info:
        await discover.get_discover_catalog(uuid.uuid4(), _FakeAsyncSession(rows))

    assert exc_info.value.status_code == 500
    assert (
        exc_info.value.detail
        == "Discover catalog seed data is missing categories: garden, exterior"
    )
