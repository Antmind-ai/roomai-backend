from __future__ import annotations

from datetime import UTC, datetime, timedelta
import uuid

import pytest

from app.services.platform import revenuecat_api, revenuecat_service
from app.services.platform.models.subscription import PurchaseRecord


class _FakeResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _FakeAsyncSession:
    def __init__(self, value):
        self._value = value

    async def execute(self, _statement):
        return _FakeResult(self._value)


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
        credit_amount_granted=0,
        is_active_subscription=False,
    )
    db = _FakeAsyncSession(record)

    current = await revenuecat_service.get_current_subscription_record(
        db,
        user_id=record.user_id,
    )

    assert current is None
