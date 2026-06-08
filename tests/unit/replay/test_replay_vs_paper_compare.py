"""Unit tests for core/replay/replay_vs_paper_compare.py (#1902)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.replay.replay_vs_paper_compare import (
    ComparePaths,
    ReplayVsPaperCompareError,
    compare_from_paths,
    load_paper_reference_window,
    load_replay_output_window,
    write_comparison_bundle,
)


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _replay_report(
    *, symbol: str = "BTCUSDT", strategy_id: str = "primary_breakout_v1"
) -> dict:
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
            "orders_placed": 0,
            "fills_recorded": 0,
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
            "order_envelopes_total": 0,
            "fill_envelopes_total": 0,
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
            "signals_total": 3,
            "buy_signals_total": 2,
            "sell_signals_total": 1,
            "closed_trades_total": 2,
        },
    }


def _paper_reference_window(
    *, symbol: str = "BTCUSDT", strategy_id: str = "primary_breakout_v1"
) -> dict:
    start = 1704067200000
    end = 1704153600000
    return {
        "contract_version": "arvp_paper_reference_window.v1",
        "strategy_id": strategy_id,
        "symbol": symbol,
        "start_ts_ms_utc": start,
        "end_ts_ms_utc": end,
        "source_table": "public.correlation_ledger",
        "source_query_intent": "test",
        "extracted_at_utc": "2026-04-24T00:00:00+00:00",
        "extracted_by": "unit-test",
        "events": [
            {
                "event_pk": "1",
                "correlation_id": "c1",
                "event_type": "SIGNAL",
                "symbol": symbol,
                "timestamp_ms": start,
                "payload": {"strategy_id": strategy_id},
                "signal_id": "s1",
            },
            {
                "event_pk": "2",
                "correlation_id": "c1",
                "event_type": "ORDER",
                "symbol": symbol,
                "timestamp_ms": start + 60_000,
                "payload": {"strategy_id": strategy_id},
                "order_id": "paper_001",
                "signal_id": "s1",
                "decision_id": "d1",
            },
            {
                "event_pk": "3",
                "correlation_id": "c1",
                "event_type": "FILL",
                "symbol": symbol,
                "timestamp_ms": start + 120_000,
                "payload": {"strategy_id": strategy_id},
                "order_id": "paper_001",
                "fill_id": "f1",
                "signal_id": "s1",
                "decision_id": "d1",
            },
        ],
    }


def test_load_replay_output_window_derives_rejects() -> None:
    replay = load_replay_output_window(_replay_report())
    assert replay.signal_count == 3
    assert replay.order_count == 3
    assert replay.fill_count == 2
    assert replay.actual_reject_count is None
    assert replay.inferred_unfilled_count == 1  # orders - fills (proxy only)


def test_load_paper_reference_window_derives_counts() -> None:
    paper = load_paper_reference_window(_paper_reference_window())
    assert paper.signal_count == 1
    assert paper.order_count == 1
    assert paper.fill_count == 1
    assert paper.actual_reject_count is None
    assert paper.inferred_unfilled_count == 0


def test_compare_from_paths_aligned_writes_bundle(tmp_path: Path) -> None:
    replay_path = tmp_path / "report.json"
    paper_path = tmp_path / "paper.json"
    _write_json(replay_path, _replay_report())
    _write_json(paper_path, _paper_reference_window())

    result = compare_from_paths(
        ComparePaths(replay_report_json=replay_path, paper_reference_json=paper_path)
    )
    assert result.status == "aligned"

    out_dir = tmp_path / "out"
    json_path, md_path = write_comparison_bundle(result=result, output_dir=out_dir)
    assert json_path.exists()
    assert md_path.exists()


def test_compare_from_paths_symbol_mismatch_is_unusable(tmp_path: Path) -> None:
    replay_path = tmp_path / "report.json"
    paper_path = tmp_path / "paper.json"
    _write_json(replay_path, _replay_report(symbol="BTCUSDT"))
    _write_json(paper_path, _paper_reference_window(symbol="ETHUSDT"))

    result = compare_from_paths(
        ComparePaths(replay_report_json=replay_path, paper_reference_json=paper_path)
    )
    assert result.status == "unusable"
    assert result.alignment_issue is not None
    assert "symbol mismatch" in result.alignment_issue


def test_paper_reference_unknown_event_type_raises() -> None:
    payload = _paper_reference_window()
    payload["events"][0]["event_type"] = "UNKNOWN"
    with pytest.raises(ReplayVsPaperCompareError, match="Unknown event_type"):
        load_paper_reference_window(payload)


def test_load_paper_reference_window_with_causal_context_events() -> None:
    """causal_context_events are counted as causal_signal_count."""
    payload = _paper_reference_window()
    payload["causal_context_events"] = [
        {
            "event_pk": "causal-sig-1",
            "correlation_id": "c1",
            "event_type": "SIGNAL",
            "symbol": "BTCUSDT",
            "timestamp_ms": payload["start_ts_ms_utc"] - 60_000,
            "payload": {"strategy_id": "primary_breakout_v1"},
            "signal_id": "s1",
            "in_window": False,
            "context_scope": "pre_window_causal",
        },
    ]
    paper = load_paper_reference_window(payload)
    assert paper.causal_signal_count == 1
    assert paper.signal_count == 1  # in-window unchanged


def test_load_paper_reference_window_no_causal_context_events() -> None:
    """Missing causal_context_events is a no-op (causal_signal_count=0)."""
    payload = _paper_reference_window()
    # Ensure key is absent, not just empty
    assert "causal_context_events" not in payload
    paper = load_paper_reference_window(payload)
    assert paper.causal_signal_count == 0
    assert paper.signal_count == 1


def test_causal_context_event_non_signal_type_raises() -> None:
    """causal_context_events must be SIGNAL type."""
    payload = _paper_reference_window()
    payload["causal_context_events"] = [
        {
            "event_pk": "bad-type",
            "correlation_id": "c1",
            "event_type": "ORDER",
            "symbol": "BTCUSDT",
            "timestamp_ms": payload["start_ts_ms_utc"] - 60_000,
            "payload": {"strategy_id": "primary_breakout_v1"},
            "signal_id": "s1",
        },
    ]
    with pytest.raises(ReplayVsPaperCompareError, match="event_type must be SIGNAL"):
        load_paper_reference_window(payload)
