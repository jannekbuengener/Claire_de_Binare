"""Unit tests for services/market/tools/v3_compare.py (Issue #1206 shadow compare/gate)."""

import json
from unittest.mock import MagicMock, patch

import pytest

from services.market.tools.v3_compare import (
    MODE_LIVE_WRITE_SMOKE,
    MODE_SHADOW_COMPARE,
    SCHEMA_VERSION,
    STALE_THRESHOLD_MS,
    GateThresholds,
    LiveWriteSmokeThresholds,
    build_report,
    collect_samples,
    compare_snapshot,
    evaluate_gate,
    evaluate_gate_smoke,
    summarize,
)

# ─── Fixtures ─────────────────────────────────────────────────────────────────

_NOW_MS = 1_700_000_030_000  # arbitrary reference epoch-ms


def _live(price: str = "50000.00", ts_ms: int = 1_700_000_000_000) -> dict:
    return {
        "symbol": "BTCUSDT",
        "price": price,
        "ts_ms": ts_ms,
        "source": "mexc",
        "trade_qty": "0.001",
        "side": "BUY",
        "cached_at_ms": ts_ms + 1,
    }


def _shadow(price: str = "50000.00", ts_ms: int = 1_700_000_001_000) -> dict:
    return {
        "symbol": "BTCUSDT",
        "price": price,
        "ts_ms": ts_ms,
        "source": "mexc",
        "trade_qty": "0.001",
        "side": "buy",
        "cached_at_ms": ts_ms + 2,
    }


def _make_summary(
    total: int = 20,
    comparable: int = 20,
    missing_shadow: int = 0,
    missing_live: int = 0,
    stale_shadow: int = 0,
    stale_live: int = 0,
    price_delta_rel_pct_p95: float = 0.0,
    price_delta_rel_pct_max: float = 0.0,
    ts_delta_ms_p95: float = 100.0,
) -> dict:
    """Build a synthetic summary dict for gate tests — no real Redis needed."""
    return {
        "total_samples": total,
        "comparable_samples": comparable,
        "missing_live_count": missing_live,
        "missing_shadow_count": missing_shadow,
        "stale_live_count": stale_live,
        "stale_shadow_count": stale_shadow,
        "price_delta_abs": {"min": 0.0, "max": 0.0, "mean": 0.0, "p95": 0.0},
        "price_delta_rel_pct": {
            "min": 0.0,
            "max": price_delta_rel_pct_max,
            "mean": 0.0,
            "p95": price_delta_rel_pct_p95,
        },
        "ts_delta_ms": {
            "min": 0,
            "max": ts_delta_ms_p95,
            "mean": 50,
            "p95": ts_delta_ms_p95,
        },
        "live_age_ms": {"min": 0, "max": 1000, "mean": 500, "p95": 900},
        "shadow_age_ms": {"min": 0, "max": 1000, "mean": 500, "p95": 900},
    }


def _make_smoke_summary(
    total: int = 20,
    missing_live: int = 0,
    missing_shadow: int = 20,
    stale_live_total: int = 0,
) -> dict:
    """Build a synthetic summary for live_write_smoke gate tests.

    In smoke mode: shadow key is always absent, live key is the only data source.
    """
    live_present = total - missing_live
    return {
        "total_samples": total,
        "comparable_samples": 0,
        "live_present_count": live_present,
        "missing_live_count": missing_live,
        "missing_shadow_count": missing_shadow,
        "stale_live_count": 0,  # always 0 (no comparable samples)
        "stale_live_total_count": stale_live_total,
        "stale_shadow_count": 0,
        "price_delta_abs": {"min": None, "max": None, "mean": None, "p95": None},
        "price_delta_rel_pct": {"min": None, "max": None, "mean": None, "p95": None},
        "ts_delta_ms": {"min": None, "max": None, "mean": None, "p95": None},
        "live_age_ms": {"min": None, "max": None, "mean": None, "p95": None},
        "shadow_age_ms": {"min": None, "max": None, "mean": None, "p95": None},
    }


# ─── compare_snapshot: happy path ─────────────────────────────────────────────


@pytest.mark.unit
def test_compare_snapshot_comparable_true_when_both_present():
    snap = compare_snapshot(_live(), _shadow(), _NOW_MS)
    assert snap["comparable"] is True


@pytest.mark.unit
def test_compare_snapshot_price_delta_abs_identical_prices():
    snap = compare_snapshot(_live("50000.00"), _shadow("50000.00"), _NOW_MS)
    assert snap["price_delta_abs"] == pytest.approx(0.0)


@pytest.mark.unit
def test_compare_snapshot_price_delta_abs_different_prices():
    snap = compare_snapshot(_live("50000.00"), _shadow("50010.00"), _NOW_MS)
    assert snap["price_delta_abs"] == pytest.approx(10.0)


@pytest.mark.unit
def test_compare_snapshot_price_delta_rel_pct_correct():
    # 10 / 50000 * 100 = 0.02 %
    snap = compare_snapshot(_live("50000.00"), _shadow("50010.00"), _NOW_MS)
    assert snap["price_delta_rel_pct"] == pytest.approx(0.02, rel=1e-4)


@pytest.mark.unit
def test_compare_snapshot_ts_delta_ms_correct():
    snap = compare_snapshot(
        _live(ts_ms=1_700_000_000_000),
        _shadow(ts_ms=1_700_000_001_500),
        _NOW_MS,
    )
    assert snap["ts_delta_ms"] == 1500


@pytest.mark.unit
def test_compare_snapshot_live_age_ms_correct():
    snap = compare_snapshot(
        _live(ts_ms=_NOW_MS - 5_000),
        _shadow(ts_ms=_NOW_MS - 3_000),
        _NOW_MS,
    )
    assert snap["live_age_ms"] == 5_000
    assert snap["shadow_age_ms"] == 3_000


@pytest.mark.unit
def test_compare_snapshot_prices_are_preserved_as_strings():
    snap = compare_snapshot(_live("49999.99"), _shadow("50000.01"), _NOW_MS)
    assert snap["live_price"] == "49999.99"
    assert snap["shadow_price"] == "50000.01"


@pytest.mark.unit
def test_compare_snapshot_ts_sample_ms_set_correctly():
    snap = compare_snapshot(_live(), _shadow(), _NOW_MS)
    assert snap["ts_sample_ms"] == _NOW_MS


# ─── compare_snapshot: missing keys ───────────────────────────────────────────


@pytest.mark.unit
def test_compare_snapshot_live_missing_sets_flag():
    snap = compare_snapshot(None, _shadow(), _NOW_MS)
    assert snap["live_missing"] is True
    assert snap["comparable"] is False


@pytest.mark.unit
def test_compare_snapshot_shadow_missing_sets_flag():
    snap = compare_snapshot(_live(), None, _NOW_MS)
    assert snap["shadow_missing"] is True
    assert snap["comparable"] is False


@pytest.mark.unit
def test_compare_snapshot_both_missing():
    snap = compare_snapshot(None, None, _NOW_MS)
    assert snap["live_missing"] is True
    assert snap["shadow_missing"] is True
    assert snap["comparable"] is False


# ─── compare_snapshot: live freshness even when shadow absent ─────────────────


@pytest.mark.unit
def test_compare_snapshot_live_age_computed_when_shadow_missing():
    """live_age_ms and live_stale are available even when shadow key is absent.

    This is required by live_write_smoke mode: the gate must assess live key
    freshness independently of shadow key presence.
    """
    fresh_ts = _NOW_MS - 5_000
    snap = compare_snapshot(_live(ts_ms=fresh_ts), None, _NOW_MS)
    assert snap["comparable"] is False
    assert snap["shadow_missing"] is True
    assert snap["live_age_ms"] == 5_000
    assert snap["live_stale"] is False


@pytest.mark.unit
def test_compare_snapshot_live_stale_set_when_shadow_missing():
    old_ts = _NOW_MS - STALE_THRESHOLD_MS - 1
    snap = compare_snapshot(_live(ts_ms=old_ts), None, _NOW_MS)
    assert snap["comparable"] is False
    assert snap["live_stale"] is True


@pytest.mark.unit
def test_compare_snapshot_no_live_age_when_live_missing():
    """When live key absent, live_age_ms and live_stale are not set."""
    snap = compare_snapshot(None, _shadow(), _NOW_MS)
    assert "live_age_ms" not in snap
    assert "live_stale" not in snap


# ─── compare_snapshot: stale detection ────────────────────────────────────────


@pytest.mark.unit
def test_compare_snapshot_live_stale_when_age_exceeds_threshold():
    old_ts = _NOW_MS - STALE_THRESHOLD_MS - 1
    snap = compare_snapshot(
        _live(ts_ms=old_ts), _shadow(ts_ms=_NOW_MS - 1_000), _NOW_MS
    )
    assert snap["live_stale"] is True
    assert snap["shadow_stale"] is False


@pytest.mark.unit
def test_compare_snapshot_shadow_stale_when_age_exceeds_threshold():
    old_ts = _NOW_MS - STALE_THRESHOLD_MS - 1
    snap = compare_snapshot(
        _live(ts_ms=_NOW_MS - 1_000), _shadow(ts_ms=old_ts), _NOW_MS
    )
    assert snap["shadow_stale"] is True
    assert snap["live_stale"] is False


@pytest.mark.unit
def test_compare_snapshot_not_stale_when_fresh():
    fresh_ts = _NOW_MS - 1_000  # 1 second old
    snap = compare_snapshot(_live(ts_ms=fresh_ts), _shadow(ts_ms=fresh_ts), _NOW_MS)
    assert snap["live_stale"] is False
    assert snap["shadow_stale"] is False


# ─── compare_snapshot: invalid payloads ───────────────────────────────────────


@pytest.mark.unit
def test_compare_snapshot_non_numeric_price_sets_comparable_false():
    bad_live = _live()
    bad_live["price"] = "not-a-number"
    snap = compare_snapshot(bad_live, _shadow(), _NOW_MS)
    assert snap["comparable"] is False
    assert "error" in snap


@pytest.mark.unit
def test_compare_snapshot_missing_price_key_sets_comparable_false():
    bad = _live()
    del bad["price"]
    snap = compare_snapshot(bad, _shadow(), _NOW_MS)
    assert snap["comparable"] is False


@pytest.mark.unit
def test_compare_snapshot_live_price_zero_sets_rel_pct_none():
    snap = compare_snapshot(_live("0.00"), _shadow("0.01"), _NOW_MS)
    # live_price=0 → can't compute relative delta
    assert snap["price_delta_rel_pct"] is None


# ─── summarize ────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_summarize_empty_samples_returns_none_stats():
    s = summarize([])
    assert s["total_samples"] == 0
    assert s["comparable_samples"] == 0
    assert s["price_delta_abs"]["min"] is None
    assert s["price_delta_abs"]["mean"] is None


@pytest.mark.unit
def test_summarize_counts_missing_live_and_shadow():
    samples = [
        compare_snapshot(None, _shadow(), _NOW_MS),
        compare_snapshot(_live(), None, _NOW_MS),
        compare_snapshot(None, None, _NOW_MS),
    ]
    s = summarize(samples)
    assert s["missing_live_count"] == 2  # sample 0 and 2
    assert s["missing_shadow_count"] == 2  # sample 1 and 2
    assert s["comparable_samples"] == 0


@pytest.mark.unit
def test_summarize_correct_stats_for_comparable_samples():
    deltas = [10.0, 20.0, 30.0]
    samples = [
        compare_snapshot(_live("50000.00"), _shadow(str(50000.0 + d)), _NOW_MS)
        for d in deltas
    ]
    s = summarize(samples)
    assert s["comparable_samples"] == 3
    assert s["price_delta_abs"]["min"] == pytest.approx(10.0)
    assert s["price_delta_abs"]["max"] == pytest.approx(30.0)
    assert s["price_delta_abs"]["mean"] == pytest.approx(20.0)


@pytest.mark.unit
def test_summarize_counts_stale_correctly():
    old_ts = _NOW_MS - STALE_THRESHOLD_MS - 1
    fresh_ts = _NOW_MS - 1_000
    samples = [
        compare_snapshot(_live(ts_ms=old_ts), _shadow(ts_ms=fresh_ts), _NOW_MS),
        compare_snapshot(_live(ts_ms=fresh_ts), _shadow(ts_ms=old_ts), _NOW_MS),
        compare_snapshot(_live(ts_ms=fresh_ts), _shadow(ts_ms=fresh_ts), _NOW_MS),
    ]
    s = summarize(samples)
    assert s["stale_live_count"] == 1
    assert s["stale_shadow_count"] == 1


@pytest.mark.unit
def test_summarize_p95_is_highest_when_single_sample():
    samples = [compare_snapshot(_live("50000.00"), _shadow("50010.00"), _NOW_MS)]
    s = summarize(samples)
    # single value: p95 == that value
    assert s["price_delta_abs"]["p95"] == pytest.approx(10.0)


@pytest.mark.unit
def test_summarize_live_present_count():
    """live_present_count tracks samples where live key exists, regardless of shadow."""
    samples = [
        compare_snapshot(_live(), None, _NOW_MS),  # live present, shadow absent
        compare_snapshot(_live(), _shadow(), _NOW_MS),  # both present
        compare_snapshot(None, _shadow(), _NOW_MS),  # live absent
    ]
    s = summarize(samples)
    assert s["live_present_count"] == 2


@pytest.mark.unit
def test_summarize_stale_live_total_count_includes_non_comparable():
    """stale_live_total_count counts stale live keys even when shadow is absent."""
    old_ts = _NOW_MS - STALE_THRESHOLD_MS - 1
    fresh_ts = _NOW_MS - 1_000
    samples = [
        compare_snapshot(_live(ts_ms=old_ts), None, _NOW_MS),  # stale live, no shadow
        compare_snapshot(_live(ts_ms=fresh_ts), None, _NOW_MS),  # fresh live, no shadow
        compare_snapshot(
            _live(ts_ms=old_ts), _shadow(), _NOW_MS
        ),  # stale live + shadow
    ]
    s = summarize(samples)
    assert s["stale_live_total_count"] == 2  # both stale-live samples counted
    assert s["stale_live_count"] == 1  # only the comparable one


# ─── evaluate_gate: PASS ──────────────────────────────────────────────────────


@pytest.mark.unit
def test_evaluate_gate_pass_all_criteria_satisfied():
    """All default thresholds satisfied → PASS."""
    summary = _make_summary(
        total=20,
        comparable=20,
        missing_shadow=0,
        stale_shadow=0,
        price_delta_rel_pct_p95=0.01,
        price_delta_rel_pct_max=0.02,
        ts_delta_ms_p95=500,
    )
    gate = evaluate_gate(summary, GateThresholds())
    assert gate["gate_status"] == "PASS"
    assert all(c["result"] in ("PASS", "SKIP") for c in gate["checks"])


@pytest.mark.unit
def test_evaluate_gate_pass_includes_all_criteria_in_checks():
    """Checks list must contain all 6 criterion names when enough data."""
    summary = _make_summary()
    gate = evaluate_gate(summary, GateThresholds())
    criteria = {c["criterion"] for c in gate["checks"]}
    expected = {
        "max_missing_shadow_pct",
        "min_comparable_samples",
        "max_stale_shadow_pct",
        "max_price_delta_rel_p95_pct",
        "max_price_delta_rel_max_pct",
        "max_ts_delta_ms_p95",
    }
    assert expected <= criteria


@pytest.mark.unit
def test_evaluate_gate_checks_contain_threshold_and_measured():
    """Each check record must expose threshold and measured values."""
    summary = _make_summary()
    gate = evaluate_gate(summary, GateThresholds())
    for chk in gate["checks"]:
        assert "threshold" in chk
        assert "measured" in chk
        assert "result" in chk


@pytest.mark.unit
def test_evaluate_gate_thresholds_included_in_result():
    """Thresholds used must be reproduced verbatim in the gate result."""
    t = GateThresholds(min_comparable_samples=30, max_missing_shadow_pct=0.02)
    summary = _make_summary(total=30, comparable=30)
    gate = evaluate_gate(summary, t)
    assert gate["thresholds"]["min_comparable_samples"] == 30
    assert gate["thresholds"]["max_missing_shadow_pct"] == 0.02


# ─── evaluate_gate: INCONCLUSIVE ──────────────────────────────────────────────


@pytest.mark.unit
def test_evaluate_gate_inconclusive_when_too_few_comparable_samples():
    """comparable < min_comparable_samples → INCONCLUSIVE (not FAIL)."""
    summary = _make_summary(total=10, comparable=5)  # 5 < default 20
    gate = evaluate_gate(summary, GateThresholds())
    assert gate["gate_status"] == "INCONCLUSIVE"


@pytest.mark.unit
def test_evaluate_gate_inconclusive_skips_stats_checks():
    """Stats-based criteria are SKIP when not enough comparable samples."""
    summary = _make_summary(total=5, comparable=3)
    gate = evaluate_gate(summary, GateThresholds())
    skip_criteria = {c["criterion"] for c in gate["checks"] if c["result"] == "SKIP"}
    assert "max_stale_shadow_pct" in skip_criteria
    assert "max_price_delta_rel_p95_pct" in skip_criteria
    assert "max_ts_delta_ms_p95" in skip_criteria


@pytest.mark.unit
def test_evaluate_gate_inconclusive_reason_mentions_sample_counts():
    summary = _make_summary(total=5, comparable=3)
    gate = evaluate_gate(summary, GateThresholds())
    assert "3" in gate["gate_reason"] or "comparable" in gate["gate_reason"]


# ─── evaluate_gate: FAIL ──────────────────────────────────────────────────────


@pytest.mark.unit
def test_evaluate_gate_fail_missing_shadow_exceeds_threshold():
    """missing_shadow_pct > max_missing_shadow_pct → FAIL."""
    # 3/20 = 15 % > 5 % default
    summary = _make_summary(total=20, comparable=17, missing_shadow=3)
    gate = evaluate_gate(summary, GateThresholds())
    assert gate["gate_status"] == "FAIL"
    failed = [c["criterion"] for c in gate["checks"] if c["result"] == "FAIL"]
    assert "max_missing_shadow_pct" in failed


@pytest.mark.unit
def test_evaluate_gate_fail_missing_shadow_even_with_few_samples():
    """Missing shadow FAIL is evaluated before the min_comparable_samples check."""
    # Only 3 total samples, all shadow absent → FAIL (not INCONCLUSIVE)
    summary = _make_summary(total=3, comparable=0, missing_shadow=3)
    gate = evaluate_gate(summary, GateThresholds())
    assert gate["gate_status"] == "FAIL"


@pytest.mark.unit
def test_evaluate_gate_fail_stale_shadow_exceeds_threshold():
    """stale_shadow / comparable > max_stale_shadow_pct → FAIL."""
    # 4/20 = 20 % > 5 % default
    summary = _make_summary(total=20, comparable=20, stale_shadow=4)
    gate = evaluate_gate(summary, GateThresholds())
    assert gate["gate_status"] == "FAIL"
    failed = [c["criterion"] for c in gate["checks"] if c["result"] == "FAIL"]
    assert "max_stale_shadow_pct" in failed


@pytest.mark.unit
def test_evaluate_gate_fail_price_delta_rel_p95_exceeded():
    """price_delta_rel_pct p95 > max → FAIL."""
    summary = _make_summary(
        total=20,
        comparable=20,
        price_delta_rel_pct_p95=0.06,  # > 0.05 default
        price_delta_rel_pct_max=0.06,
    )
    gate = evaluate_gate(summary, GateThresholds())
    assert gate["gate_status"] == "FAIL"
    failed = [c["criterion"] for c in gate["checks"] if c["result"] == "FAIL"]
    assert "max_price_delta_rel_p95_pct" in failed


@pytest.mark.unit
def test_evaluate_gate_fail_price_delta_rel_max_exceeded():
    """price_delta_rel_pct max > max_price_delta_rel_max_pct → FAIL."""
    # p95 passes but max exceeds the hard limit
    summary = _make_summary(
        total=20,
        comparable=20,
        price_delta_rel_pct_p95=0.04,  # PASS
        price_delta_rel_pct_max=0.11,  # > 0.10 default → FAIL
    )
    gate = evaluate_gate(summary, GateThresholds())
    assert gate["gate_status"] == "FAIL"
    failed = [c["criterion"] for c in gate["checks"] if c["result"] == "FAIL"]
    assert "max_price_delta_rel_max_pct" in failed


@pytest.mark.unit
def test_evaluate_gate_fail_ts_delta_p95_exceeded():
    """ts_delta_ms p95 > max_ts_delta_ms_p95 → FAIL."""
    summary = _make_summary(
        total=20,
        comparable=20,
        ts_delta_ms_p95=12_000,  # > 10_000 default
    )
    gate = evaluate_gate(summary, GateThresholds())
    assert gate["gate_status"] == "FAIL"
    failed = [c["criterion"] for c in gate["checks"] if c["result"] == "FAIL"]
    assert "max_ts_delta_ms_p95" in failed


@pytest.mark.unit
def test_evaluate_gate_reports_all_failing_criteria_at_once():
    """Multiple failures must all appear in the checks list — no short-circuit."""
    summary = _make_summary(
        total=20,
        comparable=20,
        stale_shadow=8,  # 40 % > 5 %
        price_delta_rel_pct_p95=0.5,  # >> 0.05 %
        ts_delta_ms_p95=30_000,  # > 10 000 ms
    )
    gate = evaluate_gate(summary, GateThresholds())
    assert gate["gate_status"] == "FAIL"
    failed = [c["criterion"] for c in gate["checks"] if c["result"] == "FAIL"]
    assert len(failed) >= 3


# ─── evaluate_gate_smoke: live_write_smoke mode ───────────────────────────────


@pytest.mark.unit
def test_evaluate_gate_smoke_pass_live_key_present_and_fresh():
    """All live samples present and fresh → PASS."""
    summary = _make_smoke_summary(
        total=20, missing_live=0, missing_shadow=20, stale_live_total=0
    )
    gate = evaluate_gate_smoke(summary, LiveWriteSmokeThresholds())
    assert gate["gate_status"] == "PASS"


@pytest.mark.unit
def test_evaluate_gate_smoke_shadow_missing_not_a_fail():
    """All shadow keys absent → NOT a FAIL in live_write_smoke mode."""
    summary = _make_smoke_summary(
        total=20, missing_live=0, missing_shadow=20, stale_live_total=0
    )
    gate = evaluate_gate_smoke(summary, LiveWriteSmokeThresholds())
    # Must not be FAIL because of missing shadow
    assert gate["gate_status"] != "FAIL"
    # shadow absence must be annotated INFO, not FAIL
    shadow_checks = [c for c in gate["checks"] if "shadow" in c["criterion"]]
    assert all(c["result"] == "INFO" for c in shadow_checks)


@pytest.mark.unit
def test_evaluate_gate_smoke_shadow_missing_is_info():
    """missing_shadow_expected criterion has result INFO."""
    summary = _make_smoke_summary(total=20, missing_shadow=20)
    gate = evaluate_gate_smoke(summary, LiveWriteSmokeThresholds())
    info_checks = [c for c in gate["checks"] if c["result"] == "INFO"]
    criteria = {c["criterion"] for c in info_checks}
    assert "missing_shadow_expected" in criteria


@pytest.mark.unit
def test_evaluate_gate_smoke_fail_live_key_missing():
    """Too many live keys absent → FAIL."""
    # 3/20 = 15 % > 5 % default
    summary = _make_smoke_summary(total=20, missing_live=3, missing_shadow=20)
    gate = evaluate_gate_smoke(summary, LiveWriteSmokeThresholds())
    assert gate["gate_status"] == "FAIL"
    failed = [c["criterion"] for c in gate["checks"] if c["result"] == "FAIL"]
    assert "max_missing_live_pct" in failed


@pytest.mark.unit
def test_evaluate_gate_smoke_fail_live_key_stale():
    """Too many live keys stale → FAIL."""
    # 4/20 = 20 % > 5 % default
    summary = _make_smoke_summary(
        total=20, missing_live=0, missing_shadow=20, stale_live_total=4
    )
    gate = evaluate_gate_smoke(summary, LiveWriteSmokeThresholds())
    assert gate["gate_status"] == "FAIL"
    failed = [c["criterion"] for c in gate["checks"] if c["result"] == "FAIL"]
    assert "max_stale_live_pct" in failed


@pytest.mark.unit
def test_evaluate_gate_smoke_inconclusive_too_few_live_samples():
    """Not enough live samples → INCONCLUSIVE (not FAIL).

    Scenario: only 5 total samples collected, all live present (C1 passes),
    but min_live_samples=20 not yet reached → INCONCLUSIVE.
    """
    summary = _make_smoke_summary(total=5, missing_live=0, missing_shadow=5)
    gate = evaluate_gate_smoke(summary, LiveWriteSmokeThresholds())
    assert gate["gate_status"] == "INCONCLUSIVE"


@pytest.mark.unit
def test_evaluate_gate_smoke_inconclusive_skips_stale_check():
    """Stale check is SKIP when not enough live samples."""
    summary = _make_smoke_summary(total=5, missing_live=4, missing_shadow=5)
    gate = evaluate_gate_smoke(summary, LiveWriteSmokeThresholds())
    skip_checks = {c["criterion"] for c in gate["checks"] if c["result"] == "SKIP"}
    assert "max_stale_live_pct" in skip_checks


@pytest.mark.unit
def test_evaluate_gate_smoke_info_does_not_affect_pass():
    """INFO results are excluded from gate status determination — PASS unaffected."""
    summary = _make_smoke_summary(total=20, missing_shadow=20)
    gate = evaluate_gate_smoke(summary, LiveWriteSmokeThresholds())
    # Even though shadow is always missing (INFO), gate should PASS
    assert gate["gate_status"] == "PASS"
    # reason must mention criteria satisfied, not shadow
    assert "criteria satisfied" in gate["gate_reason"]


@pytest.mark.unit
def test_evaluate_gate_smoke_thresholds_in_result():
    """Thresholds must be reproduced in the gate result."""
    t = LiveWriteSmokeThresholds(min_live_samples=10, max_missing_live_pct=0.10)
    summary = _make_smoke_summary(total=10)
    gate = evaluate_gate_smoke(summary, t)
    assert gate["thresholds"]["min_live_samples"] == 10
    assert gate["thresholds"]["max_missing_live_pct"] == 0.10


@pytest.mark.unit
def test_evaluate_gate_smoke_checks_contain_threshold_and_measured():
    """All non-INFO check records must have threshold and measured."""
    summary = _make_smoke_summary(total=20)
    gate = evaluate_gate_smoke(summary, LiveWriteSmokeThresholds())
    for chk in gate["checks"]:
        assert "threshold" in chk
        assert "measured" in chk
        assert "result" in chk


# ─── build_report (updated for gate schema v1.1) ──────────────────────────────


@pytest.mark.unit
def test_build_report_schema_version():
    samples = [compare_snapshot(_live(), _shadow(), _NOW_MS)]
    summary = summarize(samples)
    report = build_report(
        "BTCUSDT",
        samples,
        summary,
        "2026-03-18T00:00:00+00:00",
        GateThresholds(min_comparable_samples=1),
    )
    assert report["schema_version"] == SCHEMA_VERSION
    assert report["symbol"] == "BTCUSDT"


@pytest.mark.unit
def test_build_report_default_mode_is_shadow_compare():
    """build_report without mode kwarg defaults to shadow_compare."""
    samples = [compare_snapshot(_live(), _shadow(), _NOW_MS)]
    summary = summarize(samples)
    report = build_report(
        "BTCUSDT",
        samples,
        summary,
        "2026-03-18T00:00:00+00:00",
        GateThresholds(min_comparable_samples=1),
    )
    assert report["mode"] == MODE_SHADOW_COMPARE


@pytest.mark.unit
def test_build_report_overall_pass_when_criteria_satisfied():
    """With relaxed min_comparable_samples=1, a single good sample → PASS."""
    samples = [compare_snapshot(_live(), _shadow(), _NOW_MS)]
    summary = summarize(samples)
    report = build_report(
        "BTCUSDT",
        samples,
        summary,
        "2026-03-18T00:00:00+00:00",
        GateThresholds(min_comparable_samples=1),
    )
    assert report["overall"] == "PASS"


@pytest.mark.unit
def test_build_report_overall_fail_when_all_shadow_missing():
    """3/3 shadow keys absent → missing_shadow_pct=1.0 > 0.05 → FAIL."""
    samples = [compare_snapshot(_live(), None, _NOW_MS)] * 3
    summary = summarize(samples)
    report = build_report(
        "BTCUSDT",
        samples,
        summary,
        "2026-03-18T00:00:00+00:00",
    )
    assert report["overall"] == "FAIL"
    assert "max_missing_shadow_pct" in report["overall_reason"]


@pytest.mark.unit
def test_build_report_overall_inconclusive_when_all_live_missing():
    """Live absent → 0 comparable; shadow_missing=0 → C1 passes; INCONCLUSIVE."""
    samples = [compare_snapshot(None, _shadow(), _NOW_MS)] * 3
    summary = summarize(samples)
    report = build_report("BTCUSDT", samples, summary, "2026-03-18T00:00:00+00:00")
    assert report["overall"] == "INCONCLUSIVE"


@pytest.mark.unit
def test_build_report_overall_inconclusive_when_no_comparable_but_shadow_ok():
    """1 live-miss + 1 shadow-miss, but tolerated → INCONCLUSIVE (not FAIL)."""
    samples = [
        compare_snapshot(None, _shadow(), _NOW_MS),
        compare_snapshot(_live(), None, _NOW_MS),
    ]
    summary = summarize(samples)
    # Allow up to 80 % missing shadow so C1 passes; comparable=0 < 20 → INCONCLUSIVE
    report = build_report(
        "BTCUSDT",
        samples,
        summary,
        "2026-03-18T00:00:00+00:00",
        GateThresholds(max_missing_shadow_pct=0.8),
    )
    assert report["overall"] == "INCONCLUSIVE"


@pytest.mark.unit
def test_build_report_includes_gate_block():
    """Report must include a 'gate' key with checks and thresholds."""
    samples = [compare_snapshot(_live(), _shadow(), _NOW_MS)]
    summary = summarize(samples)
    report = build_report(
        "BTCUSDT",
        samples,
        summary,
        "2026-03-18T00:00:00+00:00",
        GateThresholds(min_comparable_samples=1),
    )
    assert "gate" in report
    assert "checks" in report["gate"]
    assert "thresholds" in report["gate"]
    assert "gate_status" in report["gate"]


@pytest.mark.unit
def test_build_report_gate_thresholds_match_passed_thresholds():
    """Thresholds in the report must match what was passed to build_report."""
    t = GateThresholds(min_comparable_samples=5, max_ts_delta_ms_p95=3_000)
    samples = [compare_snapshot(_live(), _shadow(), _NOW_MS)]
    summary = summarize(samples)
    report = build_report("BTCUSDT", samples, summary, "2026-03-18T00:00:00+00:00", t)
    assert report["gate"]["thresholds"]["min_comparable_samples"] == 5
    assert report["gate"]["thresholds"]["max_ts_delta_ms_p95"] == 3_000


@pytest.mark.unit
def test_build_report_contains_samples_list():
    samples = [compare_snapshot(_live(), _shadow(), _NOW_MS)]
    summary = summarize(samples)
    report = build_report(
        "BTCUSDT",
        samples,
        summary,
        "2026-03-18T00:00:00+00:00",
        GateThresholds(min_comparable_samples=1),
    )
    assert len(report["samples"]) == 1
    assert report["samples"][0]["ts_sample_ms"] == _NOW_MS


@pytest.mark.unit
def test_build_report_is_json_serializable():
    samples = [compare_snapshot(_live(), _shadow(), _NOW_MS)]
    summary = summarize(samples)
    report = build_report("BTCUSDT", samples, summary, "2026-03-18T00:00:00+00:00")
    # Must not raise
    json.dumps(report)


# ─── build_report: live_write_smoke mode ──────────────────────────────────────


@pytest.mark.unit
def test_build_report_smoke_mode_field_set():
    """Report produced with mode=live_write_smoke includes mode in output."""
    samples = [compare_snapshot(_live(), None, _NOW_MS)] * 20
    summary = summarize(samples)
    report = build_report(
        "BTCUSDT",
        samples,
        summary,
        "2026-03-18T00:00:00+00:00",
        LiveWriteSmokeThresholds(min_live_samples=20),
        mode=MODE_LIVE_WRITE_SMOKE,
    )
    assert report["mode"] == MODE_LIVE_WRITE_SMOKE


@pytest.mark.unit
def test_build_report_smoke_mode_pass_with_fresh_live_key():
    """smoke mode: all live present + fresh → PASS (shadow always absent = expected)."""
    fresh_ts = _NOW_MS - 1_000
    samples = [compare_snapshot(_live(ts_ms=fresh_ts), None, _NOW_MS)] * 20
    summary = summarize(samples)
    report = build_report(
        "BTCUSDT",
        samples,
        summary,
        "2026-03-18T00:00:00+00:00",
        LiveWriteSmokeThresholds(min_live_samples=20),
        mode=MODE_LIVE_WRITE_SMOKE,
    )
    assert report["overall"] == "PASS"


@pytest.mark.unit
def test_build_report_smoke_mode_shadow_missing_not_a_fail():
    """smoke mode: shadow always absent does NOT produce FAIL."""
    fresh_ts = _NOW_MS - 1_000
    samples = [compare_snapshot(_live(ts_ms=fresh_ts), None, _NOW_MS)] * 20
    summary = summarize(samples)
    report = build_report(
        "BTCUSDT",
        samples,
        summary,
        "2026-03-18T00:00:00+00:00",
        LiveWriteSmokeThresholds(min_live_samples=20),
        mode=MODE_LIVE_WRITE_SMOKE,
    )
    # All shadow missing → would be FAIL in shadow_compare, must NOT be here
    assert report["overall"] != "FAIL"
    # And not because of missing_shadow_pct
    failed = [c["criterion"] for c in report["gate"]["checks"] if c["result"] == "FAIL"]
    assert "max_missing_shadow_pct" not in failed


@pytest.mark.unit
def test_build_report_smoke_mode_fail_live_key_missing():
    """smoke mode: too many live keys absent → FAIL."""
    # 4/20 = 20 % > 5 % default
    stale_count = 0
    missing_live_count = 4
    live_samples = [
        compare_snapshot(_live(), None, _NOW_MS) for _ in range(20 - missing_live_count)
    ]
    dead_samples = [
        compare_snapshot(None, None, _NOW_MS) for _ in range(missing_live_count)
    ]
    samples = live_samples + dead_samples
    summary = summarize(samples)
    report = build_report(
        "BTCUSDT",
        samples,
        summary,
        "2026-03-18T00:00:00+00:00",
        LiveWriteSmokeThresholds(),
        mode=MODE_LIVE_WRITE_SMOKE,
    )
    assert report["overall"] == "FAIL"
    failed = [c["criterion"] for c in report["gate"]["checks"] if c["result"] == "FAIL"]
    assert "max_missing_live_pct" in failed


@pytest.mark.unit
def test_build_report_smoke_mode_fail_stale_live_key():
    """smoke mode: too many stale live keys → FAIL."""
    old_ts = _NOW_MS - STALE_THRESHOLD_MS - 1
    fresh_ts = _NOW_MS - 1_000
    # 4 stale out of 20 → 20 % > 5 %
    samples = [compare_snapshot(_live(ts_ms=old_ts), None, _NOW_MS)] * 4 + [
        compare_snapshot(_live(ts_ms=fresh_ts), None, _NOW_MS)
    ] * 16
    summary = summarize(samples)
    report = build_report(
        "BTCUSDT",
        samples,
        summary,
        "2026-03-18T00:00:00+00:00",
        LiveWriteSmokeThresholds(min_live_samples=20),
        mode=MODE_LIVE_WRITE_SMOKE,
    )
    assert report["overall"] == "FAIL"
    failed = [c["criterion"] for c in report["gate"]["checks"] if c["result"] == "FAIL"]
    assert "max_stale_live_pct" in failed


@pytest.mark.unit
def test_build_report_smoke_mode_uses_smoke_thresholds_not_shadow():
    """smoke mode with LiveWriteSmokeThresholds — no shadow criteria in checks."""
    samples = [compare_snapshot(_live(), None, _NOW_MS)] * 20
    summary = summarize(samples)
    report = build_report(
        "BTCUSDT",
        samples,
        summary,
        "2026-03-18T00:00:00+00:00",
        LiveWriteSmokeThresholds(min_live_samples=20),
        mode=MODE_LIVE_WRITE_SMOKE,
    )
    criteria = {c["criterion"] for c in report["gate"]["checks"]}
    # Shadow compare criteria must NOT appear
    assert "max_missing_shadow_pct" not in criteria
    assert "max_price_delta_rel_p95_pct" not in criteria
    # Smoke criteria must appear
    assert "max_missing_live_pct" in criteria
    assert "max_stale_live_pct" in criteria


@pytest.mark.unit
def test_build_report_smoke_mode_is_json_serializable():
    samples = [compare_snapshot(_live(), None, _NOW_MS)] * 5
    summary = summarize(samples)
    report = build_report(
        "BTCUSDT",
        samples,
        summary,
        "2026-03-18T00:00:00+00:00",
        LiveWriteSmokeThresholds(min_live_samples=5),
        mode=MODE_LIVE_WRITE_SMOKE,
    )
    json.dumps(report)  # must not raise


# ─── collect_samples ──────────────────────────────────────────────────────────


@pytest.mark.unit
def test_collect_samples_reads_both_keys():
    mock_redis = MagicMock()
    mock_redis.get.side_effect = lambda key: (
        json.dumps(_live()).encode()
        if key.startswith("market_price:")
        else (
            json.dumps(_shadow()).encode()
            if key.startswith("market_price_v3:")
            else None
        )
    )
    with patch("services.market.tools.v3_compare.time.sleep"):
        samples = collect_samples(mock_redis, "BTCUSDT", 3, 1.0)

    assert len(samples) == 3
    assert all(s["comparable"] for s in samples)


@pytest.mark.unit
def test_collect_samples_handles_missing_live_key():
    mock_redis = MagicMock()
    mock_redis.get.side_effect = lambda key: (
        None if key.startswith("market_price:") else json.dumps(_shadow()).encode()
    )
    with patch("services.market.tools.v3_compare.time.sleep"):
        samples = collect_samples(mock_redis, "BTCUSDT", 2, 1.0)

    assert all(s["live_missing"] for s in samples)
    assert all(not s["comparable"] for s in samples)


@pytest.mark.unit
def test_collect_samples_handles_missing_shadow_key():
    """In live_write_smoke mode the shadow key is absent — collect_samples must handle gracefully."""
    mock_redis = MagicMock()
    mock_redis.get.side_effect = lambda key: (
        json.dumps(_live()).encode() if key.startswith("market_price:") else None
    )
    with patch("services.market.tools.v3_compare.time.sleep"):
        samples = collect_samples(mock_redis, "BTCUSDT", 3, 1.0)

    assert len(samples) == 3
    assert all(s["shadow_missing"] for s in samples)
    assert all(not s["comparable"] for s in samples)
    # live_age_ms must be populated (live key was present)
    assert all("live_age_ms" in s for s in samples)


@pytest.mark.unit
def test_collect_samples_handles_corrupt_json():
    mock_redis = MagicMock()
    mock_redis.get.return_value = b"not-valid-json{"
    with patch("services.market.tools.v3_compare.time.sleep"):
        samples = collect_samples(mock_redis, "BTCUSDT", 1, 1.0)

    # Both keys corrupt → both missing → not comparable
    assert samples[0]["comparable"] is False


@pytest.mark.unit
def test_collect_samples_sleep_called_between_samples():
    mock_redis = MagicMock()
    mock_redis.get.return_value = json.dumps(_live()).encode()
    with patch("services.market.tools.v3_compare.time.sleep") as mock_sleep:
        collect_samples(mock_redis, "BTCUSDT", 3, 2.5)

    # sleep called n-1 times
    assert mock_sleep.call_count == 2
    mock_sleep.assert_called_with(2.5)


@pytest.mark.unit
def test_collect_samples_no_sleep_for_single_sample():
    mock_redis = MagicMock()
    mock_redis.get.return_value = json.dumps(_live()).encode()
    with patch("services.market.tools.v3_compare.time.sleep") as mock_sleep:
        collect_samples(mock_redis, "BTCUSDT", 1, 5.0)

    mock_sleep.assert_not_called()
