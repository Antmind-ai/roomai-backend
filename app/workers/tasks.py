from datetime import UTC, datetime
from typing import Any
import uuid

from loguru import logger
from sqlalchemy import select

from app.core.database import get_db_context
from app.services.platform.models import DesignRequest


async def health_ping_task(ctx: dict[str, Any], source: str = "api") -> dict[str, str]:
    """Simple ARQ job used to verify worker + Redis wiring."""
    logger.info("ARQ job received | source={}", source)
    return {
        "status": "ok",
        "source": source,
        "processed_at": datetime.now(UTC).isoformat(),
    }


async def process_design_request_task(
    ctx: dict[str, Any],
    design_request_id: str,
) -> dict[str, str]:
    """Mark design requests as processed by the queue worker."""
    try:
        request_id = uuid.UUID(design_request_id)
    except ValueError as exc:
        logger.error("Invalid design_request_id for ARQ task | id={}", design_request_id)
        raise RuntimeError("Invalid design_request_id") from exc

    logger.info("Processing design request ARQ job | request_id={}", request_id)

    async with get_db_context() as db:
        result = await db.execute(select(DesignRequest).where(DesignRequest.id == request_id))
        design_request = result.scalar_one_or_none()

        if design_request is None:
            logger.error("Design request not found for ARQ task | request_id={}", request_id)
            return {
                "status": "missing",
                "design_request_id": design_request_id,
            }

        design_request.status = "processing"
        design_request.processing_started_at = datetime.now(UTC)
        design_request.failed_at = None
        design_request.error_message = None
        await db.commit()

    try:
        async with get_db_context() as db:
            result = await db.execute(select(DesignRequest).where(DesignRequest.id == request_id))
            design_request = result.scalar_one_or_none()

            if design_request is None:
                logger.error("Design request missing during completion | request_id={}", request_id)
                return {
                    "status": "missing",
                    "design_request_id": design_request_id,
                }

            design_request.status = "completed"
            design_request.completed_at = datetime.now(UTC)
            await db.commit()
    except Exception as exc:
        async with get_db_context() as db:
            result = await db.execute(select(DesignRequest).where(DesignRequest.id == request_id))
            design_request = result.scalar_one_or_none()

            if design_request is not None:
                design_request.status = "failed"
                design_request.failed_at = datetime.now(UTC)
                design_request.error_message = str(exc)[:500]
                await db.commit()

        logger.exception("Design request ARQ task failed | request_id={}", request_id)
        raise

    logger.info("Design request completed by ARQ worker | request_id={}", request_id)
    return {
        "status": "completed",
        "design_request_id": design_request_id,
    }
