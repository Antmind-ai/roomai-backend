from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
import json
import logging
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

DEFAULT_MODEL = "seedream_v4_5"
DEFAULT_TIMEOUT_SECONDS = 1200
DEFAULT_RETRIES = 2
DEFAULT_RETRY_BASE_DELAY_SECONDS = 2.0
REQUIRED_COLUMNS = ("asset_id", "screen_usage", "aspect_ratio", "prompt")
MODEL_ALLOWED_ASPECT_RATIOS = {
    "seedream_v4_5": {"1:1", "4:3", "16:9", "3:2", "21:9", "3:4", "9:16", "2:3"},
}
MODEL_ASPECT_RATIO_FALLBACKS = {
    "seedream_v4_5": {
        "4:5": "3:4",
    },
}

LOGGER = logging.getLogger("seedream_manifest")


@dataclass(frozen=True)
class ManifestRow:
    asset_id: str
    screen_usage: str
    aspect_ratio: str
    prompt: str
    row_number: int


@dataclass(frozen=True)
class JobOutcome:
    status: str
    output_path: Path
    result_url: str | None
    error: str | None


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _default_csv_path() -> Path:
    return _repo_root() / "image-manifest-gpt-image-2.csv"


def _default_output_dir() -> Path:
    return _repo_root() / "generated-assets" / "seedream-v4_5"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Batch-generate images with Higgsfield Seedream from a CSV manifest and "
            "save files to per-aspect-ratio folders."
        )
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=_default_csv_path(),
        help="Path to CSV manifest with asset_id, screen_usage, aspect_ratio, prompt columns.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=_default_output_dir(),
        help="Directory where generated files and run manifest are written.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help="Higgsfield model ID to use for generation.",
    )
    parser.add_argument(
        "--higgsfield-bin",
        default="higgsfield",
        help="Higgsfield CLI binary name or absolute path.",
    )
    parser.add_argument(
        "--manifest-path",
        type=Path,
        default=None,
        help="Optional JSONL path for run records. Defaults to <output-dir>/run-manifest.jsonl.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit of rows to process from the manifest.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip rows whose target output files already exist.",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=DEFAULT_RETRIES,
        help="Retry count for each row after the initial attempt.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="Timeout for each Higgsfield CLI generate call.",
    )
    parser.add_argument(
        "--retry-base-delay-seconds",
        type=float,
        default=DEFAULT_RETRY_BASE_DELAY_SECONDS,
        help="Initial delay before retries. Delay doubles on each retry.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        help="Logging level.",
    )

    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be at least 1")
    if args.retries < 0:
        parser.error("--retries must be zero or greater")
    if args.timeout_seconds < 1:
        parser.error("--timeout-seconds must be at least 1")
    if args.retry_base_delay_seconds <= 0:
        parser.error("--retry-base-delay-seconds must be greater than 0")

    return args


def _configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def _run_command(
    *,
    args: list[str],
    timeout_seconds: int,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )


def _preflight(higgsfield_bin: str) -> None:
    if shutil.which(higgsfield_bin) is None:
        raise RuntimeError(
            f"Higgsfield CLI not found: {higgsfield_bin}. Install it and ensure it is on PATH."
        )

    account_status = _run_command(
        args=[higgsfield_bin, "account", "status"],
        timeout_seconds=30,
    )
    if account_status.returncode != 0:
        message = account_status.stderr.strip() or account_status.stdout.strip()
        raise RuntimeError(
            "Higgsfield auth session is not ready. Run 'higgsfield auth login' first. "
            f"Details: {message[:300]}"
        )


def _read_rows(csv_path: Path, limit: int | None) -> list[ManifestRow]:
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV manifest not found: {csv_path}")

    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"CSV manifest has no header row: {csv_path}")

        missing_columns = [col for col in REQUIRED_COLUMNS if col not in reader.fieldnames]
        if missing_columns:
            raise ValueError(
                "CSV manifest is missing required columns: " + ", ".join(missing_columns)
            )

        rows: list[ManifestRow] = []
        for row_number, row in enumerate(reader, start=2):
            asset_id = (row.get("asset_id") or "").strip()
            screen_usage = (row.get("screen_usage") or "").strip()
            aspect_ratio = (row.get("aspect_ratio") or "").strip()
            prompt = (row.get("prompt") or "").strip()

            if not asset_id:
                raise ValueError(f"Row {row_number}: asset_id is empty")
            if "/" in asset_id or "\\" in asset_id or ".." in asset_id:
                raise ValueError(
                    f"Row {row_number}: asset_id contains invalid path characters: {asset_id}"
                )
            if not aspect_ratio or ":" not in aspect_ratio:
                raise ValueError(f"Row {row_number}: invalid aspect_ratio: {aspect_ratio}")
            if not prompt:
                raise ValueError(f"Row {row_number}: prompt is empty")

            rows.append(
                ManifestRow(
                    asset_id=asset_id,
                    screen_usage=screen_usage,
                    aspect_ratio=aspect_ratio,
                    prompt=prompt,
                    row_number=row_number,
                )
            )

    if limit is not None:
        rows = rows[:limit]

    if not rows:
        raise ValueError("No rows found in manifest after applying filters")

    return rows


def _aspect_ratio_folder_name(aspect_ratio: str) -> str:
    return aspect_ratio.replace(":", "x").replace("/", "x").replace(" ", "")


def _generation_aspect_ratio(*, model: str, requested_aspect_ratio: str) -> str:
    allowed_ratios = MODEL_ALLOWED_ASPECT_RATIOS.get(model)
    if allowed_ratios is None or requested_aspect_ratio in allowed_ratios:
        return requested_aspect_ratio

    fallback_ratio = MODEL_ASPECT_RATIO_FALLBACKS.get(model, {}).get(requested_aspect_ratio)
    if fallback_ratio and fallback_ratio in allowed_ratios:
        return fallback_ratio

    allowed = ", ".join(sorted(allowed_ratios))
    raise ValueError(
        f"Model {model} does not support aspect_ratio={requested_aspect_ratio}. "
        f"Allowed values: {allowed}"
    )


def _extract_url_from_job(job: dict[str, Any]) -> str | None:
    result_url = job.get("result_url")
    if isinstance(result_url, str) and result_url:
        return result_url

    result = job.get("result")
    if isinstance(result, dict):
        url = result.get("url")
        if isinstance(url, str) and url:
            return url
        media = result.get("media")
        if isinstance(media, list) and media and isinstance(media[0], dict):
            media_url = media[0].get("url")
            if isinstance(media_url, str) and media_url:
                return media_url
        if isinstance(media, dict):
            media_url = media.get("url")
            if isinstance(media_url, str) and media_url:
                return media_url

    for key in ("media", "medias"):
        value = job.get(key)
        if isinstance(value, list) and value and isinstance(value[0], dict):
            media_url = value[0].get("url")
            if isinstance(media_url, str) and media_url:
                return media_url
        if isinstance(value, dict):
            media_url = value.get("url")
            if isinstance(media_url, str) and media_url:
                return media_url

    return None


def _parse_result_url(stdout: str) -> str:
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Unable to parse Higgsfield JSON output: {stdout[:300]}") from exc

    if isinstance(payload, dict):
        url = _extract_url_from_job(payload)
        if url:
            return url
        raise RuntimeError("No result URL found in Higgsfield response object")

    if isinstance(payload, list):
        if not payload:
            raise RuntimeError("Higgsfield returned an empty result list")
        for item in reversed(payload):
            if isinstance(item, dict):
                url = _extract_url_from_job(item)
                if url:
                    return url
        raise RuntimeError("No result URL found in Higgsfield response list")

    raise RuntimeError(f"Unexpected Higgsfield response type: {type(payload).__name__}")


def _generate_once(
    *,
    higgsfield_bin: str,
    model: str,
    prompt: str,
    aspect_ratio: str,
    timeout_seconds: int,
) -> str:
    command = [
        higgsfield_bin,
        "generate",
        "create",
        model,
        "--prompt",
        prompt,
        "--aspect_ratio",
        aspect_ratio,
        "--wait",
        "--json",
    ]

    completed = _run_command(args=command, timeout_seconds=timeout_seconds)
    if completed.returncode != 0:
        details = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(
            f"Higgsfield CLI failed with code {completed.returncode}: {details[:500]}"
        )

    return _parse_result_url(completed.stdout)


def _download_to_path(url: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = output_path.with_suffix(output_path.suffix + ".tmp")

    parsed_url = urlparse(url)
    if parsed_url.scheme not in {"http", "https"}:
        raise RuntimeError(f"Unsupported result URL scheme: {parsed_url.scheme or '<empty>'}")

    request = Request(url, headers={"User-Agent": "seedream-manifest-generator/1.0"})  # noqa: S310
    try:
        with urlopen(request, timeout=120) as response:  # noqa: S310
            payload = response.read()
    except URLError as exc:
        raise RuntimeError(f"Failed downloading result URL: {url}") from exc

    if not payload:
        raise RuntimeError(f"Downloaded empty payload from result URL: {url}")

    with temp_path.open("wb") as handle:
        handle.write(payload)
    temp_path.replace(output_path)


def _attempt_job(
    *,
    row: ManifestRow,
    output_path: Path,
    generation_aspect_ratio: str,
    higgsfield_bin: str,
    model: str,
    timeout_seconds: int,
    retries: int,
    retry_base_delay_seconds: float,
    resume: bool,
) -> JobOutcome:
    if resume and output_path.exists():
        return JobOutcome(
            status="skipped",
            output_path=output_path,
            result_url=None,
            error=None,
        )

    attempts = retries + 1
    for attempt in range(1, attempts + 1):
        try:
            result_url = _generate_once(
                higgsfield_bin=higgsfield_bin,
                model=model,
                prompt=row.prompt,
                aspect_ratio=generation_aspect_ratio,
                timeout_seconds=timeout_seconds,
            )
            _download_to_path(result_url, output_path)
            return JobOutcome(
                status="success",
                output_path=output_path,
                result_url=result_url,
                error=None,
            )
        except Exception as exc:
            if attempt >= attempts:
                return JobOutcome(
                    status="failed",
                    output_path=output_path,
                    result_url=None,
                    error=str(exc),
                )

            delay = retry_base_delay_seconds * (2 ** (attempt - 1))
            LOGGER.warning(
                "Row %s (%s) attempt %s/%s failed. Retrying in %.1fs. Error: %s",
                row.row_number,
                row.asset_id,
                attempt,
                attempts,
                delay,
                str(exc)[:300],
            )
            time.sleep(delay)

    return JobOutcome(
        status="failed",
        output_path=output_path,
        result_url=None,
        error="Unexpected retry loop exit",
    )


def _relative_output(output_dir: Path, output_path: Path) -> str:
    try:
        return str(output_path.relative_to(output_dir))
    except ValueError:
        return str(output_path)


def _run(args: argparse.Namespace) -> int:
    _preflight(args.higgsfield_bin)

    rows = _read_rows(args.csv, args.limit)
    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = args.manifest_path or (output_dir / "run-manifest.jsonl")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    success_count = 0
    failed_count = 0
    skipped_count = 0
    per_ratio_counts: dict[str, int] = {}
    failed_asset_ids: list[str] = []

    LOGGER.info(
        "Starting generation | rows=%s model=%s output_dir=%s manifest=%s",
        len(rows),
        args.model,
        output_dir,
        manifest_path,
    )

    with manifest_path.open("w", encoding="utf-8") as manifest_handle:
        for index, row in enumerate(rows, start=1):
            ratio_folder = _aspect_ratio_folder_name(row.aspect_ratio)
            output_path = output_dir / ratio_folder / f"{row.asset_id}.png"
            generation_aspect_ratio = _generation_aspect_ratio(
                model=args.model,
                requested_aspect_ratio=row.aspect_ratio,
            )

            if generation_aspect_ratio == row.aspect_ratio:
                LOGGER.info(
                    "Processing %s/%s | asset_id=%s ratio=%s",
                    index,
                    len(rows),
                    row.asset_id,
                    row.aspect_ratio,
                )
            else:
                LOGGER.info(
                    "Processing %s/%s | asset_id=%s ratio=%s generation_ratio=%s",
                    index,
                    len(rows),
                    row.asset_id,
                    row.aspect_ratio,
                    generation_aspect_ratio,
                )

            outcome = _attempt_job(
                row=row,
                output_path=output_path,
                generation_aspect_ratio=generation_aspect_ratio,
                higgsfield_bin=args.higgsfield_bin,
                model=args.model,
                timeout_seconds=args.timeout_seconds,
                retries=args.retries,
                retry_base_delay_seconds=args.retry_base_delay_seconds,
                resume=args.resume,
            )

            if outcome.status == "success":
                success_count += 1
            elif outcome.status == "skipped":
                skipped_count += 1
            else:
                failed_count += 1
                failed_asset_ids.append(row.asset_id)

            per_ratio_counts[row.aspect_ratio] = per_ratio_counts.get(row.aspect_ratio, 0) + 1

            record = {
                "asset_id": row.asset_id,
                "screen_usage": row.screen_usage,
                "aspect_ratio": row.aspect_ratio,
                "generation_aspect_ratio": generation_aspect_ratio,
                "prompt": row.prompt,
                "out": _relative_output(output_dir, outcome.output_path),
                "status": outcome.status,
                "result_url": outcome.result_url,
                "error": outcome.error,
            }
            manifest_handle.write(json.dumps(record, ensure_ascii=True) + "\n")
            manifest_handle.flush()

    LOGGER.info(
        "Completed | success=%s skipped=%s failed=%s manifest=%s",
        success_count,
        skipped_count,
        failed_count,
        manifest_path,
    )

    ratio_summary = ", ".join(
        f"{ratio}: {count}" for ratio, count in sorted(per_ratio_counts.items())
    )
    LOGGER.info("Processed per ratio | %s", ratio_summary)

    if failed_asset_ids:
        LOGGER.error("Failed asset_ids | %s", ", ".join(failed_asset_ids))
        return 1
    return 0


def main() -> int:
    args = _parse_args()
    _configure_logging(args.log_level)
    try:
        return _run(args)
    except KeyboardInterrupt:
        LOGGER.error("Interrupted by user")
        return 130
    except Exception as exc:
        LOGGER.error("Batch generation failed: %s", str(exc))
        return 2


if __name__ == "__main__":
    sys.exit(main())
