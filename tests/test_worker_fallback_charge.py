from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
import uuid

import pytest

from app.services.platform.credit_service import InsufficientCreditsError
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


@pytest.mark.asyncio
async def test_process_design_request_task_fails_when_fallback_charge_cannot_be_collected(
    monkeypatch,
):
    request_id = uuid.uuid4()
    user_id = uuid.uuid4()
    design_request = SimpleNamespace(
        id=request_id,
        user_id=user_id,
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

    db_instances = [_FakeDB(design_request), _FakeDB(design_request), _FakeDB(design_request)]

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

    async def _fake_consume_credit(*args, **kwargs):
        raise InsufficientCreditsError(balance=0, required_credits=50)

    monkeypatch.setattr(tasks, "get_db_context", _fake_get_db_context)
    monkeypatch.setattr(tasks, "_resolve_input_image_path", _fake_resolve_input_image_path)
    monkeypatch.setattr(tasks, "generate_image", _fake_generate_image)
    monkeypatch.setattr(tasks, "get_model_credit_cost", lambda _model: 75)
    monkeypatch.setattr(tasks, "consume_credit", _fake_consume_credit)

    result = await tasks.process_design_request_task({}, str(request_id))

    assert result["status"] == "failed"
    assert design_request.status == "failed"
    assert design_request.output_preview_url is None
    assert design_request.completed_at is None
    assert design_request.failed_at is not None
    assert "additional credits" in design_request.error_message.lower()
