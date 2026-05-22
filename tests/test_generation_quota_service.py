from __future__ import annotations

from types import SimpleNamespace
import uuid

import pytest

from app.services.platform import generation_quota_service as quota_service
from app.services.platform.models import GenerationUsage


class _FakeDB:
    def __init__(self):
        self.added: list[object] = []
        self.flush_count = 0

    def add(self, value):
        self.added.append(value)

    async def flush(self):
        self.flush_count += 1
        for item in self.added:
            if getattr(item, "id", None) is None:
                item.id = uuid.uuid4()


@pytest.mark.asyncio
async def test_reserve_generation_quota_allows_one_free_lifetime_generation(monkeypatch):
    user_id = uuid.uuid4()
    db = _FakeDB()
    events: list[str] = []

    async def _fake_lock_active_user(db, *, user_id):
        events.append("lock")
        return SimpleNamespace(id=user_id)

    async def _fake_get_active_subscription(db, *, user_id):
        events.append("subscription")
        return None

    async def _fake_count_limited_usage(db, *, user_id, since=None):
        assert events[0] == "lock"
        events.append("count")
        return 0

    monkeypatch.setattr(quota_service, "_lock_active_user", _fake_lock_active_user)
    monkeypatch.setattr(quota_service, "_get_active_subscription", _fake_get_active_subscription)
    monkeypatch.setattr(quota_service, "_count_limited_usage", _fake_count_limited_usage)

    result = await quota_service.reserve_generation_quota(
        db,
        user_id,
        generation_type="design_request",
        reference_id="request-1",
    )

    assert result.usage_id is not None
    assert result.snapshot.quota_scope == "free_trial"
    assert result.snapshot.free_lifetime_generations_remaining == 1
    assert db.flush_count == 1
    assert len(db.added) == 1
    usage = db.added[0]
    assert isinstance(usage, GenerationUsage)
    assert usage.user_id == user_id
    assert usage.generation_type == "design_request"
    assert usage.reference_id == "request-1"
    assert usage.status == "reserved"


@pytest.mark.asyncio
async def test_reserve_generation_quota_blocks_after_free_lifetime_generation(monkeypatch):
    user_id = uuid.uuid4()
    db = _FakeDB()

    async def _fake_lock_active_user(db, *, user_id):
        return SimpleNamespace(id=user_id)

    async def _fake_get_active_subscription(db, *, user_id):
        return None

    async def _fake_count_limited_usage(db, *, user_id, since=None):
        return 1 if since is None else 0

    monkeypatch.setattr(quota_service, "_lock_active_user", _fake_lock_active_user)
    monkeypatch.setattr(quota_service, "_get_active_subscription", _fake_get_active_subscription)
    monkeypatch.setattr(quota_service, "_count_limited_usage", _fake_count_limited_usage)

    with pytest.raises(quota_service.GenerationQuotaExceededError) as exc_info:
        await quota_service.reserve_generation_quota(
            db,
            user_id,
            generation_type="design_request",
            reference_id="request-2",
        )

    assert exc_info.value.reason == "free_trial_exhausted"
    assert exc_info.value.snapshot.free_lifetime_generations_remaining == 0
    assert db.added == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("daily_used", "weekly_used", "expected_reason"),
    [
        (25, 40, "daily_generation_limit_reached"),
        (10, 100, "weekly_generation_limit_reached"),
    ],
)
async def test_reserve_generation_quota_blocks_paid_limits(
    monkeypatch,
    daily_used,
    weekly_used,
    expected_reason,
):
    user_id = uuid.uuid4()
    db = _FakeDB()
    count_values = [500, daily_used, weekly_used]

    async def _fake_lock_active_user(db, *, user_id):
        return SimpleNamespace(id=user_id)

    async def _fake_get_active_subscription(db, *, user_id):
        return SimpleNamespace(
            revenuecat_product_id=quota_service.settings.subscription_weekly_product_id
        )

    async def _fake_count_limited_usage(db, *, user_id, since=None):
        return count_values.pop(0)

    monkeypatch.setattr(quota_service, "_lock_active_user", _fake_lock_active_user)
    monkeypatch.setattr(quota_service, "_get_active_subscription", _fake_get_active_subscription)
    monkeypatch.setattr(quota_service, "_count_limited_usage", _fake_count_limited_usage)

    with pytest.raises(quota_service.GenerationQuotaExceededError) as exc_info:
        await quota_service.reserve_generation_quota(
            db,
            user_id,
            generation_type="design_request",
            reference_id="request-3",
        )

    assert exc_info.value.reason == expected_reason
    assert db.added == []


@pytest.mark.asyncio
async def test_release_generation_quota_marks_reserved_usage_released(monkeypatch):
    usage = SimpleNamespace(status="reserved", released_at=None)

    async def _fake_find_generation_usage(*_args, **_kwargs):
        return usage

    monkeypatch.setattr(quota_service, "_find_generation_usage", _fake_find_generation_usage)

    released = await quota_service.release_generation_quota(
        _FakeDB(),
        user_id=uuid.uuid4(),
        generation_type="design_request",
        reference_id="request-4",
    )

    assert released is True
    assert usage.status == "released"
    assert usage.released_at is not None
    assert "released" not in quota_service.COUNTED_USAGE_STATUSES
