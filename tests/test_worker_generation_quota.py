from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
import uuid

import pytest

from app.workers import tasks


class _FakeResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _FakeDB:
    def __init__(self, design_request):
        self.design_request = design_request
        self.commit_count = 0

    async def execute(self, _statement):
        return _FakeResult(self.design_request)

    async def commit(self):
        self.commit_count += 1


def _design_request(*, request_id: uuid.UUID, user_id: uuid.UUID) -> SimpleNamespace:
    return SimpleNamespace(
        id=request_id,
        user_id=user_id,
        source="upload",
        example_photo_id=None,
        prompt="refresh the room",
        building_type="living-room",
        style_id="modern",
        palette_id="surprise-me",
        status="queued",
        processing_started_at=None,
        failed_at=None,
        error_message=None,
        completed_at=None,
        output_preview_url=None,
    )


@pytest.mark.asyncio
async def test_process_design_request_task_completes_generation_quota(monkeypatch):
    request_id = uuid.uuid4()
    user_id = uuid.uuid4()
    design_request = _design_request(request_id=request_id, user_id=user_id)
    db_instances = [_FakeDB(design_request), _FakeDB(design_request)]

    @asynccontextmanager
    async def _fake_get_db_context():
        if not db_instances:
            raise AssertionError("Unexpected DB context request")
        yield db_instances.pop(0)

    async def _fake_resolve_input_image_path(_design_request):
        return Path("tests/mock-input.jpg"), False

    async def _fake_generate_image(*, prompt: str, image_path: str):
        assert "living-room" in prompt
        assert image_path == "tests/mock-input.jpg"
        return SimpleNamespace(
            url="https://example.com/output.png",
            model="fal-ai/nano-banana-pro/edit",
        )

    completed: list[tuple[uuid.UUID, str, str]] = []

    async def _fake_complete_generation_quota(db, *, user_id, generation_type, reference_id):
        assert db is not None
        completed.append((user_id, generation_type, reference_id))
        return True

    monkeypatch.setattr(tasks, "get_db_context", _fake_get_db_context)
    monkeypatch.setattr(tasks, "_resolve_input_image_path", _fake_resolve_input_image_path)
    monkeypatch.setattr(tasks, "generate_image", _fake_generate_image)
    monkeypatch.setattr(tasks, "complete_generation_quota", _fake_complete_generation_quota)

    result = await tasks.process_design_request_task({}, str(request_id))

    assert result["status"] == "completed"
    assert design_request.status == "completed"
    assert design_request.output_preview_url == "https://example.com/output.png"
    assert completed == [(user_id, "design_request", str(request_id))]


@pytest.mark.asyncio
async def test_process_design_request_task_releases_generation_quota_when_generation_fails(
    monkeypatch,
):
    request_id = uuid.uuid4()
    user_id = uuid.uuid4()
    design_request = _design_request(request_id=request_id, user_id=user_id)
    db_instances = [_FakeDB(design_request), _FakeDB(design_request)]

    @asynccontextmanager
    async def _fake_get_db_context():
        if not db_instances:
            raise AssertionError("Unexpected DB context request")
        yield db_instances.pop(0)

    async def _fake_resolve_input_image_path(_design_request):
        return Path("tests/mock-input.jpg"), False

    async def _fake_generate_image(*, prompt: str, image_path: str):
        assert "living-room" in prompt
        assert image_path == "tests/mock-input.jpg"
        raise tasks.DesignGenerationError("fal.ai generation request failed: timeout")

    released: list[tuple[uuid.UUID, str, str]] = []

    async def _fake_release_generation_quota(db, *, user_id, generation_type, reference_id):
        assert db is not None
        released.append((user_id, generation_type, reference_id))
        return True

    monkeypatch.setattr(tasks, "get_db_context", _fake_get_db_context)
    monkeypatch.setattr(tasks, "_resolve_input_image_path", _fake_resolve_input_image_path)
    monkeypatch.setattr(tasks, "generate_image", _fake_generate_image)
    monkeypatch.setattr(tasks, "release_generation_quota", _fake_release_generation_quota)

    result = await tasks.process_design_request_task({}, str(request_id))

    assert result["status"] == "failed"
    assert design_request.status == "failed"
    assert design_request.failed_at is not None
    assert "fal.ai generation request failed" in design_request.error_message
    assert released == [(user_id, "design_request", str(request_id))]


@pytest.mark.asyncio
async def test_process_object_replace_task_releases_generation_quota_when_generation_fails(
    monkeypatch,
    tmp_path,
):
    request_id = uuid.uuid4()
    user_id = uuid.uuid4()
    design_request = _design_request(request_id=request_id, user_id=user_id)
    image_path = tmp_path / "input.jpg"
    image_path.write_bytes(b"image-bytes")
    db_instances = [_FakeDB(design_request), _FakeDB(design_request)]

    @asynccontextmanager
    async def _fake_get_db_context():
        if not db_instances:
            raise AssertionError("Unexpected DB context request")
        yield db_instances.pop(0)

    async def _fake_resolve_input_image_path(_design_request):
        return image_path, False

    async def _fake_replace_object_from_uploaded_image(**_kwargs):
        raise tasks.fal_service.ObjectReplaceFalError("object replace failed")

    released: list[tuple[uuid.UUID, str, str]] = []

    async def _fake_release_generation_quota(db, *, user_id, generation_type, reference_id):
        assert db is not None
        released.append((user_id, generation_type, reference_id))
        return True

    monkeypatch.setattr(tasks, "get_db_context", _fake_get_db_context)
    monkeypatch.setattr(tasks, "_resolve_input_image_path", _fake_resolve_input_image_path)
    monkeypatch.setattr(
        tasks.fal_service,
        "replace_object_from_uploaded_image",
        _fake_replace_object_from_uploaded_image,
    )
    monkeypatch.setattr(tasks, "release_generation_quota", _fake_release_generation_quota)

    result = await tasks.process_object_replace_request_task(
        {},
        str(request_id),
        "image/jpeg",
        "room.jpg",
        10,
        12,
        "chair",
        100,
        100,
    )

    assert result["status"] == "failed"
    assert design_request.status == "failed"
    assert released == [(user_id, "object_replace", str(request_id))]
