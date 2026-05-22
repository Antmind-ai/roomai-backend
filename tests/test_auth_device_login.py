from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from app.services.platform.endpoints import auth
from app.services.platform.models.user import DeviceUser
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

    def one_or_none(self):
        return self._value


class _FakeAsyncSession:
    def __init__(self, *, execute_results, flush_effects=None):
        self._execute_results = list(execute_results)
        self._flush_effects = list(flush_effects or [])
        self.added: list[object] = []
        self.deleted: list[object] = []
        self.commit_count = 0
        self.refresh_count = 0
        self.rollback_count = 0

    async def execute(self, _statement):
        if not self._execute_results:
            raise AssertionError("Unexpected execute call")
        return _FakeResult(self._execute_results.pop(0))

    def add(self, value):
        if hasattr(value, "id") and getattr(value, "id", None) is None:
            value.id = uuid.uuid4()
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

    async def delete(self, value):
        self.deleted.append(value)


@pytest.mark.asyncio
async def test_device_login_new_device_creates_user(monkeypatch):
    db = _FakeAsyncSession(
        execute_results=[None],
        flush_effects=[None],
    )

    monkeypatch.setattr(auth, "create_access_token", lambda subject: f"token-for:{subject}")

    response = await auth.device_login(DeviceLoginRequest(device_id="device-123"), db)

    created_user = next(item for item in db.added if isinstance(item, DeviceUser))

    assert response.user_id == created_user.id
    assert db.commit_count == 1


@pytest.mark.asyncio
async def test_device_login_existing_active_device_updates_last_seen(monkeypatch):
    user_id = uuid.uuid4()
    now_before = datetime.now(UTC)
    existing_user = SimpleNamespace(
        id=user_id,
        device_id="device-123",
        deleted_at=None,
        onboarding_completed=True,
        last_seen_at=None,
    )
    db = _FakeAsyncSession(execute_results=[existing_user])

    monkeypatch.setattr(auth, "create_access_token", lambda subject: f"token-for:{subject}")

    response = await auth.device_login(DeviceLoginRequest(device_id="device-123"), db)

    assert response.user_id == user_id
    assert existing_user.onboarding_completed is True
    assert existing_user.last_seen_at is not None
    assert existing_user.last_seen_at >= now_before


@pytest.mark.asyncio
async def test_device_login_deleted_user_creates_new_user(monkeypatch):
    deleted_user_id = uuid.uuid4()
    deleted_user = SimpleNamespace(
        id=deleted_user_id,
        device_id="device-123",
        deleted_at=datetime(2026, 5, 1, tzinfo=UTC),
        onboarding_completed=True,
        last_seen_at=None,
    )
    db = _FakeAsyncSession(execute_results=[deleted_user])

    monkeypatch.setattr(auth, "create_access_token", lambda subject: f"token-for:{subject}")

    response = await auth.device_login(DeviceLoginRequest(device_id="device-123"), db)

    assert response.user_id != deleted_user_id
    assert response.access_token == f"token-for:{response.user_id}"
    assert deleted_user in db.deleted
    assert db.rollback_count == 0


@pytest.mark.asyncio
async def test_device_login_concurrent_duplicate_device_reuses_existing_user(
    monkeypatch,
):
    user_id = uuid.uuid4()
    existing_user = SimpleNamespace(
        id=user_id,
        device_id="device-123",
        deleted_at=None,
        onboarding_completed=True,
        last_seen_at=None,
    )
    db = _FakeAsyncSession(
        execute_results=[None, existing_user],
        flush_effects=[IntegrityError("insert", {}, Exception("duplicate"))],
    )

    monkeypatch.setattr(auth, "create_access_token", lambda subject: f"token-for:{subject}")

    response = await auth.device_login(DeviceLoginRequest(device_id="device-123"), db)

    assert response.user_id == user_id
    assert db.rollback_count == 1


@pytest.mark.asyncio
async def test_delete_account_deletes_user(monkeypatch):
    user_id = uuid.uuid4()
    user = SimpleNamespace(
        id=user_id,
        deleted_at=None,
    )
    db = _FakeAsyncSession(execute_results=[user])

    async def _no_subscription(*args, **kwargs):
        return None

    async def _fake_enqueue_job(function_name, *args, **kwargs):
        assert function_name == "cleanup_user_data_task"
        assert args == (str(user_id),)
        return "cleanup-job-123"

    monkeypatch.setattr(
        auth.revenuecat_service,
        "get_current_subscription_record",
        _no_subscription,
    )
    monkeypatch.setattr("app.workers.client.enqueue_job", _fake_enqueue_job)

    response = await auth.delete_account(current_user_id=user_id, db=db)

    assert response.user_id == user_id
    assert response.job_id == "cleanup-job-123"
    assert user in db.deleted
