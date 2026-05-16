from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from app.services.platform.endpoints import auth
from app.services.platform.models.credit import CreditLedgerEvent
from app.services.platform.schemas.auth import DeviceLoginRequest


class _FakeResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value

    def scalar_one(self):
        if self._value is None:
            raise AssertionError("Expected a scalar value")
        return self._value


class _FakeAsyncSession:
    def __init__(self, *, execute_results, flush_effects):
        self._execute_results = list(execute_results)
        self._flush_effects = list(flush_effects)
        self.added: list[object] = []
        self.commit_count = 0
        self.refresh_count = 0
        self.rollback_count = 0

    async def execute(self, _statement):
        if not self._execute_results:
            raise AssertionError("Unexpected execute call")
        return _FakeResult(self._execute_results.pop(0))

    def add(self, value):
        self.added.append(value)

    async def flush(self):
        if not self._flush_effects:
            return
        effect = self._flush_effects.pop(0)
        if isinstance(effect, BaseException):
            raise effect

    async def commit(self):
        self.commit_count += 1

    async def refresh(self, _value):
        self.refresh_count += 1

    async def rollback(self):
        self.rollback_count += 1


@pytest.mark.asyncio
async def test_device_login_reactivation_preserves_existing_balance(monkeypatch):
    user_id = uuid.uuid4()
    now_before = datetime.now(UTC)
    reactivated_user = SimpleNamespace(
        id=user_id,
        device_id="device-123",
        deleted_at=datetime(2026, 5, 1, tzinfo=UTC),
        credit_balance=7,
        onboarding_completed=True,
        last_seen_at=None,
    )
    db = _FakeAsyncSession(
        execute_results=[None, reactivated_user],
        flush_effects=[IntegrityError("insert", {}, Exception("duplicate")), None],
    )

    monkeypatch.setattr(auth, "create_access_token", lambda subject: f"token-for:{subject}")

    response = await auth.device_login(DeviceLoginRequest(device_id="device-123"), db)

    assert response.user_id == user_id
    assert response.access_token == f"token-for:{user_id}"
    assert reactivated_user.credit_balance == 7
    assert reactivated_user.deleted_at is None
    assert reactivated_user.onboarding_completed is False
    assert reactivated_user.last_seen_at is not None
    assert reactivated_user.last_seen_at >= now_before
    assert db.rollback_count == 1
    assert not any(isinstance(item, CreditLedgerEvent) for item in db.added)
