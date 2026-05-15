# Seedream Manifest Batch Generation

This document covers how to run the CSV-based image generation script:

- Script: `generate_seedream_manifest.py`
- Default model: `seedream_v4_5`
- Behavior: one image per CSV row, using each row's own `aspect_ratio`

## Prerequisites

- Higgsfield CLI installed and available on PATH.
- Active Higgsfield session:

```bash
higgsfield auth login
```

## Quick Start

Run from the `backend/` directory:

```bash
python3 generate_seedream_manifest.py \
  --csv ../image-manifest-gpt-image-2.csv \
  --output-dir ../generated-assets/seedream-v4_5 \
  --model seedream_v4_5 \
  --resume
```

## What The Script Produces

- Generates one output image for each input row.
- Writes files into per-ratio folders under the output root.
- Uses `<asset_id>.png` as filename.
- Writes a run log to JSONL with generation status.

Example output layout:

```text
generated-assets/seedream-v4_5/
  4x5/
    home-interior-hero.png
  1x1/
    style-modern.png
  3x4/
    discover-living-room.png
  run-manifest.jsonl
```

## Useful Flags

- `--limit 3` processes only the first three CSV rows.
- `--resume` skips files that already exist at the target path.
- `--retries 3` sets retry count after the first failed attempt.
- `--timeout-seconds 1800` increases CLI wait timeout.
- `--manifest-path /custom/path/run-manifest.jsonl` overrides default run log path.
- `--higgsfield-bin /absolute/path/to/higgsfield` uses a custom CLI binary path.

## Run Log Fields

Each JSONL line includes:

- `asset_id`
- `screen_usage`
- `aspect_ratio`
- `prompt`
- `out`
- `status` (`success`, `failed`, or `skipped`)
- `result_url`
- `error`

## Exit Codes

- `0`: all rows succeeded or were skipped.
- `1`: one or more rows failed.
- `2`: script-level failure before completion.
- `130`: interrupted by user.

## Smoke Test

Start with one row before running the full manifest:

```bash
python3 generate_seedream_manifest.py \
  --csv ../image-manifest-gpt-image-2.csv \
  --output-dir ../generated-assets/seedream-v4_5 \
  --limit 1
```
