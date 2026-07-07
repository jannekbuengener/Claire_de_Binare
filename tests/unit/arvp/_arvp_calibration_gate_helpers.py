"""Shared helpers for ARVP calibration gate regression contract tests (#3822)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from core.replay.arvp_gate import (
    ARVPEvidenceBundle,
    ARVPGateVerdict,
    build_arvp_gate_verdict,
)
from core.replay.replay_vs_paper_compare import ComparePaths, compare_from_paths
from core.replay.run_registry import ReplayRunRecord
from core.replay.shadow_compare import ShadowComparisonResult
from core.replay.simulator_calibration_report import (
    SimulatorCalibrationReport,
    build_simulator_calibration_report,
)

_FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "arvp" / "calibration"


@dataclass(frozen=True)
class CalibrationPipelineResult:
    comparison: ShadowComparisonResult
    calibration: SimulatorCalibrationReport
    gate: ARVPGateVerdict


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def replay_report(
    *,
    symbol: str = "BTCUSDT",
    strategy_id: str = "primary_breakout_v1",
    signals: int = 3,
    fills: int = 2,
    orders: int = 2,
) -> dict[str, Any]:
    return {
        "schema_version": "replay_report.v1",
        "report_type": "shadow_replay",
        "strategy_id": strategy_id,
        "run_spec": {
            "replay_run_id": "replay-aabbccddee11-0001",
            "strategy_id": strategy_id,
            "symbol": symbol,
            "start_ts_ms": 1704067200000,
            "end_ts_ms": 1704153600000,
            "code_commit": "a" * 7,
            "run_mode": "shadow",
            "metadata": {"dataset_fingerprint": "b" * 64},
        },
        "execution_result": {
            "run_id": "replay-aabbccddee11-0001",
            "events_processed": 10,
            "decisions_made": 0,
            "orders_placed": orders,
            "fills_recorded": fills,
            "envelope_hashes": [],
        },
        "replay_integrity": {
            "run_id": "replay-aabbccddee11-0001",
            "envelope_count": 0,
            "envelope_chain_hash": "c" * 64,
            "event_loop_states_hash": "c" * 64,
            "integrity_ok": True,
        },
        "envelope_summary": {
            "decision_envelopes_total": 0,
            "order_envelopes_total": orders,
            "fill_envelopes_total": fills,
        },
        "artifact_manifest": {
            "envelope_log_uri": "none",
            "event_loop_states_uri": "none",
            "report_artifact_uri": "report.json",
        },
        "dataset_summary": {
            "period_start_ts_ms": 1704067200000,
            "period_end_ts_ms": 1704153600000,
        },
        "metrics": {
            "signals_total": signals,
            "buy_signals_total": max(1, signals - 1),
            "sell_signals_total": 1,
            "closed_trades_total": fills,
        },
    }


def paper_reference_window(
    *,
    symbol: str = "BTCUSDT",
    strategy_id: str = "primary_breakout_v1",
    signal_count: int = 1,
    order_count: int = 1,
    fill_count: int = 1,
) -> dict[str, Any]:
    start = 1704067200000
    end = 1704153600000
    events: list[dict[str, Any]] = []
    for i in range(signal_count):
        events.append(
            {
                "event_pk": f"s{i}",
                "correlation_id": f"c{i}",
                "event_type": "SIGNAL",
                "symbol": symbol,
                "timestamp_ms": start + i * 60_000,
                "payload": {"strategy_id": strategy_id},
                "signal_id": f"sig-{i}",
            }
        )
    for i in range(order_count):
        events.append(
            {
                "event_pk": f"o{i}",
                "correlation_id": f"c{i}",
                "event_type": "ORDER",
                "symbol": symbol,
                "timestamp_ms": start + 120_000 + i * 60_000,
                "payload": {"strategy_id": strategy_id},
                "order_id": f"paper_{i:03d}",
                "signal_id": f"sig-{i}",
                "decision_id": f"dec-{i}",
            }
        )
    for i in range(fill_count):
        events.append(
            {
                "event_pk": f"f{i}",
                "correlation_id": f"c{i}",
                "event_type": "FILL",
                "symbol": symbol,
                "timestamp_ms": start + 180_000 + i * 60_000,
                "payload": {"strategy_id": strategy_id},
                "order_id": f"paper_{i:03d}",
                "fill_id": f"fill-{i}",
                "signal_id": f"sig-{i}",
                "decision_id": f"dec-{i}",
            }
        )
    return {
        "contract_version": "arvp_paper_reference_window.v1",
        "strategy_id": strategy_id,
        "symbol": symbol,
        "start_ts_ms_utc": start,
        "end_ts_ms_utc": end,
        "source_table": "public.correlation_ledger",
        "source_query_intent": "arvp-p0-contract",
        "extracted_at_utc": "2026-04-24T00:00:00+00:00",
        "extracted_by": "unit-test",
        "events": events,
    }


def run_calibration_pipeline(
    tmp_path: Path,
    *,
    replay: dict[str, Any],
    paper: dict[str, Any],
    record_overrides: dict[str, Any] | None = None,
    shadow: ShadowComparisonResult | None = None,
) -> CalibrationPipelineResult:
    replay_path = tmp_path / "report.json"
    paper_path = tmp_path / "paper_reference_window.json"
    _write_json(replay_path, replay)
    _write_json(paper_path, paper)

    comparison = compare_from_paths(
        ComparePaths(replay_report_json=replay_path, paper_reference_json=paper_path)
    )
    calibration = build_simulator_calibration_report(comparison)

    record_defaults: dict[str, Any] = {
        "run_id": "replay-aabbccddee11-0001",
        "status": "completed",
        "mode": "baseline",
        "strategy_id": replay.get("strategy_id", "primary_breakout_v1"),
        "symbol": replay["run_spec"]["symbol"],
        "dataset_fingerprint": "a" * 64,
        "scheduler_profile": "2x",
        "execution_provenance_id": "bt-0123456789abcdef",
        "artifact_root": "artifacts/replay_reports/replay-aabbccddee11-0001",
        "deterministic_replay_ok": True,
        "failure_reason": None,
        "started_at_utc": "2026-04-22T14:00:00+00:00",
        "finished_at_utc": "2026-04-22T14:00:05+00:00",
    }
    if record_overrides:
        record_defaults.update(record_overrides)
    record = ReplayRunRecord(**record_defaults)

    gate_shadow = shadow if shadow is not None else comparison
    bundle = ARVPEvidenceBundle(record=record, shadow=gate_shadow)
    gate = build_arvp_gate_verdict(bundle)
    return CalibrationPipelineResult(
        comparison=comparison, calibration=calibration, gate=gate
    )


def comparison_for_calibration(
    *,
    status: str = "aligned",
    fill_rate_delta: Decimal | None = Decimal("0.10"),
    fill_count_delta: int = 0,
    inferred_unfilled_count_delta: int = 0,
    alignment_issue: str | None = None,
) -> ShadowComparisonResult:
    return ShadowComparisonResult(
        comparison_fingerprint="f" * 64,
        status=status,
        alignment_issue=alignment_issue,
        replay_run_id="replay-aabbccddee11-0001",
        paper_provenance_id="paper-run-001",
        symbol="BTCUSDT",
        strategy_id="primary_breakout_v1",
        signal_count_delta=0,
        order_count_delta=0,
        fill_count_delta=fill_count_delta,
        inferred_unfilled_count_delta=inferred_unfilled_count_delta,
        actual_reject_count_delta=None,
        fill_rate_replay=None,
        fill_rate_paper=None,
        fill_rate_delta=fill_rate_delta,
        window_start_utc_replay="2024-01-01T00:00:00+00:00",
        window_end_utc_replay="2024-01-02T00:00:00+00:00",
        window_start_utc_paper="2024-01-01T00:00:00+00:00",
        window_end_utc_paper="2024-01-02T00:00:00+00:00",
    )


def write_fixture_bundle(name: str, replay: dict[str, Any], paper: dict[str, Any]) -> None:
    target = _FIXTURE_DIR / name
    target.mkdir(parents=True, exist_ok=True)
    _write_json(target / "replay_report.json", replay)
    _write_json(target / "paper_reference_window.json", paper)
