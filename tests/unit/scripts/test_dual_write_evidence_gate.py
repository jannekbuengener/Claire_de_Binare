"""Unit tests for scripts/dual_write_evidence_gate.py (Issue #1201).

Tests focus on compare_symbol() — the pure comparison logic — and run_gate()
with a mocked Redis client. No live Redis required.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))

from dual_write_evidence_gate import (
    CANDLES_PREFIX,
    RETURN_TOL,
    SHADOW_PREFIX,
    TICK_TS_TOL_MS,
    compare_symbol,
    run_gate,
)


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _make_state(
    symbol: str = "BTCUSDT",
    return_1m: float = 0.01,
    return_5m: float = 0.05,
    price_change_5m: float = 0.05,
    ts_ms: int = 1_700_000_060_000,
    last_tick_ts_ms: int | None = 1_700_000_059_000,
    regime_id: int | None = 0,
) -> str:
    payload: dict = {
        "symbol": symbol,
        "return_1m": return_1m,
        "return_5m": return_5m,
        "price_change_5m": price_change_5m,
        "ts_ms": ts_ms,
        "last_tick_ts_ms": last_tick_ts_ms,
        "close_now": 110.0,
        "close_1m_ago": 100.0,
        "close_5m_ago": 50.0,
    }
    if regime_id is not None:
        payload["regime_id"] = regime_id
    return json.dumps(payload)


# ─── compare_symbol — happy path ──────────────────────────────────────────────


@pytest.mark.unit
def test_identical_payloads_pass():
    """Both writers produce identical values → PASS."""
    raw = _make_state()
    result = compare_symbol("BTCUSDT", raw, raw)
    assert result["result"] == "PASS"
    failed = [f for f in result["fields"] if f["result"] == "FAIL"]
    assert not failed


@pytest.mark.unit
def test_ts_ms_gap_within_tolerance_pass():
    """ts_ms gap of 60 000 ms (one candle cycle) → PASS."""
    c = _make_state(ts_ms=1_700_000_060_000)
    s = _make_state(ts_ms=1_700_000_000_000)
    result = compare_symbol("BTCUSDT", c, s)
    ts_field = next(f for f in result["fields"] if f["field"] == "ts_ms_gap")
    assert ts_field["result"] == "PASS"
    assert ts_field["gap_ms"] == 60_000


# ─── compare_symbol — missing keys ────────────────────────────────────────────


@pytest.mark.unit
def test_candles_key_missing_fail():
    """market_state:{symbol} missing → FAIL with explanation."""
    result = compare_symbol("BTCUSDT", None, _make_state())
    assert result["result"] == "FAIL"
    assert "candles key missing" in result["reason"]


@pytest.mark.unit
def test_shadow_key_missing_fail():
    """market_state_shadow:{symbol} missing → FAIL with explanation."""
    result = compare_symbol("BTCUSDT", _make_state(), None)
    assert result["result"] == "FAIL"
    assert "shadow key missing" in result["reason"]


@pytest.mark.unit
def test_both_keys_missing_fail():
    """Both keys missing → FAIL (candles reason takes priority)."""
    result = compare_symbol("BTCUSDT", None, None)
    assert result["result"] == "FAIL"
    assert "candles key missing" in result["reason"]


# ─── compare_symbol — ts_ms gap ───────────────────────────────────────────────


@pytest.mark.unit
def test_ts_ms_gap_too_large_fail():
    """ts_ms gap of 91 000 ms (> 90 000 max) → FAIL on ts_ms_gap field."""
    c = _make_state(ts_ms=1_700_000_091_000)
    s = _make_state(ts_ms=1_700_000_000_000)
    result = compare_symbol("BTCUSDT", c, s)
    assert result["result"] == "FAIL"
    ts_field = next(f for f in result["fields"] if f["field"] == "ts_ms_gap")
    assert ts_field["result"] == "FAIL"
    assert ts_field["gap_ms"] == 91_000


@pytest.mark.unit
def test_ts_ms_gap_at_boundary_pass():
    """ts_ms gap of exactly 90 000 ms → PASS (boundary is inclusive)."""
    c = _make_state(ts_ms=1_700_000_090_000)
    s = _make_state(ts_ms=1_700_000_000_000)
    result = compare_symbol("BTCUSDT", c, s)
    ts_field = next(f for f in result["fields"] if f["field"] == "ts_ms_gap")
    assert ts_field["result"] == "PASS"


# ─── compare_symbol — return field divergence ─────────────────────────────────


@pytest.mark.unit
def test_return_1m_divergence_fail():
    """return_1m delta above tolerance → FAIL."""
    c = _make_state(return_1m=0.01)
    s = _make_state(return_1m=0.01 + RETURN_TOL * 10)
    result = compare_symbol("BTCUSDT", c, s)
    assert result["result"] == "FAIL"
    field = next(f for f in result["fields"] if f["field"] == "return_1m")
    assert field["result"] == "FAIL"


@pytest.mark.unit
def test_return_5m_divergence_fail():
    """return_5m delta above tolerance → FAIL."""
    c = _make_state(return_5m=0.05)
    s = _make_state(return_5m=0.05 + RETURN_TOL * 10)
    result = compare_symbol("BTCUSDT", c, s)
    field = next(f for f in result["fields"] if f["field"] == "return_5m")
    assert field["result"] == "FAIL"


@pytest.mark.unit
def test_price_change_5m_divergence_fail():
    """price_change_5m delta above tolerance → FAIL."""
    c = _make_state(price_change_5m=0.05)
    s = _make_state(price_change_5m=0.05 + RETURN_TOL * 10)
    result = compare_symbol("BTCUSDT", c, s)
    field = next(f for f in result["fields"] if f["field"] == "price_change_5m")
    assert field["result"] == "FAIL"


@pytest.mark.unit
def test_return_fields_within_tolerance_pass():
    """Float return fields identical → all PASS."""
    raw = _make_state(return_1m=0.01234567890, return_5m=0.05, price_change_5m=0.05)
    result = compare_symbol("BTCUSDT", raw, raw)
    for fname in ("return_1m", "return_5m", "price_change_5m"):
        field = next(f for f in result["fields"] if f["field"] == fname)
        assert field["result"] == "PASS", f"{fname} should be PASS"


# ─── compare_symbol — last_tick_ts_ms ─────────────────────────────────────────


@pytest.mark.unit
def test_last_tick_ts_ms_within_tolerance_pass():
    """last_tick_ts_ms delta of 89 999 ms → PASS (< 90 000 ms structural tolerance).

    Tolerance calibrated from first real run 2026-03-18: observed delta 9 927 ms
    due to structural trigger-timing difference (cdb_candles: once per candle emission
    ~60 s; cdb_market: per market_data message, continuous).
    """
    c = _make_state(last_tick_ts_ms=1_700_000_089_999)
    s = _make_state(last_tick_ts_ms=1_700_000_000_000)
    result = compare_symbol("BTCUSDT", c, s)
    field = next(f for f in result["fields"] if f["field"] == "last_tick_ts_ms")
    assert field["result"] == "PASS"
    assert field["delta_ms"] == 89_999


@pytest.mark.unit
def test_last_tick_ts_ms_divergence_fail():
    """last_tick_ts_ms delta of 90 001 ms (> 90 000 tolerance) → FAIL."""
    c = _make_state(last_tick_ts_ms=1_700_000_090_001)
    s = _make_state(last_tick_ts_ms=1_700_000_000_000)
    result = compare_symbol("BTCUSDT", c, s)
    field = next(f for f in result["fields"] if f["field"] == "last_tick_ts_ms")
    assert field["result"] == "FAIL"
    assert field["delta_ms"] == 90_001


@pytest.mark.unit
def test_last_tick_ts_ms_both_none_pass():
    """Both last_tick_ts_ms None → PASS (both writers agree: no tick yet)."""
    c = _make_state(last_tick_ts_ms=None)
    s = _make_state(last_tick_ts_ms=None)
    result = compare_symbol("BTCUSDT", c, s)
    field = next(f for f in result["fields"] if f["field"] == "last_tick_ts_ms")
    assert field["result"] == "PASS"


@pytest.mark.unit
def test_last_tick_ts_ms_one_none_fail():
    """last_tick_ts_ms None in shadow but set in candles → FAIL."""
    c = _make_state(last_tick_ts_ms=1_700_000_059_000)
    s = _make_state(last_tick_ts_ms=None)
    result = compare_symbol("BTCUSDT", c, s)
    field = next(f for f in result["fields"] if f["field"] == "last_tick_ts_ms")
    assert field["result"] == "FAIL"


# ─── compare_symbol — regime_id ───────────────────────────────────────────────


@pytest.mark.unit
def test_regime_id_both_absent_pass():
    """Both payloads without regime_id → PASS (fail-closed consistency)."""
    c = _make_state(regime_id=None)
    s = _make_state(regime_id=None)
    result = compare_symbol("BTCUSDT", c, s)
    field = next(f for f in result["fields"] if f["field"] == "regime_id")
    assert field["result"] == "PASS"


@pytest.mark.unit
def test_regime_id_both_present_match_pass():
    """Both payloads with same regime_id=1 → PASS."""
    c = _make_state(regime_id=1)
    s = _make_state(regime_id=1)
    result = compare_symbol("BTCUSDT", c, s)
    field = next(f for f in result["fields"] if f["field"] == "regime_id")
    assert field["result"] == "PASS"


@pytest.mark.unit
def test_regime_id_mismatch_fail():
    """regime_id=0 in candles vs regime_id=1 in shadow → FAIL."""
    c = _make_state(regime_id=0)
    s = _make_state(regime_id=1)
    result = compare_symbol("BTCUSDT", c, s)
    assert result["result"] == "FAIL"
    field = next(f for f in result["fields"] if f["field"] == "regime_id")
    assert field["result"] == "FAIL"
    assert "mismatch" in field["reason"]


@pytest.mark.unit
def test_regime_id_absent_in_shadow_fail():
    """regime_id present in candles but absent in shadow → FAIL."""
    c = _make_state(regime_id=0)
    s = _make_state(regime_id=None)
    result = compare_symbol("BTCUSDT", c, s)
    field = next(f for f in result["fields"] if f["field"] == "regime_id")
    assert field["result"] == "FAIL"
    assert "candles" in field["reason"]


@pytest.mark.unit
def test_regime_id_absent_in_candles_fail():
    """regime_id absent in candles but present in shadow → FAIL."""
    c = _make_state(regime_id=None)
    s = _make_state(regime_id=2)
    result = compare_symbol("BTCUSDT", c, s)
    field = next(f for f in result["fields"] if f["field"] == "regime_id")
    assert field["result"] == "FAIL"
    assert "shadow" in field["reason"]


# ─── run_gate — mocked Redis ───────────────────────────────────────────────────


def _make_mock_redis(symbol_map: dict[str, tuple[str | None, str | None]]) -> MagicMock:
    """Build a mock Redis client with preset get() and keys() responses.

    symbol_map: { symbol: (candles_raw, shadow_raw) }
    """
    mock = MagicMock()

    def keys(pattern: str) -> list[str]:
        prefix = pattern.rstrip("*")
        return [f"{CANDLES_PREFIX}:{sym}" for sym in symbol_map]

    def get(key: str) -> str | None:
        for sym, (c, s) in symbol_map.items():
            if key == f"{CANDLES_PREFIX}:{sym}":
                return c
            if key == f"{SHADOW_PREFIX}:{sym}":
                return s
        return None

    mock.keys.side_effect = keys
    mock.get.side_effect = get
    return mock


@pytest.mark.unit
def test_run_gate_all_pass():
    """All symbols pass → overall PASS, exit 0."""
    raw = _make_state()
    mock_redis = _make_mock_redis({"BTCUSDT": (raw, raw), "ETHUSDT": (raw, raw)})
    report = run_gate(mock_redis)
    assert report["overall"] == "PASS"
    assert report["symbols_checked"] == 2
    assert report["symbols_pass"] == 2
    assert report["symbols_fail"] == 0


@pytest.mark.unit
def test_run_gate_one_fail():
    """One symbol fails shadow key missing → overall FAIL."""
    raw = _make_state()
    mock_redis = _make_mock_redis(
        {"BTCUSDT": (raw, raw), "ETHUSDT": (raw, None)}
    )
    report = run_gate(mock_redis)
    assert report["overall"] == "FAIL"
    assert report["symbols_fail"] == 1
    assert report["symbols_pass"] == 1


@pytest.mark.unit
def test_run_gate_no_symbols_blocked():
    """No market_state:* keys → overall BLOCKED (not PASS)."""
    mock_redis = _make_mock_redis({})
    report = run_gate(mock_redis)
    assert report["overall"] == "BLOCKED"
    assert report["symbols_checked"] == 0


@pytest.mark.unit
def test_run_gate_report_contains_tolerances():
    """Evidence report must document the tolerances used."""
    mock_redis = _make_mock_redis({})
    report = run_gate(mock_redis)
    assert "tolerances" in report
    assert "return_fields_abs" in report["tolerances"]
    assert "last_tick_ts_ms_ms" in report["tolerances"]
    assert "ts_ms_gap_ms" in report["tolerances"]


@pytest.mark.unit
def test_run_gate_writes_json_output(tmp_path: Path):
    """run_gate writes valid JSON evidence artefact when output_path is given."""
    raw = _make_state()
    mock_redis = _make_mock_redis({"BTCUSDT": (raw, raw)})
    output = tmp_path / "evidence.json"
    run_gate(mock_redis, output_path=output)
    assert output.is_file()
    data = json.loads(output.read_text())
    assert data["overall"] == "PASS"
    assert data["schema_version"] == "1"
    assert "generated_at" in data


@pytest.mark.unit
def test_run_gate_symbol_results_sorted():
    """Symbols in the report must be in sorted order."""
    raw = _make_state()
    mock_redis = _make_mock_redis(
        {"XRPUSDT": (raw, raw), "BTCUSDT": (raw, raw), "ETHUSDT": (raw, raw)}
    )
    report = run_gate(mock_redis)
    reported_symbols = [r["symbol"] for r in report["symbol_results"]]
    assert reported_symbols == sorted(reported_symbols)
