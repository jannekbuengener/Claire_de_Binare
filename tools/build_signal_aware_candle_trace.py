#!/usr/bin/env python3
"""Build a signal-aware replay trace from candle data and a gate trace JSONL.

Usage:
    python tools/build_signal_aware_candle_trace.py \
        --input-candles dataset.candles.json \
        --gate-trace-path gate_trace.jsonl \
        --baseline-metrics metrics.json \
        --output trace.json \
        --run-id run_002

Produces a trace that carries:
  - per-step entry_ready-based BUY signal attribution where available
  - explicit `signals_available` / `trades_available` flags
  - explicit attribution_contract artifact alongside the trace

Partial evidence only. SELL and trade-closure attribution remain unavailable.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

_SCHEMA_VERSION = "signal_aware_trace.v1"


def _regime_str_from_raw(raw: object) -> str | None:
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


def _load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Failed to read {path}: {exc}") from exc


def _load_jsonl(path: Path) -> list[dict]:
    entries: list[dict] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            entries.append(json.loads(stripped))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Failed to read gate trace {path}: {exc}") from exc
    return entries


def build_signal_aware_trace(
    candles: list[dict],
    gate_trace: list[dict],
    baseline_metrics: dict | None = None,
    run_id: str | None = None,
) -> dict:
    if run_id is None:
        run_id = "run_002"

    gt_by_ts: dict[int, dict] = {}
    for gt_row in gate_trace:
        ts_ms = _require_int(gt_row.get("ts_ms"), "gate_trace.ts_ms")
        if ts_ms in gt_by_ts:
            raise ValueError(f"Duplicate ts_ms in gate trace: {ts_ms}")
        gt_by_ts[ts_ms] = gt_row

    buy_entry_count: int = 0
    buy_entry_ts_set: set[int] = set()
    sell_inferred_count: int = 0
    missing_gt_steps: int = 0
    warmup_or_early: int = 0

    steps: list[dict] = []
    for idx, candle in enumerate(candles):
        try:
            ts_ms = int(candle["ts_ms"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Candle[{idx}] missing valid ts_ms: {exc}") from exc

        regime_id = candle.get("regime_id")
        gt_row = gt_by_ts.get(ts_ms)

        if gt_row is None:
            buy_signal_attributable = False
            signals_emitted = 0
            entry_ready = None
            missing_gt_steps += 1
            if ts_ms < min(gt_by_ts.keys(), default=0):
                warmup_or_early += 1
        else:
            entry_ready = bool(gt_row.get("entry_ready", False))
            if entry_ready:
                buy_entry_count += 1
                buy_entry_ts_set.add(ts_ms)
                signals_emitted = 1
                buy_signal_attributable = True
            else:
                signals_emitted = 0
                buy_signal_attributable = False

        step_entry: dict = {
            "ts_ms": ts_ms,
            "regime_id": regime_id,
            "buy_signal_attributable": buy_signal_attributable,
        }
        if gt_row is not None:
            step_entry["entry_ready"] = entry_ready
            step_entry["signals_emitted"] = signals_emitted
            step_entry["gate_trace_status"] = gt_row.get("status")
        else:
            step_entry["signals_emitted"] = 0
            step_entry["gate_trace_available"] = False

        steps.append(step_entry)

    buy_ok = True
    buy_reconciliation_note: str | None = None
    if baseline_metrics is not None:
        expected_buy = int(baseline_metrics.get("buy_signals_total", 22))
        if buy_entry_count != expected_buy:
            buy_ok = False
            buy_reconciliation_note = (
                f"buy_entry_count={buy_entry_count} does not reconcile "
                f"with baseline buy_signals_total={expected_buy}"
            )

    signals_available = buy_ok and buy_entry_count > 0
    if not baseline_metrics:
        signals_available = buy_entry_count > 0

    attribution_contract = {
        "schema_version": _SCHEMA_VERSION,
        "run_id": run_id,
        "signal_attribution_availability": "partial",
        "buy_entry_attribution_available": signals_available,
        "buy_entry_count": buy_entry_count,
        "sell_signal_attribution_available": False,
        "trade_closure_attribution_available": False,
        "attribution_scope": "entry_gate_buy_only",
        "source_trace_kind": "gate_trace_jsonl",
        "natural_paper_evidence": False,
        "baseline_reconciled": buy_ok,
        "baseline_buy_signals_total": (
            int(baseline_metrics["buy_signals_total"])
            if baseline_metrics and "buy_signals_total" in baseline_metrics
            else None
        ),
        "sell_inferred_count": sell_inferred_count if not buy_ok else None,
        "missing_gate_trace_steps": missing_gt_steps,
        "warmup_or_before_gate_region_steps": warmup_or_early,
        "candle_count": len(candles),
        "gate_trace_row_count": len(gate_trace),
    }
    if buy_reconciliation_note is not None:
        attribution_contract["reconciliation_note"] = buy_reconciliation_note

    notes: list[str] = []
    if not signals_available:
        notes.append(
            "blocked_input_shape: BUY entry count does not reconcile "
            "with baseline buy_signals_total"
        )
    notes.append(
        "partial_attribution: SELL signal attribution unavailable; "
        "SELL signals are not emitted in the gate trace"
    )
    notes.append(
        "unavailable_trade_closures: per-trade entry_regime_id "
        "and exit_regime_id are unavailable"
    )

    return {
        "run_id": run_id,
        "signals_available": signals_available,
        "trades_available": False,
        "steps": steps,
        "trades": [],
        "attribution_contract": attribution_contract,
        "notes": notes,
    }


def _require_int(value: object, name: str) -> int:
    if value is None:
        raise ValueError(f"{name} is required")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be an int: {exc}") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build signal-aware replay trace from candles + gate trace."
    )
    parser.add_argument(
        "--input-candles",
        required=True,
        help="Path to candles JSON file.",
    )
    parser.add_argument(
        "--gate-trace-path",
        required=True,
        help="Path to gate trace JSONL file.",
    )
    parser.add_argument(
        "--baseline-metrics",
        default=None,
        help="Path to baseline metrics JSON for BUY count reconciliation.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output trace JSON path.",
    )
    parser.add_argument(
        "--run-id",
        default="run_002",
        help="Logical run id (default: run_002).",
    )
    parser.add_argument(
        "--attribution-contract-output",
        default=None,
        help="Explicit output path for attribution_contract.json (default: sibling to --output).",
    )
    args = parser.parse_args(argv)

    input_path = Path(args.input_candles)
    gate_trace_path = Path(args.gate_trace_path)
    output_path = Path(args.output)

    try:
        candles_raw = _load_json(input_path)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if not isinstance(candles_raw, list):
        print("ERROR: candles must be a JSON array", file=sys.stderr)
        return 1

    candles: list[dict] = candles_raw

    try:
        gate_trace = _load_jsonl(gate_trace_path)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if not gate_trace:
        print("ERROR: gate trace is empty", file=sys.stderr)
        return 2

    baseline_metrics = None
    if args.baseline_metrics:
        metrics_path = Path(args.baseline_metrics)
        try:
            baseline_metrics = _load_json(metrics_path)
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1

    try:
        trace = build_signal_aware_trace(
            candles,
            gate_trace,
            baseline_metrics=baseline_metrics,
            run_id=args.run_id,
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    attribution_contract = trace.pop("attribution_contract", None)
    notes = trace.pop("notes", [])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_payload = {"notes": notes, **trace}
    try:
        output_path.write_text(
            json.dumps(output_payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError as exc:
        print(f"ERROR: Failed to write trace: {exc}", file=sys.stderr)
        return 1

    if attribution_contract:
        contract_path = Path(
            args.attribution_contract_output
            or output_path.with_name("attribution_contract.json")
        )
        contract_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            contract_path.write_text(
                json.dumps(attribution_contract, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError as exc:
            print(
                f"ERROR: Failed to write attribution contract: {exc}", file=sys.stderr
            )
            return 1

    print(f"OK: trace written to {output_path}")
    print(f"  run_id:           {output_payload['run_id']}")
    print(f"  steps:            {len(output_payload['steps'])}")
    print(f"  signals_available: {output_payload['signals_available']}")
    print(f"  trades_available:  {output_payload['trades_available']}")
    if attribution_contract:
        print(f"  buy_entry_count:   {attribution_contract['buy_entry_count']}")
        print(f"  baseline_ok:       {attribution_contract['baseline_reconciled']}")
        ac_path = args.attribution_contract_output or output_path.with_name(
            "attribution_contract.json"
        )
        print(f"  contract:          {ac_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
