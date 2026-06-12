"""Generate regime-assigned calibrated dataset for the MEXC sample expansion 3032 dataset.

Uses the predeclared distribution-based calibration rule from #3145/#3147:
ATR p75 of this specific dataset's ATR distribution.

Usage:
    python scripts/profitability/assign_regime_calibrate_3032_expansion.py
    python scripts/profitability/assign_regime_calibrate_3032_expansion.py --verify-only
"""

from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

RAW_PATH = Path("artifacts/candles/mexc_sample_expansion_3032/candles.jsonl")
DERIVED_DIR = Path("artifacts/candles/mexc_sample_expansion_3032_regime_calibrated")

EXPECTED_RAW_SHA256 = "888cfd6bc1b96c53e47ae7be984e7d8a3924207750478f0d1cb4896899b9bd0a"

ADX_PERIOD = 14
ATR_PERIOD = 14
ADX_TREND_THRESHOLD = 25.0
ADX_RANGE_THRESHOLD = 20.0
CONFIRMATION_BARS = 3
BUFFER_MAXLEN = max(ADX_PERIOD, ATR_PERIOD) * 5

# ATR p75 on this specific dataset (computed 2026-06-12 via analyze_seg6.py)
# BTCUSDT at ~$92k in Jan 2026
ATR_HIGH_VOL_THRESHOLD = 52.59

REGIME_NAME_TO_ID = {
    "TREND": 0,
    "RANGE": 1,
    "HIGH_VOL_CHAOTIC": 2,
    "CRISIS": 3,
}
REGIME_ID_TO_NAME = {v: k for k, v in REGIME_NAME_TO_ID.items()}


def compute_atr(candles: list[dict], period: int) -> float | None:
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
    atr_val = sum(trs[:period]) / period
    for tr in trs[period:]:
        atr_val = (atr_val * (period - 1) + tr) / period
    return atr_val


def compute_adx(candles: list[dict], period: int) -> float | None:
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

    adx_val = sum(dxs) / period
    for i in range(period, len(trs)):
        atr_val = (atr_val * (period - 1) + trs[i]) / period
        pdm_smooth = (pdm_smooth * (period - 1) + pdm[i]) / period
        ndm_smooth = (ndm_smooth * (period - 1) + ndm[i]) / period
        dx = _dx(pdm_smooth, ndm_smooth, atr_val)
        adx_val = (adx_val * (period - 1) + dx) / period

    return adx_val


def build_derived_candles(
    raw_candles: list[dict], atr_threshold: float
) -> tuple[list[dict], Counter[int]]:
    current_regime = "UNKNOWN"
    candidate_regime: str | None = None
    candidate_count = 0
    assigned_regime_id = 0

    buffer: list[dict] = []
    derived: list[dict] = []

    for candle in raw_candles:
        buffer.append(candle)
        if len(buffer) > BUFFER_MAXLEN:
            buffer.pop(0)

        adx = compute_adx(buffer, ADX_PERIOD)
        atr = compute_atr(buffer, ATR_PERIOD)

        if adx is not None and atr is not None:
            if atr >= atr_threshold:
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

            assigned_regime_id = REGIME_NAME_TO_ID.get(current_regime, 0)
        else:
            assigned_regime_id = 0

        row = dict(candle)
        row["regime_id"] = assigned_regime_id
        derived.append(row)

    distribution = Counter(r["regime_id"] for r in derived)
    return derived, distribution


def main() -> int:
    verify_only = "--verify-only" in sys.argv

    if not RAW_PATH.exists():
        print(f"ERROR: Raw dataset not found: {RAW_PATH}", file=sys.stderr)
        return 2

    raw_hasher = hashlib.sha256()
    raw_candles: list[dict] = []
    for line in RAW_PATH.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        raw_hasher.update((stripped + "\n").encode("utf-8"))
        raw_candles.append(json.loads(stripped))

    raw_hash = raw_hasher.hexdigest()
    if raw_hash != EXPECTED_RAW_SHA256:
        print(
            f"ERROR: Raw SHA-256 mismatch.\n"
            f"Expected: {EXPECTED_RAW_SHA256}\n"
            f"Got:      {raw_hash}",
            file=sys.stderr,
        )
        return 2

    n_raw = len(raw_candles)
    print(f"Raw dataset OK: SHA-256={raw_hash}, rows={n_raw}")

    print(f"ATR threshold: {ATR_HIGH_VOL_THRESHOLD} (p75 of this dataset)")
    print(f"Calibration rule: distribution-based p75 per #3145/#3147")

    if verify_only:
        print("VERIFY-ONLY: Would generate derived dataset at", DERIVED_DIR)
        return 0

    derived, distribution = build_derived_candles(raw_candles, ATR_HIGH_VOL_THRESHOLD)

    # Integrity checks
    null_count = sum(1 for r in derived if r["regime_id"] is None)
    if null_count > 0:
        print(f"ERROR: {null_count} rows have null regime_id", file=sys.stderr)
        return 2

    invalid = [i for i, r in enumerate(derived) if r["regime_id"] not in {0, 1, 2, 3}]
    if invalid:
        print(f"ERROR: {len(invalid)} rows have invalid regime_id", file=sys.stderr)
        return 2

    DERIVED_DIR.mkdir(parents=True, exist_ok=True)

    candles_path = DERIVED_DIR / "candles.jsonl"
    derived_bytes = 0
    derived_hasher = hashlib.sha256()
    with candles_path.open("w") as f:
        for row in derived:
            line = json.dumps(row) + "\n"
            derived_hasher.update(line.encode("utf-8"))
            f.write(line)
            derived_bytes += len(line)

    derived_sha256 = derived_hasher.hexdigest()

    print()
    print("Regime distribution:")
    total = sum(distribution.values())
    for rid in sorted(distribution):
        name = REGIME_ID_TO_NAME.get(rid, "???")
        count = distribution[rid]
        pct = count / total * 100
        print(f"  {name:<20} {count:>6} ({pct:5.1f}%)")

    # Write regime_assignment_manifest.json
    manifest = {
        "schema_version": "regime_assignment_manifest.v1",
        "issue": "#3150",
        "parent": "#3032",
        "refs": ["#3142", "#3144", "#3145", "#3147"],
        "derived_from": {
            "source_directory": str(RAW_PATH.parent),
            "source_candles": str(RAW_PATH),
            "source_sha256": EXPECTED_RAW_SHA256,
            "source_rows": n_raw,
        },
        "method": "offline_heuristic_adx_atr",
        "method_detail": (
            "Deterministic offline ADX/ATR regime classification with "
            f"calibrated ATR threshold={ATR_HIGH_VOL_THRESHOLD} (p75 of this dataset). "
            "ADX thresholds kept at committed values (trend=25.0, range=20.0). "
            "Confirmation bars applied per RegimeService logic."
        ),
        "calibration_rule": "distribution_based_p75",
        "calibration_rule_refs": ["#3145", "#3147"],
        "calibration_note": (
            "Threshold NOT selected by profit. p75 of this dataset's independent "
            "ATR(14) distribution, computed on raw candles before any replay. "
            "Same methodology as #3145/#3147: distribution-based, not profit-optimized."
        ),
        "parameters": {
            "adx_period": ADX_PERIOD,
            "atr_period": ATR_PERIOD,
            "adx_trend_threshold": ADX_TREND_THRESHOLD,
            "adx_range_threshold": ADX_RANGE_THRESHOLD,
            "atr_high_vol_threshold": ATR_HIGH_VOL_THRESHOLD,
            "confirmation_bars": CONFIRMATION_BARS,
            "buffer_maxlen": BUFFER_MAXLEN,
        },
        "estimation": True,
        "estimation_note": (
            "All regime_id values are estimated via offline ADX/ATR heuristic. "
            "They are NOT runtime-derived. Evidence class remains "
            "controlled_lab_evidence."
        ),
        "evidence_class": "controlled_lab_evidence",
        "regime_mapping": {
            "0": "TREND",
            "1": "RANGE",
            "2": "HIGH_VOL_CHAOTIC",
            "3": "CRISIS",
        },
        "regime_distribution": {
            str(rid): {
                "regime_name": REGIME_ID_TO_NAME.get(rid, "UNKNOWN"),
                "count": count,
            }
            for rid, count in sorted(distribution.items())
        },
        "output_rows": len(derived),
        "input_output_row_count_match": n_raw == len(derived),
        "output_sha256": derived_sha256,
        "deterministic": True,
        "no_randomness": True,
        "no_raw_dataset_overwrite": True,
        "raw_dataset_sha256_unchanged": EXPECTED_RAW_SHA256,
        "generated_by": "scripts/profitability/assign_regime_calibrate_3032_expansion.py",
        "generated_for": "Issue #3150 -- Expand MEXC same-venue sample size",
        "lr_status": "NO-GO",
        "board_stage": "trade-capable",
        "board_stage_note": (
            "Board stage is orthogonal to LR. Does not authorize live trading."
        ),
    }
    manifest_path = DERIVED_DIR / "regime_assignment_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")

    # Also write dataset_spec.json for the derived dataset
    spec = {
        "spec_version": "1.0",
        "dataset_id": "mexc_sample_expansion_3032_regime_calibrated",
        "derived_from": "mexc_sample_expansion_3032",
        "source": "file",
        "venue": "mexc",
        "venue_match": True,
        "symbol": "BTCUSDT",
        "interval": "1m",
        "regime_assigned": True,
        "regime_calibrated": True,
        "calibration_rule": "distribution_based_p75",
        "atr_threshold": ATR_HIGH_VOL_THRESHOLD,
        "quality": {
            "total_rows": len(derived),
            "regime_id_available": True,
            "all_regime_ids_valid": True,
        },
        "sha256": derived_sha256,
        "evidence_class": "controlled_lab_evidence",
    }
    spec_path = DERIVED_DIR / "dataset_spec.json"
    spec_path.write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n")

    print()
    print(f"Derived dataset: {candles_path}")
    print(f"  SHA-256: {derived_sha256}")
    print(f"  Rows: {len(derived)}")
    print(f"  Files: {DERIVED_DIR.name}/")
    print("ALL REGIME LABELS ARE ESTIMATED. CONTROLLED_LAB_EVIDENCE ONLY.")
    print("NO PRODUCTION CONFIG CHANGE. NO THRESHOLD SELECTION BY PROFIT.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
