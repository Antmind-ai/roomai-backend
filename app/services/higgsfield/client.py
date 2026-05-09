from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from loguru import logger

from app.core.config import settings


GENERATE_TIMEOUT = settings.higgsfield_timeout_minutes * 60


class HiggsfieldError(Exception):
    pass


class HiggsfieldGenerateResult:
    def __init__(self, url: str, media_type: str, job_id: str | None = None) -> None:
        self.url = url
        self.media_type = media_type  # "image" or "video"
        self.job_id = job_id


async def _run_higgsfield(
    *args: str,
    timeout: int = GENERATE_TIMEOUT,
) -> tuple[int, str, str]:
    cmd = [settings.higgsfield_bin, *args]
    logger.info("Higgsfield CLI | spawning | cmd={}", " ".join(cmd))

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
        raise HiggsfieldError(
            f"Higgsfield CLI timed out after {timeout}s"
        )

    stdout_str = stdout.decode("utf-8", errors="replace").strip()
    stderr_str = stderr.decode("utf-8", errors="replace").strip()

    logger.info(
        "Higgsfield CLI | exit={} | stdout_len={} | stderr_len={}",
        process.returncode,
        len(stdout_str),
        len(stderr_str),
    )

    return process.returncode or 0, stdout_str, stderr_str


def _parse_result(output: str) -> HiggsfieldGenerateResult:
    try:
        data: list[dict[str, Any]] = json.loads(output)
    except json.JSONDecodeError:
        raise HiggsfieldError(f"Failed to parse Higgsfield JSON output: {output[:500]}")

    if not data:
        raise HiggsfieldError("Higgsfield returned empty result array")

    job: dict[str, Any] = data[-1]
    job_id = job.get("id")

    result = job.get("result")
    if not result:
        raise HiggsfieldError(
            f"Higgsfield job has no result field | job_id={job_id} | status={job.get('status')}"
        )

    media = result.get("media")
    if isinstance(media, list) and media:
        item = media[0]
        url = item.get("url")
        if url:
            return HiggsfieldGenerateResult(
                url=url,
                media_type=item.get("type", "image"),
                job_id=job_id,
            )

    if isinstance(media, dict):
        url = media.get("url")
        if url:
            return HiggsfieldGenerateResult(
                url=url,
                media_type=media.get("type", "image"),
                job_id=job_id,
            )

    url = result.get("url")
    if url:
        return HiggsfieldGenerateResult(
            url=url,
            media_type="image",
            job_id=job_id,
        )

    raise HiggsfieldError(
        f"Could not extract media URL from Higgsfield result | job_id={job_id}"
    )


async def generate_image(
    *,
    model: str,
    prompt: str,
    image_path: str,
    aspect_ratio: str = "1:1",
    timeout: int = GENERATE_TIMEOUT,
) -> HiggsfieldGenerateResult:
    args = [
        "generate",
        "create",
        model,
        "--prompt", prompt,
        "--image", image_path,
        "--aspect_ratio", aspect_ratio,
        "--wait",
        "--json",
    ]

    returncode, stdout, stderr = await _run_higgsfield(*args, timeout=timeout)

    if returncode != 0:
        raise HiggsfieldError(
            f"Higgsfield CLI exited with code {returncode} | stderr={stderr[:500]}"
        )

    if stderr and "error" in stderr.lower():
        raise HiggsfieldError(f"Higgsfield CLI reported error: {stderr[:500]}")

    return _parse_result(stdout)
