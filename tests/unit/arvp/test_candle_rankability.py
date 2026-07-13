"""Unit tests for candle rankability provenance (#4065)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.arvp_vacation.candle_rankability import (
    FLAG_CANDLES_EVALUATED_MISMATCH,
    FLAG_WARMUP_MANIFEST_MISMATCH,
    FLAG_WARMUP_PROVENANCE_MISSING,
    FLAG_WARMUP_TRIM_APPLIED,
    resolve_candle_rankability,
)

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_valid_warmup_trim_is_not_blocking() -> None:
    result = resolve_candle_rankability(
        dataset_summary={
            "candles_total": 44640,
            "candles_live": 44606,
            "warmup_candles": 34,
        },
        strategy_id="breakout_volatility_filter_v1",
        campaign_id="batch_a_stage_a_d0a4e72d_20260713",
        parameter_fingerprint="abc123",
        campaign_source_sha="d0a4e72d10fced72a5fb2d2edf1e40f3c80f417a",
        repo_root=REPO_ROOT,
    )
    assert result.candles_total == 44640
    assert result.candles_input_total == 44640
    assert result.candles_evaluated == 44606
    assert result.warmup_bars == 34
    assert FLAG_WARMUP_TRIM_APPLIED in result.data_quality_flags
    assert result.rankability_blocking_flags == ()


def test_unexplained_candle_delta_is_blocking() -> None:
    result = resolve_candle_rankability(
        dataset_summary={
            "candles_total": 44640,
            "candles_live": 44606,
            "warmup_candles": 20,
        },
        strategy_id="breakout_volatility_filter_v1",
        campaign_id="batch_a_stage_a_d0a4e72d_20260713",
        parameter_fingerprint="abc123",
        campaign_source_sha="d0a4e72d10fced72a5fb2d2edf1e40f3c80f417a",
        repo_root=REPO_ROOT,
    )
    assert FLAG_CANDLES_EVALUATED_MISMATCH in result.rankability_blocking_flags


def test_missing_warmup_provenance_is_blocking() -> None:
    result = resolve_candle_rankability(
        dataset_summary={"candles_total": 44640, "candles_live": 44620},
        strategy_id="donchian_breakout_v1",
        campaign_id="arvp_binance_historical_3990_test",
        parameter_fingerprint=None,
        campaign_source_sha=None,
        repo_root=REPO_ROOT,
    )
    assert FLAG_WARMUP_PROVENANCE_MISSING in result.rankability_blocking_flags


def test_manifest_warmup_mismatch_is_blocking() -> None:
    result = resolve_candle_rankability(
        dataset_summary={
            "candles_total": 100,
            "candles_live": 50,
            "warmup_candles": 99,
        },
        strategy_id="breakout_volatility_filter_v1",
        campaign_id="batch_a_stage_a_d0a4e72d_20260713",
        parameter_fingerprint="abc123",
        campaign_source_sha="d0a4e72d10fced72a5fb2d2edf1e40f3c80f417a",
        repo_root=REPO_ROOT,
    )
    assert FLAG_WARMUP_MANIFEST_MISMATCH in result.rankability_blocking_flags
