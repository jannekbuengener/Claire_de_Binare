#!/usr/bin/env python3
"""Build a replay trace from candle data for regime scorecard evaluation.

Usage:
    python tools/build_candle_trace.py \\
        --input-candles dataset.candles.json \\
        --output trace.json

Observation-only trace: per-step signal counts and trade closures are unavailable.

The run_id is auto-derived from dataset SHA256 for determinism.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


def regime_str_from_raw(raw: object) -> str | None:
    if isinstance(raw, str) and raw.strip():
        return raw.strip().upper()
    if isinstance(raw, int) and not isinstance(raw, bool):
        if raw == 0:
            return "TREND"
        if raw == 1:
            return "RANGE"
        if raw == 2:
            return "HIGH_VOL_CHAOTIC"
        if raw == 3:
            return "CRISIS"
        return "UNKNOWN"
    return None


def derive_source_sha256(input_path: Path, raw_bytes: bytes) -> str:
    for metadata_name in ("config.resolved.json", "extraction_manifest.json"):
        metadata_path = input_path.with_name(metadata_name)
        if not metadata_path.is_file():
            continue
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(metadata, dict):
            continue
        dataset_sha256 = metadata.get("dataset_sha256")
        if isinstance(dataset_sha256, str) and dataset_sha256.strip():
            return dataset_sha256.strip()

    return hashlib.sha256(raw_bytes).hexdigest()


def build_trace(
    candles: list[dict],
    run_id: str | None = None,
    source_sha256: str | None = None,
) -> dict:
    if run_id is None:
        digest = (
            source_sha256
            or hashlib.sha256(
                json.dumps(candles, sort_keys=True, ensure_ascii=False).encode("utf-8")
            ).hexdigest()
        )
        run_id = f"candle-trace-{digest[:16]}"

    steps = []
    for candle in candles:
        try:
            ts_ms = int(candle["ts_ms"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Candle missing valid ts_ms: {exc}") from exc
        steps.append(
            {
                "ts_ms": ts_ms,
                "regime_id": candle.get("regime_id"),
            }
        )

    return {
        "run_id": run_id,
        "signals_available": False,
        "steps": steps,
        "trades_available": False,
        "trades": [],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build observation-only replay trace from candle data."
    )
    parser.add_argument(
        "--input-candles",
        required=True,
        help="Path to candles JSON file (JSON array of candle objects).",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output trace JSON path.",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Optional explicit run_id (default: auto-derived from SHA256 of candle data).",
    )
    args = parser.parse_args(argv)

    input_path = Path(args.input_candles)
    try:
        raw_bytes = input_path.read_bytes()
        raw = raw_bytes.decode("utf-8")
        candles = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: Failed to read candles: {exc}", file=sys.stderr)
        return 1
    except UnicodeDecodeError as exc:
        print(f"ERROR: Failed to decode candles as UTF-8: {exc}", file=sys.stderr)
        return 1

    if not isinstance(candles, list):
        print("ERROR: candles must be a JSON array", file=sys.stderr)
        return 1

    try:
        source_sha256 = derive_source_sha256(input_path, raw_bytes)
        trace = build_trace(
            candles,
            run_id=args.run_id,
            source_sha256=source_sha256,
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    output_path = Path(args.output)
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(trace, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    except OSError as exc:
        print(f"ERROR: Failed to write trace: {exc}", file=sys.stderr)
        return 1

    print(f"OK: trace written to {output_path}")
    print(f"  run_id:       {trace['run_id']}")
    print(f"  steps:        {len(trace['steps'])}")
    print(f"  trades:       0 (observation-only)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
