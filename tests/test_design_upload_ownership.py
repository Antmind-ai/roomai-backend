from __future__ import annotations

import uuid

from fastapi import HTTPException
import pytest

from app.services.platform.endpoints import design


def test_validate_r2_upload_ownership_accepts_matching_user_key(monkeypatch):
    current_user_id = uuid.uuid4()
    upload_id = uuid.uuid4()
    key = f"{current_user_id}/{upload_id}.jpg"

    monkeypatch.setattr(design, "object_exists", lambda value: value == key)

    resolved_key = design._validate_r2_upload_ownership(
        current_user_id=current_user_id,
        input_upload_id=upload_id,
        input_r2_key=key,
    )

    assert resolved_key == key


def test_validate_r2_upload_ownership_rejects_foreign_key(monkeypatch):
    current_user_id = uuid.uuid4()
    upload_id = uuid.uuid4()
    foreign_key = f"{uuid.uuid4()}/{upload_id}.jpg"

    def _unexpected_call(_value: str) -> bool:
        raise AssertionError("object_exists should not be called for foreign keys")

    monkeypatch.setattr(design, "object_exists", _unexpected_call)

    with pytest.raises(HTTPException) as exc_info:
        design._validate_r2_upload_ownership(
            current_user_id=current_user_id,
            input_upload_id=upload_id,
            input_r2_key=foreign_key,
        )

    assert exc_info.value.status_code == 403
