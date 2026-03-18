#!/usr/bin/env python3
"""Read-only compare + Evidence Gate for market_price (live) vs market_price_v3 (shadow).

Supports two modes (``--mode``):

  shadow_compare   (default)
      Reads both Redis keys, records N samples, computes price/timestamp delta
      metrics, evaluates explicit gate criteria, and writes a JSON evidence
      artefact.  Shadow key is *required*; a missing shadow key is a FAIL.

  live_write_smoke
      Used after MARKET_V3_LIVE_WRITE=true promotion.  V3 now writes directly
      to ``market_price:{symbol}``; the shadow key intentionally does not exist.
      Gate checks live-key health only (presence + freshness).
      A missing shadow key is *expected* and is annotated INFO — never FAIL.

Usage (standalone):
    python -m services.market.tools.v3_compare \\
        --symbol BTCUSDT --samples 20 --interval 5 \\
        --out reports/v3_compare_BTCUSDT.json

    python -m services.market.tools.v3_compare \\
        --mode live_write_smoke --symbol BTCUSDT --samples 20 --interval 5 \\
        --out reports/v3_smoke_BTCUSDT.json

Gate thresholds — shadow_compare (all override via CLI flags):
    --min-comparable-samples      INT    default: 20
    --max-missing-shadow-pct      FLOAT  default: 0.05   (5 %)
    --max-stale-shadow-pct        FLOAT  default: 0.05   (5 %)
    --max-price-delta-rel-p95-pct FLOAT  default: 0.05   (0.05 %)
    --max-price-delta-rel-max-pct FLOAT  default: 0.10   (0.10 %)
    --max-ts-delta-ms-p95         INT    default: 10000  (10 s)

Gate thresholds — live_write_smoke (all override via CLI flags):
    --min-live-samples            INT    default: 20
    --max-missing-live-pct        FLOAT  default: 0.05   (5 %)
    --max-stale-live-pct          FLOAT  default: 0.05   (5 %)

Environment variables (Redis connection):
    REDIS_HOST      hostname   (default: localhost)
    REDIS_PORT      port       (default: 6379)
    REDIS_PASSWORD  password   (default: empty)

Exit codes:
    0 — gate PASS
    1 — gate FAIL, INCONCLUSIVE, or runtime error

Design:
- Pure functions (compare_snapshot, summarize, evaluate_gate,
  evaluate_gate_smoke, build_report) — no I/O
- collect_samples() accepts an injected redis client → fully mockable in tests
- No writes to any Redis key; live-path is never touched
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ─── Constants ────────────────────────────────────────────────────────────────

SCHEMA_VERSION = "1.1"
LIVE_KEY_PREFIX = "market_price"
SHADOW_KEY_PREFIX = "market_price_v3"

# Keys are stale when their age exceeds the 30 s TTL used by service.py.
STALE_THRESHOLD_MS: int = 30_000  # 30 seconds

# ─── Mode constants ────────────────────────────────────────────────────────────

MODE_SHADOW_COMPARE = "shadow_compare"
MODE_LIVE_WRITE_SMOKE = "live_write_smoke"
VALID_MODES = (MODE_SHADOW_COMPARE, MODE_LIVE_WRITE_SMOKE)


# ─── Gate thresholds ──────────────────────────────────────────────────────────


@dataclasses.dataclass
class GateThresholds:
    """Explicit, named gate criteria for V3 shadow promotion readiness.

    All defaults are intentionally conservative and documented below.
    Override via CLI flags or direct instantiation.

    Rationale for defaults (derived from first evidence run 2026-03-18):
      max_missing_shadow_pct       5 % — tolerate brief Redis key eviction / restart lag
      max_stale_shadow_pct         5 % — tolerate at most 1 stale entry per 20 samples
      max_price_delta_rel_p95_pct  0.05 % — first run p95 was ~0 %; 0.05 % ≈ 16x headroom
      max_price_delta_rel_max_pct  0.10 % — first run max was 0.003 %; 0.10 % ≈ 30x headroom
      max_ts_delta_ms_p95          10 000 ms — first run max was 2976 ms; 10 s ≈ 3x headroom
    """

    # Minimum number of comparable samples before a PASS/FAIL decision is made.
    # Below this the gate is INCONCLUSIVE — not enough data to trust the stats.
    min_comparable_samples: int = 20

    # Maximum fraction (0–1) of total samples where the shadow key is absent.
    # Exceeding this is a hard FAIL regardless of sample count.
    max_missing_shadow_pct: float = 0.05

    # Maximum fraction (0–1) of *comparable* samples where shadow entry is stale
    # (age > STALE_THRESHOLD_MS = 30 s).
    max_stale_shadow_pct: float = 0.05

    # Maximum p95 of relative price delta (percent).
    max_price_delta_rel_p95_pct: float = 0.05

    # Hard maximum of relative price delta (percent).
    # A single outlier above this causes an immediate FAIL.
    max_price_delta_rel_max_pct: float = 0.10

    # Maximum p95 of ts_delta_ms (milliseconds).
    max_ts_delta_ms_p95: int = 10_000

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclasses.dataclass
class LiveWriteSmokeThresholds:
    """Gate criteria for live_write_smoke mode (MARKET_V3_LIVE_WRITE=true).

    In this mode V3 writes directly to market_price:{symbol}.
    The shadow key market_price_v3:{symbol} intentionally does not exist.
    Gate checks live-key health only.

    Criteria:
      max_missing_live_pct  — fraction of samples where the live key is absent
      min_live_samples      — minimum live-key-present samples before PASS/FAIL
      max_stale_live_pct    — fraction of live-present samples where key is stale
    """

    min_live_samples: int = 20
    max_missing_live_pct: float = 0.05
    max_stale_live_pct: float = 0.05

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


# ─── Pure computation layer ───────────────────────────────────────────────────


def compare_snapshot(
    live: dict[str, Any] | None,
    shadow: dict[str, Any] | None,
    now_ms: int,
) -> dict[str, Any]:
    """Compare one snapshot of live vs V3 shadow Redis entries.

    Both *live* and *shadow* are already-decoded dicts (or None when the key
    is absent from Redis).  *now_ms* is the epoch-millisecond timestamp of
    the sample, used to compute freshness.

    Live freshness (``live_age_ms``, ``live_stale``) is computed whenever
    the live key is present, regardless of shadow key presence.  This allows
    live_write_smoke mode to evaluate live key health even when shadow is
    intentionally absent.

    Returns a flat dict with:
      comparable          — True only when both entries are present and parseable
      live_missing        — True when the live key was absent
      shadow_missing      — True when the shadow key was absent
      live_age_ms         — now_ms - live_ts_ms           (int, when live present)
      live_stale          — live_age_ms > STALE_THRESHOLD_MS (when live present)
      price_delta_abs     — |live_price - shadow_price|  (float, comparable only)
      price_delta_rel_pct — delta / live_price * 100     (float, comparable only)
      ts_delta_ms         — |live_ts_ms - shadow_ts_ms|  (int, comparable only)
      shadow_age_ms       — now_ms - shadow_ts_ms         (int, comparable only)
      shadow_stale        — shadow_age_ms > STALE_THRESHOLD_MS (comparable only)
    """
    result: dict[str, Any] = {
        "ts_sample_ms": now_ms,
        "live_missing": live is None,
        "shadow_missing": shadow is None,
    }

    # Compute live freshness whenever live is present — shadow-independent.
    # Needed by live_write_smoke gate even when shadow key is absent.
    live_ts: int | None = None
    if live is not None:
        live_ts = live.get("ts_ms")
        live_age_ms: int | None = now_ms - int(live_ts) if live_ts is not None else None
        result["live_age_ms"] = live_age_ms
        result["live_stale"] = (
            live_age_ms > STALE_THRESHOLD_MS if live_age_ms is not None else None
        )

    if live is None or shadow is None:
        result["comparable"] = False
        return result

    try:
        live_price = float(live["price"])
        shadow_price = float(shadow["price"])
    except (KeyError, ValueError, TypeError) as exc:
        result["comparable"] = False
        result["error"] = f"price parse error: {exc}"
        return result

    price_delta_abs = abs(live_price - shadow_price)
    price_delta_rel_pct: float | None = (
        round(price_delta_abs / live_price * 100, 8) if live_price != 0.0 else None
    )

    shadow_ts: int | None = shadow.get("ts_ms")

    ts_delta_ms: int | None = (
        abs(int(shadow_ts) - int(live_ts))
        if live_ts is not None and shadow_ts is not None
        else None
    )
    shadow_age_ms: int | None = (
        now_ms - int(shadow_ts) if shadow_ts is not None else None
    )

    result.update(
        {
            "comparable": True,
            "live_price": live["price"],
            "shadow_price": shadow["price"],
            "price_delta_abs": price_delta_abs,
            "price_delta_rel_pct": price_delta_rel_pct,
            "live_ts_ms": live_ts,
            "shadow_ts_ms": shadow_ts,
            "ts_delta_ms": ts_delta_ms,
            "shadow_age_ms": shadow_age_ms,
            "shadow_stale": (
                shadow_age_ms > STALE_THRESHOLD_MS
                if shadow_age_ms is not None
                else None
            ),
        }
    )
    return result


def _numeric_stats(values: list[float]) -> dict[str, float | None]:
    """Return min/max/mean/p95 for a list of floats. Returns None for all when empty."""
    if not values:
        return {"min": None, "max": None, "mean": None, "p95": None}
    sorted_v = sorted(values)
    p95_idx = max(0, int(len(sorted_v) * 0.95) - 1)
    return {
        "min": sorted_v[0],
        "max": sorted_v[-1],
        "mean": sum(values) / len(values),
        "p95": sorted_v[p95_idx],
    }


def summarize(samples: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate sample metrics into a summary dict.

    Counts missing/stale occurrences and computes distribution stats for
    price delta, relative price delta, and ts_ms delta across all
    *comparable* samples.

    Additional fields for live_write_smoke mode:
      live_present_count      — samples where live key was present (shadow-independent)
      stale_live_total_count  — stale live keys across ALL live-present samples
                                (not just comparable; shadow key may be absent)
    """
    comparable = [s for s in samples if s.get("comparable") is True]
    live_present = [s for s in samples if not s.get("live_missing")]

    price_deltas = [s["price_delta_abs"] for s in comparable]
    rel_deltas = [
        s["price_delta_rel_pct"]
        for s in comparable
        if s.get("price_delta_rel_pct") is not None
    ]
    ts_deltas = [
        s["ts_delta_ms"] for s in comparable if s.get("ts_delta_ms") is not None
    ]
    live_ages = [
        s["live_age_ms"] for s in comparable if s.get("live_age_ms") is not None
    ]
    shadow_ages = [
        s["shadow_age_ms"] for s in comparable if s.get("shadow_age_ms") is not None
    ]

    return {
        "total_samples": len(samples),
        "comparable_samples": len(comparable),
        "live_present_count": len(live_present),
        "missing_live_count": sum(1 for s in samples if s.get("live_missing")),
        "missing_shadow_count": sum(1 for s in samples if s.get("shadow_missing")),
        "stale_live_count": sum(1 for s in comparable if s.get("live_stale") is True),
        "stale_live_total_count": sum(
            1 for s in live_present if s.get("live_stale") is True
        ),
        "stale_shadow_count": sum(
            1 for s in comparable if s.get("shadow_stale") is True
        ),
        "price_delta_abs": _numeric_stats(price_deltas),
        "price_delta_rel_pct": _numeric_stats(rel_deltas),
        "ts_delta_ms": _numeric_stats(ts_deltas),
        "live_age_ms": _numeric_stats(live_ages),
        "shadow_age_ms": _numeric_stats(shadow_ages),
    }


# ─── Gate evaluation — shadow_compare ─────────────────────────────────────────


def _chk(
    criterion: str,
    threshold: Any,
    measured: Any,
    result: str,
    note: str = "",
) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "criterion": criterion,
        "threshold": threshold,
        "measured": measured,
        "result": result,
    }
    if note:
        entry["note"] = note
    return entry


def evaluate_gate(
    summary: dict[str, Any],
    thresholds: GateThresholds,
) -> dict[str, Any]:
    """Evaluate gate criteria against a completed summary (shadow_compare mode).

    Evaluation order (determines overall status priority):
      1. max_missing_shadow_pct  — FAIL even when comparable count is low
      2. min_comparable_samples  — INCONCLUSIVE when not met (and no FAIL above)
      3. max_stale_shadow_pct    — FAIL  (only when enough comparable data)
      4. max_price_delta_rel_p95_pct  — FAIL
      5. max_price_delta_rel_max_pct  — FAIL
      6. max_ts_delta_ms_p95     — FAIL

    Returns a dict with:
      gate_status   — PASS / FAIL / INCONCLUSIVE
      gate_reason   — human-readable summary
      thresholds    — copy of the applied thresholds (for full transparency)
      checks        — list of individual check records (criterion/threshold/measured/result)
    """
    total = summary["total_samples"]
    comparable = summary["comparable_samples"]
    checks: list[dict[str, Any]] = []

    # ── C1: Missing shadow fraction ───────────────────────────────────────────
    # Evaluated first and unconditionally; a systematically absent shadow key
    # is always a hard FAIL regardless of how many samples we have.
    msf = summary["missing_shadow_count"] / total if total > 0 else 0.0
    c1_pass = msf <= thresholds.max_missing_shadow_pct
    checks.append(
        _chk(
            "max_missing_shadow_pct",
            thresholds.max_missing_shadow_pct,
            round(msf, 6),
            "PASS" if c1_pass else "FAIL",
        )
    )

    # ── C2: Minimum comparable samples ───────────────────────────────────────
    # INCONCLUSIVE (not FAIL) — insufficient data is a data-collection problem,
    # not a correctness problem.
    enough_data = comparable >= thresholds.min_comparable_samples
    checks.append(
        _chk(
            "min_comparable_samples",
            thresholds.min_comparable_samples,
            comparable,
            "PASS" if enough_data else "INCONCLUSIVE",
            note="" if enough_data else "below minimum — stats not reliable",
        )
    )

    if not enough_data:
        # Skip stats-based checks; they're not meaningful with too few samples.
        for crit in (
            "max_stale_shadow_pct",
            "max_price_delta_rel_p95_pct",
            "max_price_delta_rel_max_pct",
            "max_ts_delta_ms_p95",
        ):
            checks.append(
                _chk(crit, None, None, "SKIP", note="insufficient comparable samples")
            )
    else:
        # ── C3: Stale shadow fraction ─────────────────────────────────────────
        ssf = summary["stale_shadow_count"] / comparable
        checks.append(
            _chk(
                "max_stale_shadow_pct",
                thresholds.max_stale_shadow_pct,
                round(ssf, 6),
                "PASS" if ssf <= thresholds.max_stale_shadow_pct else "FAIL",
            )
        )

        # ── C4: Price delta rel p95 ───────────────────────────────────────────
        rel_p95 = summary["price_delta_rel_pct"]["p95"]
        if rel_p95 is None:
            checks.append(
                _chk(
                    "max_price_delta_rel_p95_pct",
                    thresholds.max_price_delta_rel_p95_pct,
                    None,
                    "FAIL",
                    note="p95 unavailable (all live prices zero?)",
                )
            )
        else:
            checks.append(
                _chk(
                    "max_price_delta_rel_p95_pct",
                    thresholds.max_price_delta_rel_p95_pct,
                    round(rel_p95, 8),
                    (
                        "PASS"
                        if rel_p95 <= thresholds.max_price_delta_rel_p95_pct
                        else "FAIL"
                    ),
                )
            )

        # ── C5: Price delta rel max ───────────────────────────────────────────
        rel_max = summary["price_delta_rel_pct"]["max"]
        if rel_max is None:
            checks.append(
                _chk(
                    "max_price_delta_rel_max_pct",
                    thresholds.max_price_delta_rel_max_pct,
                    None,
                    "FAIL",
                    note="max unavailable",
                )
            )
        else:
            checks.append(
                _chk(
                    "max_price_delta_rel_max_pct",
                    thresholds.max_price_delta_rel_max_pct,
                    round(rel_max, 8),
                    (
                        "PASS"
                        if rel_max <= thresholds.max_price_delta_rel_max_pct
                        else "FAIL"
                    ),
                )
            )

        # ── C6: ts_delta p95 ─────────────────────────────────────────────────
        ts_p95 = summary["ts_delta_ms"]["p95"]
        if ts_p95 is None:
            checks.append(
                _chk(
                    "max_ts_delta_ms_p95",
                    thresholds.max_ts_delta_ms_p95,
                    None,
                    "FAIL",
                    note="p95 unavailable",
                )
            )
        else:
            checks.append(
                _chk(
                    "max_ts_delta_ms_p95",
                    thresholds.max_ts_delta_ms_p95,
                    round(ts_p95, 1),
                    "PASS" if ts_p95 <= thresholds.max_ts_delta_ms_p95 else "FAIL",
                )
            )

    # ── Determine overall gate status ─────────────────────────────────────────
    results = {c["result"] for c in checks}
    if "FAIL" in results:
        failed_criteria = [c["criterion"] for c in checks if c["result"] == "FAIL"]
        gate_status = "FAIL"
        gate_reason = f"{len(failed_criteria)} criterion failed: {failed_criteria}"
    elif "INCONCLUSIVE" in results:
        gate_status = "INCONCLUSIVE"
        gate_reason = (
            f"insufficient data: "
            f"{comparable}/{thresholds.min_comparable_samples} comparable samples"
        )
    else:
        passed = sum(1 for c in checks if c["result"] == "PASS")
        gate_status = "PASS"
        gate_reason = f"all {passed} criteria satisfied"

    return {
        "gate_status": gate_status,
        "gate_reason": gate_reason,
        "thresholds": thresholds.to_dict(),
        "checks": checks,
    }


# ─── Gate evaluation — live_write_smoke ───────────────────────────────────────


def evaluate_gate_smoke(
    summary: dict[str, Any],
    thresholds: LiveWriteSmokeThresholds,
) -> dict[str, Any]:
    """Evaluate gate criteria for live_write_smoke mode.

    In live_write_smoke mode MARKET_V3_LIVE_WRITE=true: V3 writes directly to
    ``market_price:{symbol}``.  The shadow key ``market_price_v3:{symbol}``
    intentionally does not exist.  A missing shadow key is never a FAIL here.

    Evaluation order:
      INFO: missing_shadow_count   — annotated as expected; never FAIL
      C1:   max_missing_live_pct   — FAIL when live key systematically absent
      C2:   min_live_samples       — INCONCLUSIVE when not enough live data
      C3:   max_stale_live_pct     — FAIL when live key frequently stale

    Returns a dict with:
      gate_status   — PASS / FAIL / INCONCLUSIVE
      gate_reason   — human-readable summary
      thresholds    — copy of the applied thresholds
      checks        — list of individual check records
    """
    total = summary["total_samples"]
    # live_present_count is set by summarize(); fall back to derivation for
    # callers that pass a hand-built summary dict (e.g. unit tests).
    live_present = summary.get(
        "live_present_count",
        total - summary["missing_live_count"],
    )
    checks: list[dict[str, Any]] = []

    # ── INFO: Shadow key absence is expected ──────────────────────────────────
    # Explicit annotation so the report reader knows this is intentional.
    checks.append(
        _chk(
            "missing_shadow_expected",
            None,
            summary["missing_shadow_count"],
            "INFO",
            note=(
                "shadow key absent is EXPECTED in live_write_smoke mode "
                "(MARKET_V3_LIVE_WRITE=true)"
            ),
        )
    )

    # ── C1: Missing live fraction ─────────────────────────────────────────────
    mlp = summary["missing_live_count"] / total if total > 0 else 0.0
    c1_pass = mlp <= thresholds.max_missing_live_pct
    checks.append(
        _chk(
            "max_missing_live_pct",
            thresholds.max_missing_live_pct,
            round(mlp, 6),
            "PASS" if c1_pass else "FAIL",
        )
    )

    # ── C2: Minimum live samples ──────────────────────────────────────────────
    enough_data = live_present >= thresholds.min_live_samples
    checks.append(
        _chk(
            "min_live_samples",
            thresholds.min_live_samples,
            live_present,
            "PASS" if enough_data else "INCONCLUSIVE",
            note="" if enough_data else "below minimum — staleness stats not reliable",
        )
    )

    if not enough_data:
        checks.append(
            _chk(
                "max_stale_live_pct",
                None,
                None,
                "SKIP",
                note="insufficient live samples",
            )
        )
    else:
        # ── C3: Stale live fraction ───────────────────────────────────────────
        # Use stale_live_total_count (all live-present samples) rather than
        # stale_live_count (comparable-only) because in this mode there are no
        # comparable samples.
        stale_live = summary.get(
            "stale_live_total_count",
            summary.get("stale_live_count", 0),
        )
        slp = stale_live / live_present if live_present > 0 else 0.0
        checks.append(
            _chk(
                "max_stale_live_pct",
                thresholds.max_stale_live_pct,
                round(slp, 6),
                "PASS" if slp <= thresholds.max_stale_live_pct else "FAIL",
            )
        )

    # ── Determine overall gate status ─────────────────────────────────────────
    # INFO results are excluded from status determination.
    non_info = [c for c in checks if c["result"] != "INFO"]
    results = {c["result"] for c in non_info}
    if "FAIL" in results:
        failed_criteria = [c["criterion"] for c in non_info if c["result"] == "FAIL"]
        gate_status = "FAIL"
        gate_reason = f"{len(failed_criteria)} criterion failed: {failed_criteria}"
    elif "INCONCLUSIVE" in results:
        gate_status = "INCONCLUSIVE"
        gate_reason = (
            f"insufficient data: "
            f"{live_present}/{thresholds.min_live_samples} live samples"
        )
    else:
        passed = sum(1 for c in non_info if c["result"] == "PASS")
        gate_status = "PASS"
        gate_reason = (
            f"all {passed} criteria satisfied "
            f"(shadow key absence expected in live_write_smoke mode)"
        )

    return {
        "gate_status": gate_status,
        "gate_reason": gate_reason,
        "thresholds": thresholds.to_dict(),
        "checks": checks,
    }


def build_report(
    symbol: str,
    samples: list[dict[str, Any]],
    summary: dict[str, Any],
    generated_at: str,
    thresholds: GateThresholds | LiveWriteSmokeThresholds | None = None,
    mode: str = MODE_SHADOW_COMPARE,
) -> dict[str, Any]:
    """Wrap samples + summary + gate result into the canonical JSON evidence structure.

    *mode* selects the gate evaluation strategy:
      shadow_compare    — uses GateThresholds; shadow key required
      live_write_smoke  — uses LiveWriteSmokeThresholds; shadow key absence is expected

    *thresholds* defaults to the canonical defaults for the selected mode when None.
    The gate result is the authoritative source of the ``overall`` status.
    """
    if mode == MODE_LIVE_WRITE_SMOKE:
        t: GateThresholds | LiveWriteSmokeThresholds = (
            thresholds
            if isinstance(thresholds, LiveWriteSmokeThresholds)
            else LiveWriteSmokeThresholds()
        )
        gate = evaluate_gate_smoke(summary, t)  # type: ignore[arg-type]
    else:
        t = thresholds if isinstance(thresholds, GateThresholds) else GateThresholds()
        gate = evaluate_gate(summary, t)  # type: ignore[arg-type]

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at,
        "symbol": symbol,
        "mode": mode,
        "live_key_prefix": LIVE_KEY_PREFIX,
        "shadow_key_prefix": SHADOW_KEY_PREFIX,
        "stale_threshold_ms": STALE_THRESHOLD_MS,
        "overall": gate["gate_status"],
        "overall_reason": gate["gate_reason"],
        "gate": gate,
        "summary": summary,
        "samples": samples,
    }


# ─── Redis-dependent collection layer ─────────────────────────────────────────


def collect_samples(
    redis_client: Any,
    symbol: str,
    n: int,
    interval_s: float,
) -> list[dict[str, Any]]:
    """Collect *n* comparison snapshots at *interval_s* second intervals.

    *redis_client* must expose a `.get(key) -> bytes | None` interface.
    Never writes to Redis.
    """
    live_key = f"{LIVE_KEY_PREFIX}:{symbol}"
    shadow_key = f"{SHADOW_KEY_PREFIX}:{symbol}"
    samples: list[dict[str, Any]] = []

    for i in range(n):
        now_ms = int(time.time() * 1000)
        live_raw = redis_client.get(live_key)
        shadow_raw = redis_client.get(shadow_key)

        try:
            live = json.loads(live_raw) if live_raw is not None else None
        except (json.JSONDecodeError, TypeError):
            live = None

        try:
            shadow = json.loads(shadow_raw) if shadow_raw is not None else None
        except (json.JSONDecodeError, TypeError):
            shadow = None

        samples.append(compare_snapshot(live, shadow, now_ms))

        if i < n - 1:
            time.sleep(interval_s)

    return samples


# ─── CLI entry point ──────────────────────────────────────────────────────────


def _connect_redis() -> Any:
    import redis as redis_lib  # noqa: F401 — only imported when running as CLI

    host = os.getenv("REDIS_HOST", "localhost")
    port = int(os.getenv("REDIS_PORT", "6379"))
    password = os.getenv("REDIS_PASSWORD") or None
    client = redis_lib.Redis(
        host=host, port=port, password=password, decode_responses=True
    )
    client.ping()
    return client


def _print_gate_summary(gate: dict[str, Any], mode: str) -> None:
    """Print a human-readable gate summary to stderr."""
    status = gate["gate_status"]
    print(f"\n[v3_compare] Mode       : {mode}", file=sys.stderr)
    print(f"[v3_compare] Gate verdict: {status}", file=sys.stderr)
    print(f"             Reason     : {gate['gate_reason']}", file=sys.stderr)
    print("[v3_compare] Checks:", file=sys.stderr)
    for c in gate["checks"]:
        result = c["result"]
        crit = c["criterion"]
        thresh = c.get("threshold")
        measured = c.get("measured")
        note = c.get("note", "")
        suffix = f"  ({note})" if note else ""
        if result == "PASS":
            icon = "✓"
        elif result == "FAIL":
            icon = "✗"
        elif result == "INFO":
            icon = "ℹ"
        else:
            icon = "~"
        print(
            f"  {icon}  {crit:<35} threshold={thresh}  measured={measured}"
            f"  → {result}{suffix}",
            file=sys.stderr,
        )


def main() -> None:
    shadow_defaults = GateThresholds()
    smoke_defaults = LiveWriteSmokeThresholds()

    parser = argparse.ArgumentParser(
        description=(
            "Read-only Evidence Gate: market_price vs market_price_v3 "
            "(shadow_compare) or live key health smoke (live_write_smoke)"
        )
    )
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--samples", type=int, default=20)
    parser.add_argument("--interval", type=float, default=5.0)
    parser.add_argument("--out", type=str, default=None)
    parser.add_argument(
        "--mode",
        choices=VALID_MODES,
        default=MODE_SHADOW_COMPARE,
        help=(
            "shadow_compare: compare live vs shadow key (default). "
            "live_write_smoke: check live key health after MARKET_V3_LIVE_WRITE=true."
        ),
    )

    # Gate threshold overrides — shadow_compare mode
    g = parser.add_argument_group(
        "shadow_compare gate thresholds",
        "Override defaults; only used when --mode=shadow_compare",
    )
    g.add_argument(
        "--min-comparable-samples",
        type=int,
        default=shadow_defaults.min_comparable_samples,
        metavar="N",
    )
    g.add_argument(
        "--max-missing-shadow-pct",
        type=float,
        default=shadow_defaults.max_missing_shadow_pct,
        metavar="F",
    )
    g.add_argument(
        "--max-stale-shadow-pct",
        type=float,
        default=shadow_defaults.max_stale_shadow_pct,
        metavar="F",
    )
    g.add_argument(
        "--max-price-delta-rel-p95-pct",
        type=float,
        default=shadow_defaults.max_price_delta_rel_p95_pct,
        metavar="F",
    )
    g.add_argument(
        "--max-price-delta-rel-max-pct",
        type=float,
        default=shadow_defaults.max_price_delta_rel_max_pct,
        metavar="F",
    )
    g.add_argument(
        "--max-ts-delta-ms-p95",
        type=int,
        default=shadow_defaults.max_ts_delta_ms_p95,
        metavar="MS",
    )

    # Gate threshold overrides — live_write_smoke mode
    sg = parser.add_argument_group(
        "live_write_smoke gate thresholds",
        "Override defaults; only used when --mode=live_write_smoke",
    )
    sg.add_argument(
        "--min-live-samples",
        type=int,
        default=smoke_defaults.min_live_samples,
        metavar="N",
    )
    sg.add_argument(
        "--max-missing-live-pct",
        type=float,
        default=smoke_defaults.max_missing_live_pct,
        metavar="F",
    )
    sg.add_argument(
        "--max-stale-live-pct",
        type=float,
        default=smoke_defaults.max_stale_live_pct,
        metavar="F",
    )

    args = parser.parse_args()

    if args.mode == MODE_LIVE_WRITE_SMOKE:
        thresholds: GateThresholds | LiveWriteSmokeThresholds = (
            LiveWriteSmokeThresholds(
                min_live_samples=args.min_live_samples,
                max_missing_live_pct=args.max_missing_live_pct,
                max_stale_live_pct=args.max_stale_live_pct,
            )
        )
    else:
        thresholds = GateThresholds(
            min_comparable_samples=args.min_comparable_samples,
            max_missing_shadow_pct=args.max_missing_shadow_pct,
            max_stale_shadow_pct=args.max_stale_shadow_pct,
            max_price_delta_rel_p95_pct=args.max_price_delta_rel_p95_pct,
            max_price_delta_rel_max_pct=args.max_price_delta_rel_max_pct,
            max_ts_delta_ms_p95=args.max_ts_delta_ms_p95,
        )

    try:
        r = _connect_redis()
    except Exception as exc:  # noqa: BLE001
        print(f"[v3_compare] Redis connection failed: {exc}", file=sys.stderr)
        sys.exit(1)

    print(
        f"[v3_compare] Mode={args.mode} — Collecting {args.samples} samples "
        f"for {args.symbol} (interval={args.interval}s) …",
        file=sys.stderr,
    )
    samples = collect_samples(r, args.symbol, args.samples, args.interval)

    now_iso = datetime.now(tz=timezone.utc).isoformat()
    summary = summarize(samples)
    report = build_report(args.symbol, samples, summary, now_iso, thresholds, args.mode)

    report_json = json.dumps(report, indent=2)
    print(report_json)

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(report_json, encoding="utf-8")
        print(f"[v3_compare] Report written to {out_path}", file=sys.stderr)

    _print_gate_summary(report["gate"], args.mode)

    if report["overall"] != "PASS":
        sys.exit(1)


if __name__ == "__main__":
    main()
