"""Offline regime assignment for MEXC strict window #3091 dataset.

Mirrors services/regime/service.py ADX/ATR logic deterministically.
Produces a derived JSONL file with integer regime_id values.
Original raw dataset is never modified.

Usage:
    python scripts/profitability/assign_regime_to_mexc_3091.py
    python scripts/profitability/assign_regime_to_mexc_3091.py --verify-only
"""

from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

from tools.market_data.assign_regime_offline import (
    REGIME_ID_TO_NAME,
    REGIME_NAME_TO_ID,
    annotate_regime_row,
    resolve_assigned_regime,
)

RAW_DIR = Path("artifacts/candles/mexc_strict_window_3091")
RAW_PATH = RAW_DIR / "candles.jsonl"
DERIVED_DIR = Path("artifacts/candles/mexc_strict_window_3091_regime_assigned")
DERIVED_PATH = DERIVED_DIR / "candles.jsonl"
MANIFEST_PATH = DERIVED_DIR / "regime_assignment_manifest.json"

EXPECTED_RAW_SHA256 = "d79a1c3c81191dcf4418ae0c2b2775a6f354ed0cc6801a6955904871c4077605"
EXPECTED_ROW_COUNT = 3496

# ── Canonical regime config ──
# From infrastructure/compose/compose.blue.yml (services/regime/config.py env vars)
ADX_PERIOD = 14
ATR_PERIOD = 14
ADX_TREND_THRESHOLD = 25.0
ADX_RANGE_THRESHOLD = 20.0
ATR_HIGH_VOL_THRESHOLD = 2.0
CONFIRMATION_BARS = 3
BUFFER_MAXLEN = max(ADX_PERIOD, ATR_PERIOD) * 5  # 70

_VALID_REGIME_IDS = frozenset(REGIME_NAME_TO_ID.values())


def compute_atr(candles: list[dict], period: int) -> float | None:
    """Mirror services/regime/models.py:compute_atr."""
    if len(candles) < period + 1:
        return None
    trs: list[float] = []
    for i in range(1, len(candles)):
        cur = candles[i]
        prev = candles[i - 1]
        cur_high = float(cur["high"])
        cur_low = float(cur["low"])
        prev_close = float(prev["close"])
        tr = max(
            cur_high - cur_low,
            abs(cur_high - prev_close),
            abs(cur_low - prev_close),
        )
        trs.append(tr)
    atr = sum(trs[:period]) / period
    for tr in trs[period:]:
        atr = (atr * (period - 1) + tr) / period
    return atr


def compute_adx(candles: list[dict], period: int) -> float | None:
    """Mirror services/regime/models.py:compute_adx."""
    if len(candles) < period + 1:
        return None
    trs: list[float] = []
    pdm: list[float] = []
    ndm: list[float] = []
    for i in range(1, len(candles)):
        cur = candles[i]
        prev = candles[i - 1]
        cur_high = float(cur["high"])
        cur_low = float(cur["low"])
        prev_high = float(prev["high"])
        prev_low = float(prev["low"])
        prev_close = float(prev["close"])
        tr = max(
            cur_high - cur_low,
            abs(cur_high - prev_close),
            abs(cur_low - prev_close),
        )
        up_move = cur_high - prev_high
        down_move = prev_low - cur_low
        trs.append(tr)
        pdm.append(up_move if up_move > down_move and up_move > 0 else 0.0)
        ndm.append(down_move if down_move > up_move and down_move > 0 else 0.0)

    atr_val = sum(trs[:period]) / period
    pdm_smooth = sum(pdm[:period])
    ndm_smooth = sum(ndm[:period])

    def _dx(pdm_v: float, ndm_v: float, atr_v: float) -> float:
        if atr_v == 0:
            return 0.0
        pdi = 100.0 * (pdm_v / atr_v)
        ndi = 100.0 * (ndm_v / atr_v)
        denom = pdi + ndi
        if denom == 0:
            return 0.0
        return 100.0 * abs(pdi - ndi) / denom

    dxs: list[float] = []
    for i in range(period):
        dxs.append(_dx(pdm_smooth, ndm_smooth, atr_val))
        if i + 1 < period:
            atr_val = (atr_val * (period - 1) + trs[i + 1]) / period
            pdm_smooth = (pdm_smooth * (period - 1) + pdm[i + 1]) / period
            ndm_smooth = (ndm_smooth * (period - 1) + ndm[i + 1]) / period

    adx = sum(dxs) / period
    for i in range(period, len(trs)):
        atr_val = (atr_val * (period - 1) + trs[i]) / period
        pdm_smooth = (pdm_smooth * (period - 1) + pdm[i]) / period
        ndm_smooth = (ndm_smooth * (period - 1) + ndm[i]) / period
        dx = _dx(pdm_smooth, ndm_smooth, atr_val)
        adx = (adx * (period - 1) + dx) / period

    return adx


def build_derived_candles(raw_candles: list[dict]) -> list[dict]:
    """Build derived candles with integer regime_id using offline ADX/ATR heuristic.

    Faithfully mirrors the regime derivation + confirmation logic from
    services/regime/service.py:_derive_regime. Warmup / UNKNOWN map to
    ``regime_id=None`` (fail-closed; never silent TREND / 0). Refs #4188.
    """
    current_regime = "UNKNOWN"
    candidate_regime: str | None = None
    candidate_count = 0

    buffer: list[dict] = []
    derived: list[dict] = []

    for candle in raw_candles:
        buffer.append(candle)
        if len(buffer) > BUFFER_MAXLEN:
            buffer.pop(0)

        adx = compute_adx(buffer, ADX_PERIOD)
        atr = compute_atr(buffer, ATR_PERIOD)

        if adx is not None and atr is not None:
            if atr >= ATR_HIGH_VOL_THRESHOLD:
                raw_regime = "HIGH_VOL_CHAOTIC"
            elif adx >= ADX_TREND_THRESHOLD:
                raw_regime = "TREND"
            elif adx <= ADX_RANGE_THRESHOLD:
                raw_regime = "RANGE"
            else:
                raw_regime = current_regime

            if raw_regime == current_regime:
                candidate_count = 0
            elif candidate_regime != raw_regime:
                candidate_regime = raw_regime
                candidate_count = 1
            else:
                candidate_count += 1

            if candidate_regime is not None and candidate_count >= CONFIRMATION_BARS:
                current_regime = candidate_regime
                candidate_regime = None
                candidate_count = 0

            assigned_regime_id, block_reason = resolve_assigned_regime(
                indicators_ready=True,
                current_regime=current_regime,
            )
        else:
            assigned_regime_id, block_reason = resolve_assigned_regime(
                indicators_ready=False,
                current_regime=current_regime,
            )

        derived.append(
            annotate_regime_row(
                candle,
                regime_id=assigned_regime_id,
                block_reason=block_reason,
            )
        )

    return derived


def write_manifest(
    raw_rows: int, derived_rows: int, distribution: dict[int, int]
) -> None:
    manifest = {
        "schema_version": "regime_assignment_manifest.v1",
        "issue": "#3142",
        "derived_from": {
            "source_directory": str(RAW_DIR),
            "source_candles": str(RAW_PATH),
            "source_sha256": EXPECTED_RAW_SHA256,
            "source_rows": raw_rows,
        },
        "method": "offline_heuristic_adx_atr",
        "method_detail": (
            "Deterministic offline ADX/ATR-based regime classification mirroring "
            "services/regime/service.py:_derive_regime and services/regime/models.py "
            "(compute_adx, compute_atr). Confirmation bars applied per RegimeService "
            "logic (services/regime/service.py:143-153)."
        ),
        "estimation": True,
        "estimation_note": (
            "All regime_id values are estimated/synthetic via offline ADX/ATR "
            "heuristic. They are NOT runtime-derived. Evidence class remains "
            "controlled_lab_evidence. No claim is made that these labels match "
            "what a live regime service would have produced."
        ),
        "evidence_class": "controlled_lab_evidence",
        "parameters": {
            "adx_period": ADX_PERIOD,
            "atr_period": ATR_PERIOD,
            "adx_trend_threshold": ADX_TREND_THRESHOLD,
            "adx_range_threshold": ADX_RANGE_THRESHOLD,
            "atr_high_vol_threshold": ATR_HIGH_VOL_THRESHOLD,
            "confirmation_bars": CONFIRMATION_BARS,
            "buffer_maxlen": BUFFER_MAXLEN,
            "source": "infrastructure/compose/compose.blue.yml regime env vars",
        },
        "regime_mapping": {
            "0": "TREND",
            "1": "RANGE",
            "2": "HIGH_VOL_CHAOTIC",
            "3": "CRISIS",
            "null": "UNKNOWN",
        },
        "regime_distribution": {
            ("null" if regime_id is None else str(regime_id)): {
                "regime_name": (
                    "UNKNOWN"
                    if regime_id is None
                    else REGIME_ID_TO_NAME.get(regime_id, "UNKNOWN")
                ),
                "count": count,
            }
            for regime_id, count in sorted(
                distribution.items(),
                key=lambda item: (-1 if item[0] is None else item[0]),
            )
        },
        "regime_distribution_summary": {
            ("null" if regime_id is None else str(regime_id)): count
            for regime_id, count in sorted(
                distribution.items(),
                key=lambda item: (-1 if item[0] is None else item[0]),
            )
        },
        "initial_fallback_regime": {
            "regime_id": None,
            "regime_name": "UNKNOWN",
            "block_reason": "WARMUP_INSUFFICIENT_INDICATORS",
            "note": (
                f"Regime defaults to null/UNKNOWN for first {ADX_PERIOD} candles "
                f"(ADX/ATR require period+1={ADX_PERIOD + 1} candles). "
                f"Never silent TREND / regime_id=0. Refs #4188 #4149. "
                f"Full buffer depth is {BUFFER_MAXLEN} candles."
            ),
        },
        "warmup_candles_defaulted": ADX_PERIOD,
        "fail_closed_semantics": (
            "Warmup / UNKNOWN / unmapped regimes emit regime_id=null "
            "(never silent TREND / regime_id=0). Refs #4188 #4149."
        ),
        "confirmation_bars_applied": True,
        "deterministic": True,
        "no_randomness": True,
        "no_gaps": True,
        "all_rows_assigned": True,
        "output_rows": derived_rows,
        "input_output_row_count_match": raw_rows == derived_rows,
        "no_raw_dataset_overwrite": True,
        "raw_dataset_sha256_unchanged": EXPECTED_RAW_SHA256,
        "generated_by": "scripts/profitability/assign_regime_to_mexc_3091.py",
        "generated_for": "Issue #3142 — Regime-assigned file-backed MEXC replay",
        "refs": ["#3142", "#3032", "#3141", "#3091"],
        "lr_status": "NO-GO",
        "board_stage": "trade-capable",
        "board_stage_note": (
            "Board stage is orthogonal to LR. Does not authorize live trading."
        ),
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")


def main() -> int:
    if not RAW_PATH.exists():
        print(f"ERROR: Raw dataset not found: {RAW_PATH}", file=sys.stderr)
        return 2

    raw_bytes = RAW_PATH.read_bytes()
    raw_hash = hashlib.sha256(raw_bytes).hexdigest()
    if raw_hash != EXPECTED_RAW_SHA256:
        print(
            f"ERROR: Raw SHA-256 mismatch.\n"
            f"Expected: {EXPECTED_RAW_SHA256}\n"
            f"Got:      {raw_hash}",
            file=sys.stderr,
        )
        return 2

    raw_candles: list[dict] = []
    for line in raw_bytes.decode("utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        raw_candles.append(json.loads(stripped))

    if len(raw_candles) != EXPECTED_ROW_COUNT:
        print(
            f"ERROR: Unexpected row count: got {len(raw_candles)}, "
            f"expected {EXPECTED_ROW_COUNT}",
            file=sys.stderr,
        )
        return 2

    print(f"Raw dataset OK: SHA-256={raw_hash}, rows={len(raw_candles)}")

    DERIVED_DIR.mkdir(parents=True, exist_ok=True)

    derived = build_derived_candles(raw_candles)

    unknown_count = sum(1 for r in derived if r["regime_id"] is None)
    invalid = [
        i
        for i, r in enumerate(derived)
        if r["regime_id"] is not None and r["regime_id"] not in _VALID_REGIME_IDS
    ]
    if invalid:
        print(f"ERROR: {len(invalid)} rows have invalid regime_id", file=sys.stderr)
        return 2
    print(f"UNKNOWN/null regime_id rows (warmup or unmapped): {unknown_count}")

    distribution = Counter(r["regime_id"] for r in derived)

    with DERIVED_PATH.open("w") as f:
        for row in derived:
            f.write(json.dumps(row) + "\n")

    write_manifest(len(raw_candles), len(derived), dict(distribution))

    print(f"Derived dataset: {DERIVED_PATH} ({len(derived)} rows)")
    print(f"Manifest:       {MANIFEST_PATH}")
    print("Regime distribution:")
    for rid, count in sorted(
        distribution.items(), key=lambda item: (-1 if item[0] is None else item[0])
    ):
        name = "UNKNOWN" if rid is None else REGIME_ID_TO_NAME.get(rid, "???")
        pct = count / len(derived) * 100
        print(f"  {rid} ({name}): {count} ({pct:.1f}%)")
    print("ALL REGIME LABELS ARE ESTIMATED. NOT runtime-derived.")
    return 0


def verify_only() -> int:
    """Validate derived dataset integrity. Returns 0 on pass, 2 on fail."""
    raw_bytes = RAW_PATH.read_bytes()
    raw_hash = hashlib.sha256(raw_bytes).hexdigest()
    if raw_hash != EXPECTED_RAW_SHA256:
        print(
            f"FAIL: Raw SHA-256={raw_hash} (expected {EXPECTED_RAW_SHA256})",
            file=sys.stderr,
        )
        return 2
    print(f"PASS: Raw SHA-256 unchanged: {raw_hash}")

    if not DERIVED_PATH.exists():
        print(f"FAIL: Derived dataset not found: {DERIVED_PATH}", file=sys.stderr)
        return 2

    derived_text = DERIVED_PATH.read_text("utf-8")
    derived: list[dict] = []
    for line in derived_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        derived.append(json.loads(stripped))

    if len(derived) != EXPECTED_ROW_COUNT:
        print(
            f"FAIL: Derived row count={len(derived)} "
            f"(expected {EXPECTED_ROW_COUNT})",
            file=sys.stderr,
        )
        return 2
    print(f"PASS: Derived row count: {len(derived)}")

    raw_candles: list[dict] = []
    for line in raw_bytes.decode("utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        raw_candles.append(json.loads(stripped))

    for i in range(len(derived)):
        rid = derived[i].get("regime_id")
        if rid is None:
            # Fail-closed UNKNOWN/warmup is allowed (#4188).
            if derived[i].get("regime_name") != "UNKNOWN":
                print(
                    f"FAIL: null regime_id without regime_name=UNKNOWN at row {i}",
                    file=sys.stderr,
                )
                return 2
        elif not isinstance(rid, int):
            print(
                f"FAIL: non-int regime_id at row {i}: {type(rid).__name__}",
                file=sys.stderr,
            )
            return 2
        elif rid not in _VALID_REGIME_IDS:
            print(f"FAIL: Invalid regime_id at row {i}: {rid}", file=sys.stderr)
            return 2
        if derived[i]["ts_ms"] != raw_candles[i]["ts_ms"]:
            print(
                f"FAIL: ts_ms mismatch at row {i}: "
                f"derived={derived[i]['ts_ms']} raw={raw_candles[i]['ts_ms']}",
                file=sys.stderr,
            )
            return 2
        for key in ("open", "high", "low", "close", "volume", "trade_count"):
            if derived[i].get(key) != raw_candles[i].get(key):
                print(
                    f"FAIL: {key} mismatch at row {i}: "
                    f"derived={derived[i].get(key)} raw={raw_candles[i].get(key)}",
                    file=sys.stderr,
                )
                return 2

    null_in_derived = sum(1 for r in derived if r["regime_id"] is None)
    print(f"PASS: null/UNKNOWN regime_id in derived: {null_in_derived}")
    print(
        "PASS: Non-null regime_id values are valid integers in "
        f"{sorted(_VALID_REGIME_IDS)}"
    )
    print("PASS: All ts_ms and OHLCV fields match raw dataset")

    distribution = Counter(r["regime_id"] for r in derived)
    print("Regime distribution:")
    for rid in sorted(distribution, key=lambda x: (-1 if x is None else x)):
        name = "UNKNOWN" if rid is None else REGIME_ID_TO_NAME.get(rid, "???")
        pct = distribution[rid] / len(derived) * 100
        print(f"  {rid} ({name}): {distribution[rid]} ({pct:.1f}%)")

    print("ALL REGIME LABELS ARE ESTIMATED. NOT runtime-derived.")
    return 0


if __name__ == "__main__":
    if "--verify-only" in sys.argv:
        sys.exit(verify_only())
    sys.exit(main())
