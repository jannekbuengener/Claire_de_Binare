"""Unit tests for candle rankability provenance (#4065 / #4336 CDB-052)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.arvp_vacation.batch_a_gate_common import record_is_rankable
from tools.arvp_vacation.candle_rankability import (
    FLAG_CANDLES_EVALUATED_MISMATCH,
    FLAG_CONTENT_FINGERPRINT_MISSING,
    FLAG_DQ_CONTENT_FINGERPRINT_MISMATCH,
    FLAG_MANIFEST_MISSING,
    FLAG_RANKABILITY_PROVENANCE_MISSING,
    FLAG_REQUEST_FINGERPRINT_MISMATCH,
    FLAG_REQUEST_FINGERPRINT_ONLY,
    FLAG_STALE_MANIFEST_FALLBACK_BLOCKED,
    FLAG_STALE_RANKABILITY_VERDICT,
    FLAG_WARMUP_MANIFEST_MISMATCH,
    FLAG_WARMUP_MISMATCH,
    FLAG_WARMUP_PROVENANCE_MISSING,
    FLAG_WARMUP_TRIM_APPLIED,
    FLAG_WINDOW_MISMATCH,
    RankabilityProvenanceError,
    assert_rankability_provenance,
    enforce_rankability_provenance,
    resolve_candle_rankability,
)

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[3]
_CONTENT_FP = "a" * 64
_OTHER_FP = "c" * 64
_REQUEST_FP = "b" * 64


def _summary(**extra: object) -> dict:
    base = {
        "candles_total": 44640,
        "candles_live": 44606,
        "warmup_candles": 34,
        "content_fingerprint": _CONTENT_FP,
    }
    base.update(extra)
    return base


def _resolve(**summary_extra: object):
    return resolve_candle_rankability(
        dataset_summary=_summary(**summary_extra),
        strategy_id="breakout_volatility_filter_v1",
        campaign_id="batch_a_stage_a_d0a4e72d_20260713",
        parameter_fingerprint="abc123",
        campaign_source_sha="d0a4e72d10fced72a5fb2d2edf1e40f3c80f417a",
        repo_root=REPO_ROOT,
    )


def test_valid_warmup_trim_is_not_blocking() -> None:
    result = _resolve()
    assert result.candles_total == 44640
    assert result.candles_input_total == 44640
    assert result.candles_evaluated == 44606
    assert result.warmup_bars == 34
    assert FLAG_WARMUP_TRIM_APPLIED in result.data_quality_flags
    assert result.rankability_blocking_flags == ()
    assert result.warmup_provenance["silent_manifest_fallback"] is False


def test_unexplained_candle_delta_is_blocking() -> None:
    result = _resolve(warmup_candles=20)
    assert FLAG_CANDLES_EVALUATED_MISMATCH in result.rankability_blocking_flags


def test_missing_warmup_provenance_is_blocking() -> None:
    result = resolve_candle_rankability(
        dataset_summary={
            "candles_total": 44640,
            "candles_live": 44620,
            "content_fingerprint": _CONTENT_FP,
        },
        strategy_id="donchian_breakout_v1",
        campaign_id="arvp_binance_historical_3990_test",
        parameter_fingerprint=None,
        campaign_source_sha=None,
        repo_root=REPO_ROOT,
    )
    assert FLAG_WARMUP_PROVENANCE_MISSING in result.rankability_blocking_flags


def test_manifest_warmup_mismatch_is_blocking() -> None:
    result = _resolve(candles_total=100, candles_live=50, warmup_candles=99)
    assert FLAG_WARMUP_MANIFEST_MISMATCH in result.rankability_blocking_flags


def test_cdb052_stale_manifest_fallback_is_not_rankable() -> None:
    """Missing run warmup must not be filled from Batch-A manifest (CDB-052)."""
    result = resolve_candle_rankability(
        dataset_summary={
            "candles_total": 100,
            "candles_live": 66,
            "content_fingerprint": _CONTENT_FP,
        },
        strategy_id="breakout_volatility_filter_v1",
        campaign_id="batch_a_stage_a_d0a4e72d_20260713",
        parameter_fingerprint="abc123",
        campaign_source_sha="d0a4e72d10fced72a5fb2d2edf1e40f3c80f417a",
        repo_root=REPO_ROOT,
    )
    assert FLAG_STALE_MANIFEST_FALLBACK_BLOCKED in result.rankability_blocking_flags
    assert FLAG_WARMUP_PROVENANCE_MISSING in result.rankability_blocking_flags
    assert result.warmup_bars is None
    assert result.warmup_provenance["silent_manifest_fallback"] is False


def test_cdb052_missing_manifest_for_batch_a_is_blocking(
    tmp_path: Path,
) -> None:
    """Batch-A campaign without funnel manifest must fail closed (no silent skip)."""
    result = resolve_candle_rankability(
        dataset_summary=_summary(),
        strategy_id="breakout_volatility_filter_v1",
        campaign_id="batch_a_stage_a_synthetic",
        parameter_fingerprint="abc123",
        campaign_source_sha="d0a4e72d10fced72a5fb2d2edf1e40f3c80f417a",
        repo_root=tmp_path,
    )
    assert FLAG_MANIFEST_MISSING in result.rankability_blocking_flags
    assert result.warmup_provenance["manifest_ref"] is None


def test_cdb052_missing_content_fingerprint_is_not_rankable() -> None:
    result = resolve_candle_rankability(
        dataset_summary={
            "candles_total": 44640,
            "candles_live": 44606,
            "warmup_candles": 34,
            "dataset_fingerprint": _REQUEST_FP,
        },
        strategy_id="breakout_volatility_filter_v1",
        campaign_id="batch_a_stage_a_d0a4e72d_20260713",
        parameter_fingerprint="abc123",
        campaign_source_sha="d0a4e72d10fced72a5fb2d2edf1e40f3c80f417a",
        repo_root=REPO_ROOT,
    )
    assert FLAG_CONTENT_FINGERPRINT_MISSING in result.rankability_blocking_flags
    assert FLAG_REQUEST_FINGERPRINT_ONLY in result.rankability_blocking_flags


def test_cdb052_dq_content_binding_missing_is_not_rankable() -> None:
    result = _resolve(dq_verdict="STRICT_COMPLETE")
    from tools.arvp_vacation.candle_rankability import FLAG_DQ_CONTENT_BINDING_MISSING

    assert FLAG_DQ_CONTENT_BINDING_MISSING in result.rankability_blocking_flags

    result = _resolve(dq_content_fingerprint=_OTHER_FP)
    assert FLAG_DQ_CONTENT_FINGERPRINT_MISMATCH in result.rankability_blocking_flags


def test_cdb052_reason_codes_are_deterministic() -> None:
    first = resolve_candle_rankability(
        dataset_summary={
            "candles_total": 100,
            "candles_live": 66,
            "dataset_fingerprint": _REQUEST_FP,
        },
        strategy_id="breakout_volatility_filter_v1",
        campaign_id="batch_a_stage_a_d0a4e72d_20260713",
        parameter_fingerprint="abc123",
        campaign_source_sha="d0a4e72d10fced72a5fb2d2edf1e40f3c80f417a",
        repo_root=REPO_ROOT,
    )
    second = resolve_candle_rankability(
        dataset_summary={
            "candles_total": 100,
            "candles_live": 66,
            "dataset_fingerprint": _REQUEST_FP,
        },
        strategy_id="breakout_volatility_filter_v1",
        campaign_id="batch_a_stage_a_d0a4e72d_20260713",
        parameter_fingerprint="abc123",
        campaign_source_sha="d0a4e72d10fced72a5fb2d2edf1e40f3c80f417a",
        repo_root=REPO_ROOT,
    )
    assert first.rankability_blocking_flags == second.rankability_blocking_flags
    assert first.rankability_blocking_flags == tuple(
        sorted(first.rankability_blocking_flags)
    )


def test_cdb052_stale_content_fingerprint_rejects_reuse() -> None:
    """Independent expected content must not equal evidence copied from itself."""
    expected_content = "d" * 64
    evidence_content = "e" * 64
    assert expected_content != evidence_content
    with pytest.raises(RankabilityProvenanceError) as exc:
        assert_rankability_provenance(
            {
                "content_fingerprint": expected_content,
                "warmup_bars": 34,
            },
            {
                "content_fingerprint": evidence_content,
                "warmup_bars": 34,
                "silent_manifest_fallback": False,
            },
        )
    assert exc.value.code == FLAG_STALE_RANKABILITY_VERDICT


def test_cdb052_warmup_mismatch_rejects_reuse() -> None:
    with pytest.raises(RankabilityProvenanceError) as exc:
        assert_rankability_provenance(
            {"content_fingerprint": _CONTENT_FP, "warmup_bars": 34},
            {
                "content_fingerprint": _CONTENT_FP,
                "warmup_bars": 10,
                "silent_manifest_fallback": False,
            },
        )
    assert exc.value.code == FLAG_WARMUP_MISMATCH


def test_cdb052_window_mismatch_rejects_reuse() -> None:
    with pytest.raises(RankabilityProvenanceError) as exc:
        assert_rankability_provenance(
            {
                "content_fingerprint": _CONTENT_FP,
                "warmup_bars": 34,
                "window_id": "win-a",
                "start_ts_ms": 1,
                "end_ts_ms": 2,
            },
            {
                "content_fingerprint": _CONTENT_FP,
                "warmup_bars": 34,
                "window_id": "win-b",
                "start_ts_ms": 1,
                "end_ts_ms": 2,
                "silent_manifest_fallback": False,
            },
        )
    assert exc.value.code == FLAG_WINDOW_MISMATCH


def test_cdb052_request_fingerprint_mismatch_rejects_reuse() -> None:
    with pytest.raises(RankabilityProvenanceError) as exc:
        assert_rankability_provenance(
            {
                "content_fingerprint": _CONTENT_FP,
                "warmup_bars": 34,
                "request_fingerprint": _REQUEST_FP,
            },
            {
                "content_fingerprint": _CONTENT_FP,
                "warmup_bars": 34,
                "request_fingerprint": _OTHER_FP,
                "silent_manifest_fallback": False,
            },
        )
    assert exc.value.code == FLAG_REQUEST_FINGERPRINT_MISMATCH


def test_cdb052_missing_evidence_is_fail_closed() -> None:
    with pytest.raises(RankabilityProvenanceError) as exc:
        enforce_rankability_provenance(current={"content_fingerprint": _CONTENT_FP})
    assert exc.value.code == FLAG_RANKABILITY_PROVENANCE_MISSING


def test_cdb052_scorer_rejects_missing_rankable_field() -> None:
    assert record_is_rankable({"closed_trades_total": 5}) is False


def test_cdb052_scorer_rejects_historical_rankable_without_provenance() -> None:
    assert (
        record_is_rankable(
            {
                "rankable": True,
                "closed_trades_total": 5,
            }
        )
        is False
    )


def test_cdb052_scorer_rejects_stale_rankability_verdict() -> None:
    bound = _resolve()
    assert bound.rankability_blocking_flags == ()
    record = {
        "rankable": True,
        "closed_trades_total": 5,
        "warmup_provenance": bound.warmup_provenance,
        "rankability_blocking_flags": [],
        "not_rankable_reasons": [],
    }
    assert record_is_rankable(record) is True
    with pytest.raises(RankabilityProvenanceError) as exc:
        enforce_rankability_provenance(
            current={
                "content_fingerprint": _OTHER_FP,
                "warmup_bars": 34,
            },
            evidence=bound.warmup_provenance,
        )
    assert exc.value.code == FLAG_STALE_RANKABILITY_VERDICT


def test_cdb052_identical_inputs_are_deterministic() -> None:
    first = _resolve()
    second = _resolve()
    assert first.rankability_blocking_flags == second.rankability_blocking_flags
    assert first.warmup_provenance == second.warmup_provenance


def test_cdb052_bound_provenance_passes_enforce() -> None:
    result = _resolve()
    enforce_rankability_provenance(
        current={
            "content_fingerprint": _CONTENT_FP,
            "warmup_bars": 34,
            "parameter_fingerprint": "abc123",
            "campaign_source_sha": "d0a4e72d10fced72a5fb2d2edf1e40f3c80f417a",
        },
        evidence=result.warmup_provenance,
    )
