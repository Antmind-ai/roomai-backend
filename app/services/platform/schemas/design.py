from datetime import datetime
from enum import Enum
import uuid

from pydantic import BaseModel, Field, model_validator


class DesignSource(str, Enum):
    UPLOAD = "upload"
    EXAMPLE = "example"


class DesignInputUploadResponse(BaseModel):
    upload_id: uuid.UUID
    user_id: uuid.UUID
    filename: str
    content_type: str
    size_bytes: int


class CreateDesignRequest(BaseModel):
    source: DesignSource
    input_upload_id: uuid.UUID | None = None
    example_photo_id: str | None = Field(default=None, max_length=120)
    building_type: str = Field(..., min_length=1, max_length=80)
    style_id: str = Field(..., min_length=1, max_length=80)
    palette_id: str = Field(..., min_length=1, max_length=80)
    prompt: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_source_inputs(self) -> "CreateDesignRequest":
        if self.source == DesignSource.UPLOAD and self.input_upload_id is None:
            raise ValueError("input_upload_id is required when source is 'upload'")
        if self.source == DesignSource.EXAMPLE and not self.example_photo_id:
            raise ValueError("example_photo_id is required when source is 'example'")
        return self


class CreateDesignResponse(BaseModel):
    design_request_id: uuid.UUID
    user_id: uuid.UUID
    status: str
    submitted_at: datetime
    queue_job_id: str | None = None
    prompt: str | None = None


class DesignHistoryItem(BaseModel):
    design_request_id: uuid.UUID
    user_id: uuid.UUID
    source: DesignSource
    status: str
    input_upload_id: uuid.UUID | None = None
    building_type: str
    style_id: str
    palette_id: str
    prompt: str | None = None
    submitted_at: datetime
    updated_at: datetime
    preview_url: str | None = None
    output_preview_url: str | None = None


class DesignHistoryResponse(BaseModel):
    items: list[DesignHistoryItem]
