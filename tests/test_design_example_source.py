from __future__ import annotations

from datetime import UTC, datetime
import uuid

from fastapi import HTTPException
import pytest

from app.services.platform.endpoints import design
from app.services.platform.schemas.design import CreateDesignRequest, DesignSource


class _FakeResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _FakeLookupDB:
    def __init__(self, resolved_key: str | None):
        self.resolved_key = resolved_key
        self.execute_count = 0

    async def execute(self, _statement):
        self.execute_count += 1
        return _FakeResult(self.resolved_key)


class _FakeSubmitDB:
    def __init__(self):
        self.added: list[object] = []
        self.flush_count = 0
        self.commit_count = 0
        self.refresh_count = 0
        self.rollback_count = 0

    async def execute(self, _statement):
        raise AssertionError("submit test should not call execute directly")

    def add(self, value):
        self.added.append(value)

    async def flush(self):
        self.flush_count += 1
        for item in self.added:
            if getattr(item, "id", None) is None:
                item.id = uuid.uuid4()

    async def commit(self):
        self.commit_count += 1

    async def refresh(self, value):
        self.refresh_count += 1
        if getattr(value, "submitted_at", None) is None:
            value.submitted_at = datetime.now(UTC)

    async def rollback(self):
        self.rollback_count += 1


@pytest.mark.asyncio
async def test_resolve_example_input_refs_returns_r2_key_for_known_card(monkeypatch, tmp_path):
    expected_key = "assets/3-4/discover-kitchen.webp"
    db = _FakeLookupDB(expected_key)

    monkeypatch.setattr(design.settings, "r2_endpoint_url", "https://r2.example.com")
    monkeypatch.setattr(design.settings, "r2_bucket_name", "roomai")
    monkeypatch.setattr(design, "object_exists", lambda key: key == expected_key)
    monkeypatch.setattr(design, "DISCOVER_SAMPLE_ASSETS_DIR", tmp_path / "non-existent")

    resolved_r2_key, local_filename = await design._resolve_example_input_refs(
        db=db,
        current_user_id=uuid.uuid4(),
        example_photo_id="kitchen-1",
    )

    assert resolved_r2_key == expected_key
    assert local_filename is None
    assert db.execute_count == 1


@pytest.mark.asyncio
async def test_resolve_example_input_refs_rejects_unknown_card(monkeypatch, tmp_path):
    db = _FakeLookupDB(None)

    monkeypatch.setattr(design.settings, "r2_endpoint_url", "https://r2.example.com")
    monkeypatch.setattr(design.settings, "r2_bucket_name", "roomai")
    monkeypatch.setattr(design, "DISCOVER_SAMPLE_ASSETS_DIR", tmp_path / "non-existent")

    def _unexpected_object_exists(_key: str) -> bool:
        raise AssertionError("object_exists should not run when card lookup misses")

    monkeypatch.setattr(design, "object_exists", _unexpected_object_exists)

    with pytest.raises(HTTPException) as exc_info:
        await design._resolve_example_input_refs(
            db=db,
            current_user_id=uuid.uuid4(),
            example_photo_id="unknown-card",
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Example photo not found"
    assert db.execute_count == 1


@pytest.mark.asyncio
async def test_resolve_example_input_refs_requires_storage_or_local_sample(monkeypatch, tmp_path):
    db = _FakeLookupDB("assets/3-4/discover-kitchen.webp")

    monkeypatch.setattr(design.settings, "r2_endpoint_url", None)
    monkeypatch.setattr(design.settings, "r2_bucket_name", "roomai")
    monkeypatch.setattr(design, "DISCOVER_SAMPLE_ASSETS_DIR", tmp_path / "non-existent")

    with pytest.raises(HTTPException) as exc_info:
        await design._resolve_example_input_refs(
            db=db,
            current_user_id=uuid.uuid4(),
            example_photo_id="kitchen-1",
        )

    assert exc_info.value.status_code == 503
    assert (
        exc_info.value.detail
        == "Object storage is not configured and local sample assets are unavailable"
    )
    assert db.execute_count == 1


@pytest.mark.asyncio
async def test_resolve_example_input_refs_rejects_missing_asset_object_when_local_unavailable(
    monkeypatch,
    tmp_path,
):
    db = _FakeLookupDB("assets/3-4/discover-kitchen.webp")

    monkeypatch.setattr(design.settings, "r2_endpoint_url", "https://r2.example.com")
    monkeypatch.setattr(design.settings, "r2_bucket_name", "roomai")
    monkeypatch.setattr(design, "object_exists", lambda _key: False)
    monkeypatch.setattr(design, "DISCOVER_SAMPLE_ASSETS_DIR", tmp_path / "non-existent")

    with pytest.raises(HTTPException) as exc_info:
        await design._resolve_example_input_refs(
            db=db,
            current_user_id=uuid.uuid4(),
            example_photo_id="kitchen-1",
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Example photo asset not found in storage"


@pytest.mark.asyncio
async def test_resolve_example_input_refs_uses_local_sample_fallback_when_asset_missing(
    monkeypatch,
    tmp_path,
):
    db = _FakeLookupDB("assets/3-4/discover-kitchen.webp")
    current_user_id = uuid.uuid4()

    sample_dir = tmp_path / "discover-samples"
    sample_dir.mkdir(parents=True, exist_ok=True)
    sample_file = sample_dir / "discover-kitchen.webp"
    sample_file.write_bytes(b"sample")

    upload_dir = tmp_path / "uploads"
    monkeypatch.setattr(design.settings, "design_upload_dir", str(upload_dir))
    monkeypatch.setattr(design.settings, "r2_endpoint_url", "https://r2.example.com")
    monkeypatch.setattr(design.settings, "r2_bucket_name", "roomai")
    monkeypatch.setattr(design, "object_exists", lambda _key: False)
    monkeypatch.setattr(design, "DISCOVER_SAMPLE_ASSETS_DIR", sample_dir)

    resolved_r2_key, local_filename = await design._resolve_example_input_refs(
        db=db,
        current_user_id=current_user_id,
        example_photo_id="kitchen-1",
    )

    assert resolved_r2_key is None
    assert local_filename is not None
    copied_file = upload_dir / str(current_user_id) / local_filename
    assert copied_file.exists()
    assert copied_file.read_bytes() == b"sample"


@pytest.mark.asyncio
async def test_submit_design_request_example_uses_server_resolved_r2_key(monkeypatch):
    current_user_id = uuid.uuid4()
    expected_key = "assets/3-4/discover-kitchen.webp"
    db = _FakeSubmitDB()

    async def _fake_resolve_example_input_refs(*, db, current_user_id, example_photo_id):
        assert example_photo_id == "kitchen-1"
        assert db is not None
        assert current_user_id is not None
        return expected_key, None

    async def _fake_reserve_generation_quota(*args, **kwargs):
        assert kwargs["user_id"] == current_user_id
        assert kwargs["generation_type"] == "design_request"
        assert kwargs["reference_id"]

    async def _fake_enqueue_job(task_name: str, **kwargs):
        assert task_name == "process_design_request_task"
        assert "design_request_id" in kwargs
        return "job-example-123"

    monkeypatch.setattr(
        design,
        "_resolve_example_input_refs",
        _fake_resolve_example_input_refs,
    )
    monkeypatch.setattr(design, "reserve_generation_quota", _fake_reserve_generation_quota)
    monkeypatch.setattr(design, "enqueue_job", _fake_enqueue_job)

    payload = CreateDesignRequest(
        source=DesignSource.EXAMPLE,
        input_r2_key="malicious/client-key.webp",
        example_photo_id="kitchen-1",
        building_type="living-room",
        style_id="modern",
        palette_id="surprise-me",
        prompt="refresh the room",
    )

    response = await design.submit_design_request(
        payload=payload,
        current_user_id=current_user_id,
        db=db,
    )

    assert db.flush_count == 1
    assert db.commit_count == 1
    assert db.refresh_count == 1
    assert db.rollback_count == 0
    assert len(db.added) == 1

    design_request = db.added[0]
    assert design_request.source == DesignSource.EXAMPLE.value
    assert design_request.input_upload_id is None
    assert design_request.input_filename is None
    assert design_request.input_r2_key == expected_key
    assert design_request.example_photo_id == "kitchen-1"
    assert design_request.queue_job_id == "job-example-123"

    assert response.user_id == current_user_id
    assert response.status == "queued"
    assert response.queue_job_id == "job-example-123"
