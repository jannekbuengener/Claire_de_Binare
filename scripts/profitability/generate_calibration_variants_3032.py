"""Generate regime calibration variant datasets for #3032/#3144.

Creates test-only derived datasets under artifacts/candles/mexc_strict_window_3091_regime_calibration/
with different ATR thresholds, producing candles.jsonl + calibration_manifest.json per variant.

Each variant re-runs the offline ADX/ATR regime assignment with a single changed
parameter (atr_high_vol_threshold). ADX thresholds remain at committed values.

Usage:
    python scripts/profitability/generate_calibration_variants_3032.py
    python scripts/profitability/generate_calibration_variants_3032.py --dry-run
"""

from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

RAW_PATH = Path("artifacts/candles/mexc_strict_window_3091/candles.jsonl")
DERIVED_ROOT = Path("artifacts/candles/mexc_strict_window_3091_regime_calibration")

EXPECTED_RAW_SHA256 = (
    "d79a1c3c81191dcf4418ae0c2b2775a6f354ed0cc6801a6955904871c4077605"
)

ADX_PERIOD = 14
ATR_PERIOD = 14
ADX_TREND_THRESHOLD = 25.0
ADX_RANGE_THRESHOLD = 20.0
CONFIRMATION_BARS = 3
BUFFER_MAXLEN = max(ADX_PERIOD, ATR_PERIOD) * 5

REGIME_NAME_TO_ID = {
    "TREND": 0,
    "RANGE": 1,
    "HIGH_VOL_CHAOTIC": 2,
    "CRISIS": 3,
}
REGIME_ID_TO_NAME = {v: k for k, v in REGIME_NAME_TO_ID.items()}

# Calibration grid: (variant_slug, atr_threshold, note)
# Thresholds derived from data percentiles (see analyze_btcusdt_regime_calibration_3032.py output)
CALIBRATION_GRID = [
    (
        "baseline_atr_2.0",
        2.0,
        "Current committed config (ATR=2.0) -- expected 0 trades",
    ),
    (
        "atr_p50_48.01",
        48.01,
        "ATR at p50 (median) -- balanced regime split",
    ),
    (
        "atr_p75_61.82",
        61.82,
        "ATR at p75 (upper quartile) -- mostly TREND/RANGE",
    ),
    (
        "atr_p90_76.84",
        76.84,
        "ATR at p90 -- conservative HVC filter",
    ),
    (
        "atr_pct_0.01pct_6.09",
        6.09,
        "ATR_pct 0.01% of price (~6 USD) -- generous threshold",
    ),
    (
        "atr_pct_0.05pct_30.43",
        30.43,
        "ATR_pct 0.05% of price (~30 USD) -- moderate threshold",
    ),
    (
        "atr_pct_0.1pct_60.86",
        60.86,
        "ATR_pct 0.1% of price (~61 USD) -- near p75",
    ),
    (
        "atr_pct_0.25pct_152.15",
        152.15,
        "ATR_pct 0.25% of price (~152 USD) -- strict threshold",
    ),
]


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
    """Build derived candles with parameterized ATR threshold.

    Faithfully mirrors services/regime/service.py:_derive_regime.
    """
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


def write_variant_manifest(
    variant_dir: Path,
    slug: str,
    atr_threshold: float,
    note: str,
    distribution: Counter[int],
    raw_rows: int,
    derived_rows: int,
) -> None:
    manifest = {
        "schema_version": "calibration_variant_manifest.v1",
        "issue": "#3144",
        "parent": "#3032",
        "refs": ["#3142", "#3143"],
        "variant_slug": slug,
        "atr_high_vol_threshold": atr_threshold,
        "threshold_note": note,
        "derived_from": {
            "source_directory": str(RAW_PATH.parent),
            "source_candles": str(RAW_PATH),
            "source_sha256": EXPECTED_RAW_SHA256,
            "source_rows": raw_rows,
        },
        "method": "offline_heuristic_adx_atr",
        "method_detail": (
            "Deterministic offline ADX/ATR regime classification with "
            f"parameterized ATR threshold={atr_threshold}. "
            "ADX thresholds unchanged (trend=25.0, range=20.0). "
            "Confirmation bars applied per RegimeService logic."
        ),
        "parameters": {
            "adx_period": ADX_PERIOD,
            "atr_period": ATR_PERIOD,
            "adx_trend_threshold": ADX_TREND_THRESHOLD,
            "adx_range_threshold": ADX_RANGE_THRESHOLD,
            "atr_high_vol_threshold": atr_threshold,
            "confirmation_bars": CONFIRMATION_BARS,
            "buffer_maxlen": BUFFER_MAXLEN,
        },
        "estimation": True,
        "estimation_note": (
            "All regime_id values are estimated via offline ADX/ATR heuristic. "
            "They are NOT runtime-derived. Evidence class remains "
            "controlled_lab_evidence. This is a test-only calibration variant."
        ),
        "evidence_class": "controlled_lab_evidence",
        "test_only": True,
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
        "regime_distribution_summary": {
            str(rid): count for rid, count in sorted(distribution.items())
        },
        "initial_fallback_regime": {
            "regime_id": 0,
            "regime_name": "TREND",
            "note": (
                f"Regime defaulted to 0 (TREND) for first {ADX_PERIOD} candles "
                f"(ADX/ATR require period+1={ADX_PERIOD + 1} candles)."
            ),
        },
        "warmup_candles_defaulted": ADX_PERIOD,
        "confirmation_bars_applied": True,
        "deterministic": True,
        "no_randomness": True,
        "output_rows": derived_rows,
        "input_output_row_count_match": raw_rows == derived_rows,
        "no_raw_dataset_overwrite": True,
        "raw_dataset_sha256_unchanged": EXPECTED_RAW_SHA256,
        "generated_by": "scripts/profitability/generate_calibration_variants_3032.py",
        "generated_for": "Issue #3144 -- BTCUSDT regime calibration analysis",
        "lr_status": "NO-GO",
        "board_stage": "trade-capable",
        "board_stage_note": (
            "Board stage is orthogonal to LR. Does not authorize live trading."
        ),
    }
    manifest_path = variant_dir / "calibration_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    )


def main() -> int:
    dry_run = "--dry-run" in sys.argv

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

    n_raw = len(raw_candles)
    print(f"Raw dataset OK: SHA-256={raw_hash}, rows={n_raw}")

    variant_summaries: list[dict] = []

    for slug, atr_threshold, note in CALIBRATION_GRID:
        variant_dir = DERIVED_ROOT / slug
        print()
        print(f"Variant: {slug}")
        print(f"  ATR threshold: {atr_threshold}")
        print(f"  Note: {note}")

        if dry_run:
            print(f"  DRY-RUN: would write to {variant_dir}")
            continue

        variant_dir.mkdir(parents=True, exist_ok=True)

        derived, distribution = build_derived_candles(raw_candles, atr_threshold)

        null_count = sum(1 for r in derived if r["regime_id"] is None)
        if null_count > 0:
            print(f"  ERROR: {null_count} rows have null regime_id", file=sys.stderr)
            return 2

        invalid = [
            i for i, r in enumerate(derived) if r["regime_id"] not in {0, 1, 2, 3}
        ]
        if invalid:
            print(
                f"  ERROR: {len(invalid)} rows have invalid regime_id",
                file=sys.stderr,
            )
            return 2

        candles_path = variant_dir / "candles.jsonl"
        with candles_path.open("w") as f:
            for row in derived:
                f.write(json.dumps(row) + "\n")

        write_variant_manifest(
            variant_dir, slug, atr_threshold, note, distribution, n_raw, len(derived)
        )

        total = sum(distribution.values())
        summary_dist = {}
        for rid in sorted(distribution):
            name = REGIME_ID_TO_NAME.get(rid, "???")
            count = distribution[rid]
            pct = count / total * 100
            summary_dist[name] = {"count": count, "pct": round(pct, 1)}
            print(f"  {name:<20} {count:>6} ({pct:5.1f}%)")

        variant_summaries.append(
            {
                "slug": slug,
                "atr_threshold": atr_threshold,
                "note": note,
                "rows": len(derived),
                "distribution": {str(k): v for k, v in distribution.items()},
            }
        )

    if not dry_run:
        top_manifest = {
            "schema_version": "calibration_variants_manifest.v1",
            "issue": "#3144",
            "parent": "#3032",
            "refs": ["#3142", "#3143"],
            "raw_dataset": {
                "path": str(RAW_PATH),
                "sha256": EXPECTED_RAW_SHA256,
                "rows": n_raw,
            },
            "calibration_grid": [
                {"slug": s["slug"], "atr_threshold": s["atr_threshold"]}
                for s in variant_summaries
            ],
            "variant_count": len(variant_summaries),
            "variants": variant_summaries,
            "evidence_class": "controlled_lab_evidence",
            "test_only": True,
            "estimation": True,
            "lr_status": "NO-GO",
            "no_live_go": True,
            "no_echtgeld_go": True,
            "no_production_config_change": True,
            "generated_by": "scripts/profitability/generate_calibration_variants_3032.py",
        }
        top_path = DERIVED_ROOT / "calibration_manifest.json"
        top_path.write_text(
            json.dumps(top_manifest, indent=2, ensure_ascii=False) + "\n"
        )
        print()
        print(f"Top-level manifest: {top_path}")

    print()
    print(f"Generated {len(variant_summaries)} calibration variants.")
    print("ALL REGIME LABELS ARE ESTIMATED. TEST-ONLY. NO PRODUCTION CONFIG CHANGE.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
