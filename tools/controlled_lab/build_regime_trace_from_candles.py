"""Build a regime replay trace from candle dataset for controlled_lab_evidence.

Usage:
    python tools/controlled_lab/build_regime_trace_from_candles.py \
        --candles <path> --output <path> [--run-id <id>]

Reads a candle JSON array with fields: ts_ms, regime_id.
Produces a replay trace consumable by arvp_regime_scorecard_runner.py
--replay-trace argument, with signals_available=false, trades_available=false.

Output JSON embeds scenario_source metadata for evidence_class provenance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="build_regime_trace_from_candles",
        description="Build regime replay trace from candle dataset",
    )
    p.add_argument("--candles", required=True, help="Path to candle dataset JSON")
    p.add_argument(
        "--output",
        required=True,
        help="Output path for generated replay trace JSON",
    )
    p.add_argument(
        "--run-id",
        default="controlled-lab-001",
        help="Run ID for the trace (default: controlled-lab-001)",
    )
    return p.parse_args(argv)


def _build_replay_trace(
    candles: list[dict[str, Any]],
    run_id: str,
    source_path: str,
    dataset_sha256: str,
) -> dict[str, Any]:
    trace_start_ts = candles[0]["ts_ms"] if candles else None
    trace_end_ts = candles[-1]["ts_ms"] if candles else None
    steps: list[dict[str, Any]] = []
    regime_counter: Counter[int] = Counter()
    for c in candles:
        rid = c.get("regime_id", 0)
        regime_counter[rid] += 1
        steps.append({"ts_ms": c["ts_ms"], "regime_id": rid})

    scenario_source = {
        "source_path": source_path,
        "dataset_sha256": dataset_sha256,
        "candle_count": len(candles),
        "regime_id_distribution": dict(regime_counter),
        "trace_start_ts_ms": trace_start_ts,
        "trace_end_ts_ms": trace_end_ts,
        "generator": "build_regime_trace_from_candles.py",
    }
    trace: dict[str, Any] = {
        "run_id": run_id,
        "signals_available": False,
        "trades_available": False,
        "steps": steps,
        "trades": [],
        "scenario_source": scenario_source,
    }
    return trace


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        args = _parse_args(argv)
    except SystemExit:
        return 1

    candles_path = Path(args.candles)
    if not candles_path.is_file():
        print(f"ERROR: candles file not found: {candles_path}", file=sys.stderr)
        return 1

    try:
        raw = candles_path.read_bytes()
        dataset_sha256 = hashlib.sha256(raw).hexdigest()
        candles: list[dict[str, Any]] = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: failed to read candles: {exc}", file=sys.stderr)
        return 1

    if not isinstance(candles, list):
        print("ERROR: candles JSON must be an array", file=sys.stderr)
        return 1
    if not candles:
        print("ERROR: candles array is empty", file=sys.stderr)
        return 1

    trace = _build_replay_trace(
        candles=candles,
        run_id=args.run_id,
        source_path=str(candles_path.resolve()),
        dataset_sha256=dataset_sha256,
    )

    try:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(trace, indent=2, sort_keys=False), encoding="utf-8"
        )
    except OSError as exc:
        print(f"ERROR: failed to write output: {exc}", file=sys.stderr)
        return 1

    print(
        f"OK: trace written ({len(trace['steps'])} steps, "
        f"{len(trace['scenario_source']['regime_id_distribution'])} regimes)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
