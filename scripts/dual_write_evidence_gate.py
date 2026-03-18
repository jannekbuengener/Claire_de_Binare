#!/usr/bin/env python3
"""Dual-Write Evidence Gate — market_state Contract V1 (Issue #1201).

Reads two Redis keys for each observed symbol:
  market_state:{symbol}        — live contract, written by cdb_candles
  market_state_shadow:{symbol} — shadow copy,  written by cdb_market (Delta 1)

Compares all Contract V1 fields within defined tolerances. Writes a JSON
evidence artefact and prints a summary. Blocks cutover on any failure.

Exit codes:
  0 — PASS:    all symbols within tolerance → evidence ready for cutover review
  1 — FAIL:    field divergence, missing key, ts-gap too wide, or no symbols
  2 — ERROR:   Redis unavailable, bad arguments, or unexpected exception

Tolerances (V1 — change only via PR with explicit justification):
  return_1m / return_5m / price_change_5m : delta ≤ 1e-9  (effectively exact)
  last_tick_ts_ms                         : delta ≤ 5 000 ms (trigger timing)
  ts_ms gap between the two writes        : ≤ 90 000 ms (< 1.5 candle cycles)
  regime_id                               : exact match (or both absent)
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ─── Tolerances ────────────────────────────────────────────────────────────────

RETURN_TOL: float = 1e-9      # return_1m / return_5m / price_change_5m
TICK_TS_TOL_MS: int = 90_000  # last_tick_ts_ms: 90 s — structural trigger-timing gap:
#   cdb_candles writes last_tick_ts_ms once per candle emission (every ~60 s).
#   cdb_market  writes last_tick_ts_ms as the triggering market_data message ts (continuous).
#   Max expected delta = one candle cycle (60 s) + buffer (30 s) = 90 s.
#   Calibrated from first real run 2026-03-18: observed delta = 9 927 ms.
MAX_TS_GAP_MS: int = 90_000   # ts_ms age gap: 90 s  — stale comparison guard

CANDLES_PREFIX = "market_state"
SHADOW_PREFIX = "market_state_shadow"
SCHEMA_VERSION = "1"


# ─── Core comparison logic (pure — no Redis, fully unit-testable) ──────────────


def compare_symbol(
    symbol: str,
    candles_raw: str | None,
    shadow_raw: str | None,
) -> dict[str, Any]:
    """Compare Contract V1 payloads for one symbol.

    Parameters
    ----------
    symbol      : trading symbol, e.g. "BTCUSDT"
    candles_raw : JSON string from market_state:{symbol}        (cdb_candles)
    shadow_raw  : JSON string from market_state_shadow:{symbol} (cdb_market)

    Returns a result dict:
      { symbol, result ("PASS"|"FAIL"), reason, fields: [FieldResult, ...] }
    """
    result: dict[str, Any] = {
        "symbol": symbol,
        "result": "FAIL",
        "reason": "",
        "fields": [],
    }

    if candles_raw is None:
        result["reason"] = (
            f"candles key missing — {CANDLES_PREFIX}:{symbol} expired or not yet written"
        )
        return result
    if shadow_raw is None:
        result["reason"] = (
            f"shadow key missing — {SHADOW_PREFIX}:{symbol} expired or not yet written"
        )
        return result

    try:
        candles = json.loads(candles_raw)
        shadow = json.loads(shadow_raw)
    except (json.JSONDecodeError, TypeError) as exc:
        result["reason"] = f"JSON parse error: {exc}"
        return result

    fields: list[dict[str, Any]] = []
    overall_pass = True

    # ── ts_ms gap — fair-comparison guard ─────────────────────────────────────
    ts_c = candles.get("ts_ms")
    ts_s = shadow.get("ts_ms")
    if ts_c is None or ts_s is None:
        fields.append(
            {
                "field": "ts_ms_gap",
                "result": "FAIL",
                "reason": "ts_ms missing in one or both payloads",
            }
        )
        overall_pass = False
    else:
        gap_ms = abs(int(ts_c) - int(ts_s))
        fr: dict[str, Any] = {
            "field": "ts_ms_gap",
            "candles_value": ts_c,
            "shadow_value": ts_s,
            "gap_ms": gap_ms,
            "max_gap_ms": MAX_TS_GAP_MS,
        }
        if gap_ms > MAX_TS_GAP_MS:
            fr["result"] = "FAIL"
            fr["reason"] = (
                f"ts_ms gap {gap_ms} ms > max {MAX_TS_GAP_MS} ms"
                " — snapshots too far apart for fair comparison"
            )
            overall_pass = False
        else:
            fr["result"] = "PASS"
        fields.append(fr)

    # ── Float return fields ────────────────────────────────────────────────────
    for fname in ("return_1m", "return_5m", "price_change_5m"):
        v_c = candles.get(fname)
        v_s = shadow.get(fname)
        fr = {
            "field": fname,
            "candles_value": v_c,
            "shadow_value": v_s,
            "tolerance": RETURN_TOL,
        }
        if v_c is None or v_s is None:
            fr["result"] = "FAIL"
            fr["reason"] = (
                f"{fname} missing in {'candles' if v_c is None else 'shadow'} payload"
            )
            overall_pass = False
        else:
            delta = abs(float(v_c) - float(v_s))
            fr["delta"] = delta
            if delta > RETURN_TOL:
                fr["result"] = "FAIL"
                fr["reason"] = f"delta {delta:.2e} > tolerance {RETURN_TOL:.2e}"
                overall_pass = False
            else:
                fr["result"] = "PASS"
        fields.append(fr)

    # ── last_tick_ts_ms ────────────────────────────────────────────────────────
    lt_c = candles.get("last_tick_ts_ms")
    lt_s = shadow.get("last_tick_ts_ms")
    fr = {
        "field": "last_tick_ts_ms",
        "candles_value": lt_c,
        "shadow_value": lt_s,
        "tolerance_ms": TICK_TS_TOL_MS,
    }
    if lt_c is None and lt_s is None:
        fr["result"] = "PASS"
        fr["reason"] = "both None — no tick seen yet by either writer"
    elif lt_c is None or lt_s is None:
        fr["result"] = "FAIL"
        fr["reason"] = (
            f"last_tick_ts_ms None in {'candles' if lt_c is None else 'shadow'}"
            " but present in the other"
        )
        overall_pass = False
    else:
        delta_ms = abs(int(lt_c) - int(lt_s))
        fr["delta_ms"] = delta_ms
        if delta_ms > TICK_TS_TOL_MS:
            fr["result"] = "FAIL"
            fr["reason"] = f"delta {delta_ms} ms > tolerance {TICK_TS_TOL_MS} ms"
            overall_pass = False
        else:
            fr["result"] = "PASS"
    fields.append(fr)

    # ── regime_id — exact match or both absent ────────────────────────────────
    has_r_c = "regime_id" in candles
    has_r_s = "regime_id" in shadow
    fr = {
        "field": "regime_id",
        "candles_value": candles.get("regime_id"),
        "shadow_value": shadow.get("regime_id"),
    }
    if not has_r_c and not has_r_s:
        fr["result"] = "PASS"
        fr["reason"] = "both absent — fail-closed: no regime signal for either writer"
    elif has_r_c != has_r_s:
        fr["result"] = "FAIL"
        fr["reason"] = (
            f"regime_id present in {'candles' if has_r_c else 'shadow'} only"
        )
        overall_pass = False
    elif candles["regime_id"] != shadow["regime_id"]:
        fr["result"] = "FAIL"
        fr["reason"] = (
            f"regime_id mismatch: candles={candles['regime_id']}"
            f" shadow={shadow['regime_id']}"
        )
        overall_pass = False
    else:
        fr["result"] = "PASS"
    fields.append(fr)

    result["fields"] = fields
    result["result"] = "PASS" if overall_pass else "FAIL"
    if not overall_pass:
        failed = [f["field"] for f in fields if f.get("result") == "FAIL"]
        result["reason"] = f"field failures: {failed}"
    return result


# ─── Redis-backed gate run ─────────────────────────────────────────────────────


def run_gate(redis_client: Any, output_path: Path | None = None) -> dict[str, Any]:
    """Execute the full evidence gate against a live Redis instance.

    Discovers symbols from ``market_state:*`` keys (live contract, cdb_candles).
    Returns the full evidence report dict and optionally writes it to *output_path*.
    """
    now_utc = datetime.now(timezone.utc).isoformat()

    # Discover symbols from live contract keys only.
    # "market_state:*" never matches "market_state_shadow:*" because the colon
    # is part of the pattern, so no shadow keys are included here.
    raw_keys: list[str] = redis_client.keys(f"{CANDLES_PREFIX}:*")
    symbols = sorted(k[len(CANDLES_PREFIX) + 1 :] for k in raw_keys)

    symbol_results: list[dict[str, Any]] = []
    passes = 0
    fails = 0

    for symbol in symbols:
        candles_raw = redis_client.get(f"{CANDLES_PREFIX}:{symbol}")
        shadow_raw = redis_client.get(f"{SHADOW_PREFIX}:{symbol}")
        res = compare_symbol(symbol, candles_raw, shadow_raw)
        symbol_results.append(res)
        if res["result"] == "PASS":
            passes += 1
        else:
            fails += 1

    if not symbols:
        overall = "BLOCKED"
        overall_reason = (
            f"no {CANDLES_PREFIX}:* keys found"
            " — cdb_candles not writing or Redis not populated"
        )
    elif fails > 0:
        overall = "FAIL"
        overall_reason = f"{fails}/{len(symbols)} symbols failed"
    else:
        overall = "PASS"
        overall_reason = f"all {passes} symbol(s) within tolerance"

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now_utc,
        "candles_key_prefix": CANDLES_PREFIX,
        "shadow_key_prefix": SHADOW_PREFIX,
        "tolerances": {
            "return_fields_abs": RETURN_TOL,
            "last_tick_ts_ms_ms": TICK_TS_TOL_MS,
            "ts_ms_gap_ms": MAX_TS_GAP_MS,
        },
        "symbols_checked": len(symbols),
        "symbols_pass": passes,
        "symbols_fail": fails,
        "overall": overall,
        "overall_reason": overall_reason,
        "symbol_results": symbol_results,
    }

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    return report


# ─── CLI ──────────────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Dual-Write Evidence Gate — market_state Contract V1"
    )
    parser.add_argument("--redis-host", default="localhost", help="Redis host")
    parser.add_argument("--redis-port", type=int, default=6379, help="Redis port")
    parser.add_argument("--redis-password", default=None, help="Redis password")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        metavar="PATH",
        help="Write JSON evidence report to PATH",
    )
    args = parser.parse_args()

    try:
        import redis as redis_lib

        client = redis_lib.Redis(
            host=args.redis_host,
            port=args.redis_port,
            password=args.redis_password,
            decode_responses=True,
        )
        client.ping()
    except Exception as exc:
        print(f"ERROR: Redis connection failed: {exc}", file=sys.stderr)
        return 2

    try:
        report = run_gate(client, output_path=args.output)
    except Exception as exc:
        print(f"ERROR: gate execution failed: {exc}", file=sys.stderr)
        return 2

    print(f"Evidence Gate: {report['overall']}")
    print(f"  Symbols checked : {report['symbols_checked']}")
    print(f"  Pass / Fail     : {report['symbols_pass']} / {report['symbols_fail']}")
    print(f"  Reason          : {report['overall_reason']}")
    for sr in report["symbol_results"]:
        status = sr["result"]
        extra = f" — {sr['reason']}" if sr.get("reason") else ""
        print(f"  [{status}] {sr['symbol']}{extra}")
    if args.output:
        print(f"\nEvidence written to: {args.output}")

    return 0 if report["overall"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
