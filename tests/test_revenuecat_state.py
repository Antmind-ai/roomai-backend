from __future__ import annotations

from datetime import UTC, datetime, timedelta
import uuid

import pytest

from app.services.platform import revenuecat_api, revenuecat_service
from app.services.platform.endpoints import revenuecat as revenuecat_endpoint
from app.services.platform.models.subscription import PurchaseRecord


class _FakeResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _FakeAsyncSession:
    def __init__(self, value):
        self._value = value
        self.commit_count = 0
        self.rollback_count = 0

    async def execute(self, _statement):
        return _FakeResult(self._value)

    async def commit(self):
        self.commit_count += 1

    async def rollback(self):
        self.rollback_count += 1


class _FakeRequest:
    async def body(self):
        return b"{}"


def test_extract_active_entitlements_filters_expired_and_invalid_dates():
    now = datetime.now(UTC)
    subscriber = {
        "entitlements": {
            "active": {"expires_date": (now + timedelta(days=1)).isoformat()},
            "expired": {"expires_date": (now - timedelta(days=1)).isoformat()},
            "invalid": {"expires_date": "not-a-date"},
            "missing": {},
        }
    }

    active = revenuecat_api.extract_active_entitlements(subscriber)

    assert list(active.keys()) == ["active"]


@pytest.mark.asyncio
async def test_get_current_subscription_record_returns_none_for_latest_inactive():
    record = PurchaseRecord(
        user_id=uuid.uuid4(),
        revenuecat_event_id="evt_1",
        revenuecat_transaction_id="txn_1",
        revenuecat_product_id="weekly",
        event_type="EXPIRATION",
        environment="production",
        is_active_subscription=False,
    )
    db = _FakeAsyncSession(record)

    current = await revenuecat_service.get_current_subscription_record(
        db,
        user_id=record.user_id,
    )

    assert current is None


@pytest.mark.asyncio
async def test_revenuecat_webhook_records_subscription_state_only(monkeypatch):
    user_id = uuid.uuid4()
    db = _FakeAsyncSession(None)
    captured: dict[str, object] = {}

    event = {
        "event": {
            "type": "INITIAL_PURCHASE",
            "id": "evt_1",
            "product_id": "weekly",
            "transaction_id": "txn_1",
            "environment": "SANDBOX",
            "app_user_id": str(user_id),
            "expiration_at_ms": 1_800_000_000_000,
            "purchased_at_ms": 1_700_000_000_000,
        }
    }

    async def _fake_record_purchase_event(db, **kwargs):
        captured.update(kwargs)
        return None

    monkeypatch.setattr(revenuecat_endpoint.revenuecat_service, "parse_event", lambda _raw: event)
    monkeypatch.setattr(
        revenuecat_endpoint.revenuecat_service,
        "verify_webhook_secret",
        lambda _authorization: True,
    )
    monkeypatch.setattr(
        revenuecat_endpoint.revenuecat_service,
        "record_purchase_event",
        _fake_record_purchase_event,
    )

    result = await revenuecat_endpoint.revenuecat_webhook(
        _FakeRequest(),
        db=db,
        authorization="secret",
    )

    assert result == {"status": "ok", "result": "processed"}
    assert captured["user_id"] == user_id
    assert captured["event_type"] == "INITIAL_PURCHASE"
    assert captured["is_active"] is True
    assert set(captured) == {
        "user_id",
        "event_id",
        "event_type",
        "product_id",
        "transaction_id",
        "environment",
        "is_active",
        "purchased_at",
        "expires_at",
        "raw_payload",
    }
    assert db.commit_count == 1
