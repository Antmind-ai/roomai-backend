from __future__ import annotations

from collections.abc import Callable
import os
from typing import Any

import fal_client
from loguru import logger

from app.core.config import settings
from app.services.object_replace.schemas import ObjectReplacePoint


class ObjectReplaceFalError(RuntimeError):
    """Raised when fal.ai cannot complete the Object Replace pipeline."""


def _require_fal_key() -> None:
    if not settings.fal_key:
        raise ObjectReplaceFalError("FAL_KEY is required for Object Replace")
    os.environ["FAL_KEY"] = settings.fal_key


def _extract_request_id(output: dict[str, Any], enqueued_request_id: str | None) -> str | None:
    request_id = output.get("request_id")
    if isinstance(request_id, str) and request_id:
        return request_id
    return enqueued_request_id


def extract_mask_url(output: dict[str, Any]) -> str:
    mask_url = output.get("mask_url")
    if isinstance(mask_url, str) and mask_url:
        return mask_url

    mask = output.get("mask")
    if isinstance(mask, dict):
        url = mask.get("url")
        if isinstance(url, str) and url:
            return url

    masks = output.get("masks")
    if isinstance(masks, list):
        for item in masks:
            if not isinstance(item, dict):
                continue
            url = item.get("url")
            if isinstance(url, str) and url:
                return url

    image = output.get("image")
    if isinstance(image, dict):
        url = image.get("url")
        if isinstance(url, str) and url:
            return url

    raise ObjectReplaceFalError("fal.ai segmentation response did not include a mask URL")


def extract_fill_image_url(output: dict[str, Any]) -> str:
    images = output.get("images")
    if isinstance(images, list):
        for item in images:
            if not isinstance(item, dict):
                continue
            url = item.get("url")
            if isinstance(url, str) and url:
                return url

    raise ObjectReplaceFalError("fal.ai fill response did not include an image URL")


def _log_queue_update(stage: str) -> Callable[[Any], None]:
    def _handler(update: Any) -> None:
        status = getattr(update, "status", None)
        if status is None and isinstance(update, dict):
            status = update.get("status")
        if status != "IN_PROGRESS":
            return

        logs = getattr(update, "logs", None)
        if logs is None and isinstance(update, dict):
            logs = update.get("logs")
        if not isinstance(logs, list):
            return

        for log in logs:
            message = log.get("message") if isinstance(log, dict) else getattr(log, "message", None)
            if message:
                logger.debug("[object-replace:{}] {}", stage, message)

    return _handler


async def _subscribe(
    *,
    model_id: str,
    arguments: dict[str, Any],
    stage: str,
) -> tuple[dict[str, Any], str | None]:
    _require_fal_key()
    enqueued_request_id: str | None = None

    def _capture_request_id(request_id: str) -> None:
        nonlocal enqueued_request_id
        enqueued_request_id = request_id

    try:
        output = await fal_client.subscribe_async(
            model_id,
            arguments=arguments,
            with_logs=True,
            on_enqueue=_capture_request_id,
            on_queue_update=_log_queue_update(stage),
            client_timeout=settings.fal_timeout_ms / 1000,
        )
    except Exception as exc:
        logger.exception("fal.ai {} request failed | model={}", stage, model_id)
        raise ObjectReplaceFalError(f"fal.ai {stage} request failed") from exc

    if not isinstance(output, dict):
        raise ObjectReplaceFalError(
            f"Invalid fal.ai {stage} response type: {type(output).__name__}"
        )

    return output, _extract_request_id(output, enqueued_request_id)


async def generate_mask(
    *,
    image_url: str,
    point: ObjectReplacePoint,
) -> tuple[str, str | None]:
    output, request_id = await _subscribe(
        model_id=settings.fal_segmentation_model_id,
        arguments={
            "image_url": image_url,
            "points": [
                {
                    "x": point.x,
                    "y": point.y,
                    "label": 1,
                }
            ],
        },
        stage="mask",
    )
    return extract_mask_url(output), request_id


async def inpaint_object(
    *,
    image_url: str,
    mask_url: str,
    prompt: str,
) -> tuple[str, str | None, str]:
    output, request_id = await _subscribe(
        model_id=settings.fal_fill_model_id,
        arguments={
            "image_url": image_url,
            "mask_url": mask_url,
            "prompt": prompt,
            "enhance_prompt": True,
            "num_images": 1,
            "output_format": "jpeg",
            "safety_tolerance": "2",
        },
        stage="fill",
    )
    final_prompt = output.get("prompt")
    return (
        extract_fill_image_url(output),
        request_id,
        final_prompt if isinstance(final_prompt, str) else prompt,
    )


async def replace_object(
    *,
    image_url: str,
    point: ObjectReplacePoint,
    prompt: str,
) -> dict[str, str | None]:
    mask_url, mask_request_id = await generate_mask(image_url=image_url, point=point)
    image_url_out, fill_request_id, final_prompt = await inpaint_object(
        image_url=image_url,
        mask_url=mask_url,
        prompt=prompt,
    )

    return {
        "image_url": image_url_out,
        "mask_url": mask_url,
        "request_id": fill_request_id,
        "mask_request_id": mask_request_id,
        "fill_request_id": fill_request_id,
        "prompt": final_prompt,
    }
