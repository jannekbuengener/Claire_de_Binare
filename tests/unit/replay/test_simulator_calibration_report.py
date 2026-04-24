"""Unit tests for core/replay/simulator_calibration_report.py (#1903)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from core.replay.shadow_compare import ShadowComparisonResult
from core.replay.simulator_calibration_report import (
    SimulatorCalibrationError,
    build_simulator_calibration_report,
    load_shadow_comparison_artifact,
)


def _comparison(
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


def test_build_report_optimistic_when_fill_rate_delta_positive() -> None:
    report = build_simulator_calibration_report(_comparison(fill_rate_delta=Decimal("0.01")))
    assert report.status == "aligned"
    assert report.drift_classification == "optimistic"
    assert any(s.name == "fill_rate_delta" and s.evidence_level == "explicit" for s in report.signals)


def test_build_report_pessimistic_when_fill_rate_delta_negative() -> None:
    report = build_simulator_calibration_report(_comparison(fill_rate_delta=Decimal("-0.02")))
    assert report.status == "aligned"
    assert report.drift_classification == "pessimistic"


def test_build_report_ambiguous_when_proxy_signals_conflict() -> None:
    # Explicit fill_rate_delta missing -> proxy-only signals used.
    # fill_count_delta optimistic (>0) AND inferred_unfilled_count_delta pessimistic (>0) -> mixed.
    report = build_simulator_calibration_report(
        _comparison(fill_rate_delta=None, fill_count_delta=5, inferred_unfilled_count_delta=3)
    )
    assert report.status == "aligned"
    assert report.drift_classification == "ambiguous"
    assert any("mixed_signals" in n for n in report.notes)
    assert all(s.evidence_level == "proxy" for s in report.signals)


def test_build_report_unusable_when_comparison_unusable() -> None:
    report = build_simulator_calibration_report(
        _comparison(status="unusable", fill_rate_delta=None, alignment_issue="misaligned: symbol mismatch")
    )
    assert report.status == "unusable"
    assert report.drift_classification == "unusable"
    assert report.signals == ()
    assert any("unusable_input" in n for n in report.notes)


def test_load_shadow_comparison_artifact_rejects_non_object() -> None:
    with pytest.raises(SimulatorCalibrationError, match="must be a JSON object"):
        load_shadow_comparison_artifact([])  # type: ignore[arg-type]


def test_load_shadow_comparison_artifact_parses_minimal_payload() -> None:
    payload = _comparison(fill_rate_delta=Decimal("0.01")).to_dict()
    parsed = load_shadow_comparison_artifact(payload)
    assert parsed.status == "aligned"
    assert parsed.replay_run_id == "replay-aabbccddee11-0001"
    assert parsed.fill_rate_delta == Decimal("0.01")

