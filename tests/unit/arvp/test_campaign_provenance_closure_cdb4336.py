"""Post-fix campaign provenance closure check for #4336 (no campaign runs)."""

from __future__ import annotations

import pytest

from core.replay.dataset_integrity_rules import (
    REPLAY_VS_RUNTIME_CONTRACT,
    REPLAY_VS_RUNTIME_CONTRACT_VERSION,
    assert_replay_integrity,
)
from core.replay.dataset_provider import enforce_exact_window, warmup_start_ms
from tools.arvp_vacation.candle_rankability import (
    FLAG_STALE_MANIFEST_FALLBACK_BLOCKED,
    resolve_candle_rankability,
)
from tools.market_data.development_window_selector import (
    LOCKED_BATCH_A_DEVELOPMENT_WINDOW_IDS,
)
from tools.market_data.historical_common import (
    NormalizedCandle,
    assert_dq_content_binding,
    build_quality_report,
)

pytestmark = pytest.mark.unit

_BASE = 1_700_000_000_000


def test_campaign_provenance_ready_cdb049_to_052(tmp_path_factory, repo_root=None):
    from pathlib import Path

    root = Path(__file__).resolve().parents[3]

    # CDB-049: exact window helpers exist and 39 locked windows remain file-backed.
    assert len(LOCKED_BATCH_A_DEVELOPMENT_WINDOW_IDS) == 39
    from core.replay.dataset_spec import DatasetSpec

    spec = DatasetSpec(
        symbol="BTCUSDT",
        timeframe="1m",
        start_ts_ms=_BASE,
        end_ts_ms=_BASE + 60_000,
        warmup_candles=1,
        source="file",
        file_path="x.json",
    )
    candles = [
        {"ts_ms": warmup_start_ms(spec), "high": 1, "low": 1, "close": 1},
        {"ts_ms": _BASE, "high": 1, "low": 1, "close": 1},
        {"ts_ms": _BASE + 60_000, "high": 1, "low": 1, "close": 1},
    ]
    enforce_exact_window(candles, spec, "file:closure")

    # CDB-050
    rows = [
        NormalizedCandle(
            ts_ms=_BASE + i * 60_000,
            open="1",
            high="1",
            low="1",
            close="1",
            volume="1",
            quote_volume=None,
            trade_count=None,
            symbol="BTCUSDT",
            venue="binance",
            timeframe="1m",
            source_type="test",
            source_file_sha256="d" * 64,
        )
        for i in range(2)
    ]
    report = build_quality_report(
        rows,
        start_ts_ms=_BASE,
        end_ts_ms=_BASE + 60_000,
        step_ms=60_000,
        source_hash="e" * 64,
    )
    assert_dq_content_binding(report, content_fingerprint=report["content_fingerprint"])

    # CDB-051
    assert (
        REPLAY_VS_RUNTIME_CONTRACT["schema_version"]
        == REPLAY_VS_RUNTIME_CONTRACT_VERSION
    )
    assert_replay_integrity(
        [
            {"ts_ms": _BASE, "close": 1, "high": 1, "low": 1},
            {"ts_ms": _BASE + 60_000, "close": 1, "high": 1, "low": 1},
        ],
        start_ts_ms=_BASE,
        end_ts_ms=_BASE + 60_000,
    )

    # CDB-052
    blocked = resolve_candle_rankability(
        dataset_summary={
            "candles_total": 100,
            "candles_live": 66,
            "content_fingerprint": "a" * 64,
        },
        strategy_id="breakout_volatility_filter_v1",
        campaign_id="batch_a_stage_a_d0a4e72d_20260713",
        parameter_fingerprint="abc",
        campaign_source_sha="d0a4e72d10fced72a5fb2d2edf1e40f3c80f417a",
        repo_root=root,
    )
    assert FLAG_STALE_MANIFEST_FALLBACK_BLOCKED in blocked.rankability_blocking_flags

    rankable = resolve_candle_rankability(
        dataset_summary={
            "candles_total": 44640,
            "candles_live": 44606,
            "warmup_candles": 34,
            "content_fingerprint": "a" * 64,
        },
        strategy_id="breakout_volatility_filter_v1",
        campaign_id="batch_a_stage_a_d0a4e72d_20260713",
        parameter_fingerprint="abc",
        campaign_source_sha="d0a4e72d10fced72a5fb2d2edf1e40f3c80f417a",
        repo_root=root,
    )
    assert rankable.rankability_blocking_flags == ()
