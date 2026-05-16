from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.services.object_replace import fal_service, storage
from app.services.object_replace.schemas import (
    CreateObjectReplaceUploadRequest,
    ObjectReplaceResponse,
    ObjectReplaceUploadResponse,
    ReplaceObjectRequest,
)
from app.services.platform.endpoints.auth import get_current_user_id

router = APIRouter(prefix="/object-replace", tags=["Object Replace"])


@router.post(
    "/uploads",
    response_model=ObjectReplaceUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a presigned upload URL for Object Replace",
)
async def create_object_replace_upload(
    payload: CreateObjectReplaceUploadRequest,
    current_user_id=Depends(get_current_user_id),
) -> ObjectReplaceUploadResponse:
    try:
        upload = await storage.create_presigned_upload_async(
            user_id=current_user_id,
            file_name=payload.file_name,
            content_type=payload.content_type,
            size_bytes=payload.size_bytes,
            image_width=payload.image_width,
            image_height=payload.image_height,
        )
    except storage.ObjectReplaceStorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return ObjectReplaceUploadResponse(
        upload_id=upload.upload_id,
        object_key=upload.object_key,
        upload_url=upload.upload_url,
        original_image_url=upload.original_image_url,
        headers=upload.headers,
        expires_in=upload.expires_in,
    )


@router.post(
    "",
    response_model=ObjectReplaceResponse,
    summary="Replace an object in an uploaded image using a tap point and prompt",
)
async def replace_object_in_image(
    payload: ReplaceObjectRequest,
    _current_user_id=Depends(get_current_user_id),
) -> ObjectReplaceResponse:
    try:
        result = await fal_service.replace_object(
            image_url=payload.original_image_url,
            point=payload.point,
            prompt=payload.prompt,
        )
    except fal_service.ObjectReplaceFalError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return ObjectReplaceResponse(
        image_url=str(result["image_url"]),
        mask_url=str(result["mask_url"]),
        original_image_url=payload.original_image_url,
        request_id=result["request_id"],
        mask_request_id=result["mask_request_id"],
        fill_request_id=result["fill_request_id"],
        prompt=str(result["prompt"]),
    )
