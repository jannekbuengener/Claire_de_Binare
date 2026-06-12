"""BTCUSDT MEXC regime threshold calibration analysis for #3032/#3144.

Deterministic ATR/ADX distribution analysis on the committed raw MEXC
candles. Computes rolling ATR(14), ATR_pct (ATR / close), ADX(14), reports
quantile distribution, and evaluates the current ATR=2.0 threshold against
the BTCUSDT price scale (~60k).

Usage:
    python scripts/profitability/analyze_btcusdt_regime_calibration_3032.py
    python scripts/profitability/analyze_btcusdt_regime_calibration_3032.py --verify-only
"""

from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

RAW_PATH = Path("artifacts/candles/mexc_strict_window_3091/candles.jsonl")

EXPECTED_RAW_SHA256 = (
    "d79a1c3c81191dcf4418ae0c2b2775a6f354ed0cc6801a6955904871c4077605"
)

ADX_PERIOD = 14
ATR_PERIOD = 14
BUFFER_MAXLEN = max(ADX_PERIOD, ATR_PERIOD) * 5  # 70

CURRENT_ATR_THRESHOLD = 2.0
CURRENT_ADX_TREND = 25.0
CURRENT_ADX_RANGE = 20.0


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


def quantile(sorted_values: list[float], q: float) -> float:
    if not sorted_values:
        return 0.0
    idx = q * (len(sorted_values) - 1)
    lo = int(idx)
    hi = min(lo + 1, len(sorted_values) - 1)
    frac = idx - lo
    return sorted_values[lo] * (1 - frac) + sorted_values[hi] * frac


def compute_distribution_stats(values: list[float]) -> dict:
    if not values:
        return {"count": 0}
    sv = sorted(values)
    return {
        "count": len(sv),
        "min": sv[0],
        "max": sv[-1],
        "mean": sum(sv) / len(sv),
        "std": (sum((x - sum(sv) / len(sv)) ** 2 for x in sv) / len(sv)) ** 0.5,
        "p10": quantile(sv, 0.10),
        "p25": quantile(sv, 0.25),
        "p50": quantile(sv, 0.50),
        "p75": quantile(sv, 0.75),
        "p90": quantile(sv, 0.90),
        "p95": quantile(sv, 0.95),
        "p99": quantile(sv, 0.99),
    }


def classify_regime(atr: float, adx: float) -> str:
    if atr >= CURRENT_ATR_THRESHOLD:
        return "HIGH_VOL_CHAOTIC"
    elif adx >= CURRENT_ADX_TREND:
        return "TREND"
    elif adx <= CURRENT_ADX_RANGE:
        return "RANGE"
    return "TRANSITION"


def percentile_of_threshold(sorted_values: list[float], threshold: float) -> float:
    below = sum(1 for v in sorted_values if v < threshold)
    return below / len(sorted_values) * 100 if sorted_values else 0.0


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

    n = len(raw_candles)
    print(f"Raw dataset: SHA-256={raw_hash}, rows={n}")

    atr_values: list[float] = []
    atr_pct_values: list[float] = []
    adx_values: list[float] = []

    regime_counts: Counter[str] = Counter()
    buffer: list[dict] = []

    for row in raw_candles:
        buffer.append(row)
        if len(buffer) > BUFFER_MAXLEN:
            buffer.pop(0)

        adx = compute_adx(buffer, ADX_PERIOD)
        atr = compute_atr(buffer, ATR_PERIOD)
        close = float(row["close"])

        if adx is not None and atr is not None:
            atr_values.append(atr)
            atr_pct_values.append(atr / close * 100.0)
            adx_values.append(adx)
            regime_counts[classify_regime(atr, adx)] += 1

    effective_n = len(atr_values)
    warmup_skipped = n - effective_n
    print(f"Warmup candles: {ADX_PERIOD} (first candle in buffer produces no ATR/ADX)")
    print(f"Candles with valid ATR/ADX: {effective_n} (skipped: {warmup_skipped})")

    atr_stats = compute_distribution_stats(atr_values)
    atr_pct_stats = compute_distribution_stats(atr_pct_values)
    adx_stats = compute_distribution_stats(adx_values)

    atr_2_pctile = percentile_of_threshold(sorted(atr_values), CURRENT_ATR_THRESHOLD)

    print()
    print("=" * 72)
    print("  ATR DISTRIBUTION (absolute, USD)")
    print("=" * 72)
    print(f"  Count:         {atr_stats['count']}")
    print(f"  Min:           {atr_stats['min']:>10.4f} USD")
    print(f"  Max:           {atr_stats['max']:>10.4f} USD")
    print(f"  Mean:          {atr_stats['mean']:>10.4f} USD")
    print(f"  Std:           {atr_stats['std']:>10.4f} USD")
    print(f"  p10:           {atr_stats['p10']:>10.4f} USD")
    print(f"  p25:           {atr_stats['p25']:>10.4f} USD")
    print(f"  p50 (median):  {atr_stats['p50']:>10.4f} USD")
    print(f"  p75:           {atr_stats['p75']:>10.4f} USD")
    print(f"  p90:           {atr_stats['p90']:>10.4f} USD")
    print(f"  p95:           {atr_stats['p95']:>10.4f} USD")
    print(f"  p99:           {atr_stats['p99']:>10.4f} USD")
    print()
    print(
        f"  CURRENT ATR=2.0 USD: below {atr_2_pctile:.2f}% of observations"
    )
    print(f"  => ATR=2.0 is approximately at the p{atr_2_pctile:.1f} threshold")
    print()

    print("=" * 72)
    print("  ATR_PCT DISTRIBUTION (ATR / close * 100)")
    print("=" * 72)
    print(f"  Count:         {atr_pct_stats['count']}")
    print(f"  Min:           {atr_pct_stats['min']:>10.4f}%")
    print(f"  Max:           {atr_pct_stats['max']:>10.4f}%")
    print(f"  Mean:          {atr_pct_stats['mean']:>10.4f}%")
    print(f"  Std:           {atr_pct_stats['std']:>10.4f}%")
    print(f"  p10:           {atr_pct_stats['p10']:>10.4f}%")
    print(f"  p25:           {atr_pct_stats['p25']:>10.4f}%")
    print(f"  p50 (median):  {atr_pct_stats['p50']:>10.4f}%")
    print(f"  p75:           {atr_pct_stats['p75']:>10.4f}%")
    print(f"  p90:           {atr_pct_stats['p90']:>10.4f}%")
    print(f"  p95:           {atr_pct_stats['p95']:>10.4f}%")
    print(f"  p99:           {atr_pct_stats['p99']:>10.4f}%")
    print()

    atr_pct_2 = (CURRENT_ATR_THRESHOLD / 60859.0) * 100
    atr_pct_2_pctile = percentile_of_threshold(
        sorted(atr_pct_values), atr_pct_2
    )
    print(
        f"  CURRENT ATR=2.0 ~= {atr_pct_2:.4f}% of mid-range price (~60859)")
    print(
        f"  => ATR_pct=0.0033% is below {atr_pct_2_pctile:.2f}% of observations"
    )
    print()

    print("=" * 72)
    print("  ADX DISTRIBUTION (0-100 scale)")
    print("=" * 72)
    print(f"  Count:         {adx_stats['count']}")
    print(f"  Min:           {adx_stats['min']:>10.4f}")
    print(f"  Max:           {adx_stats['max']:>10.4f}")
    print(f"  Mean:          {adx_stats['mean']:>10.4f}")
    print(f"  Std:           {adx_stats['std']:>10.4f}")
    print(f"  p10:           {adx_stats['p10']:>10.4f}")
    print(f"  p25:           {adx_stats['p25']:>10.4f}")
    print(f"  p50 (median):  {adx_stats['p50']:>10.4f}")
    print(f"  p75:           {adx_stats['p75']:>10.4f}")
    print(f"  p90:           {adx_stats['p90']:>10.4f}")
    print(f"  p95:           {adx_stats['p95']:>10.4f}")
    print(f"  p99:           {adx_stats['p99']:>10.4f}")
    print()
    print(
        f"  ADX TREND threshold={CURRENT_ADX_TREND}: "
        f"above {percentile_of_threshold(sorted(adx_values), CURRENT_ADX_TREND):.1f}% of observations"
    )
    print(
        f"  ADX RANGE threshold={CURRENT_ADX_RANGE}: "
        f"at = {CURRENT_ADX_RANGE} (qualitative boundary)"
    )
    print()

    print("=" * 72)
    print("  REGIME DISTRIBUTION (CURRENT THRESHOLDS)")
    print("=" * 72)
    total_regime = sum(regime_counts.values())
    for name in ("HIGH_VOL_CHAOTIC", "TREND", "RANGE", "TRANSITION"):
        count = regime_counts.get(name, 0)
        pct = count / total_regime * 100 if total_regime else 0
        print(f"  {name:<20} {count:>6} ({pct:5.1f}%)")
    print()
    print(
        f"  WARNING: {regime_counts.get('HIGH_VOL_CHAOTIC', 0) / total_regime * 100:.1f}% "
        f"HIGH_VOL_CHAOTIC => strategy gets 0 entry opportunities"
    )

    print()
    print("=" * 72)
    print("  CANDIDATE ATR THRESHOLDS (distribution-based)")
    print("=" * 72)
    candidate_thresholds = [
        ("p10", atr_stats["p10"]),
        ("p25", atr_stats["p25"]),
        ("p50 (median)", atr_stats["p50"]),
        ("p75", atr_stats["p75"]),
        ("p90", atr_stats["p90"]),
        ("p95", atr_stats["p95"]),
        ("p99", atr_stats["p99"]),
    ]
    for label, value in candidate_thresholds:
        pct = (value / 60859.0) * 100
        print(f"  ATR p{label:<12} = {value:>10.4f} USD  ({pct:.4f}% of price)")
    print()

    candidate_atr_pct = [0.01, 0.02, 0.05, 0.1, 0.25, 0.5, 1.0]
    print("  ATR_pct-based:")
    for pct_thresh in candidate_atr_pct:
        abs_thresh = pct_thresh / 100.0 * 60859.0
        below = sum(1 for v in atr_pct_values if v < pct_thresh)
        below_pct = below / len(atr_pct_values) * 100
        print(
            f"  ATR > {pct_thresh:>6.2f}%  "
            f"= ATR > {abs_thresh:>8.2f} USD  "
            f"(<p{100 - below_pct:.1f} per dataset)"
        )
    print()

    print("=" * 72)
    print("  RECOMMENDED CALIBRATION GRID (for variant replay testing)")
    print("=" * 72)
    grid = [
        ("baseline", 2.0, "Current committed config -- expected 0 trades"),
        ("atr_p50", atr_stats["p50"], "Median ATR -- balanced regime split"),
        ("atr_p75", atr_stats["p75"], "Upper-quartile ATR -- mostly TREND/RANGE"),
        ("atr_p90", atr_stats["p90"], "90th percentile -- conservative HVC filter"),
        (
            "atr_pct_0.01pct",
            60859.0 * 0.0001,
            "ATR_pct 0.01% -- generous threshold",
        ),
        (
            "atr_pct_0.05pct",
            60859.0 * 0.0005,
            "ATR_pct 0.05% -- moderate threshold",
        ),
        (
            "atr_pct_0.1pct",
            60859.0 * 0.001,
            "ATR_pct 0.1% -- conservative threshold",
        ),
        (
            "atr_pct_0.25pct",
            60859.0 * 0.0025,
            "ATR_pct 0.25% -- strict threshold",
        ),
    ]
    for label, value, note in grid:
        pct_of_price = value / 60859.0 * 100
        print(f"  {label:<20} = {value:>10.2f} USD  ({pct_of_price:.4f}% of price)")
        print(f"    {note}")
    print()

    print("ALL STATISTICS ARE FROM COMMITTED RAW MEXC DATASET ONLY.")
    print("NO THRESHOLD REPRESENTS A PRODUCTION CONFIG CHANGE.")
    print()

    return 0


def verify_only() -> int:
    raw_bytes = RAW_PATH.read_bytes()
    raw_hash = hashlib.sha256(raw_bytes).hexdigest()
    if raw_hash != EXPECTED_RAW_SHA256:
        print(
            f"FAIL: Raw SHA-256={raw_hash} (expected {EXPECTED_RAW_SHA256})",
            file=sys.stderr,
        )
        return 2
    print(f"PASS: Raw SHA-256 unchanged: {raw_hash}")

    raw_candles: list[dict] = []
    for line in raw_bytes.decode("utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        raw_candles.append(json.loads(stripped))

    adx_vals: list[float] = []
    atr_vals: list[float] = []
    atr_pct_vals: list[float] = []
    buffer: list[dict] = []
    for row in raw_candles:
        buffer.append(row)
        if len(buffer) > BUFFER_MAXLEN:
            buffer.pop(0)
        adx = compute_adx(buffer, ADX_PERIOD)
        atr_val = compute_atr(buffer, ATR_PERIOD)
        close = float(row["close"])
        if adx is not None and atr_val is not None:
            adx_vals.append(adx)
            atr_vals.append(atr_val)
            atr_pct_vals.append(atr_val / close * 100.0)

    n_eff = len(atr_vals)
    if n_eff < 1000:
        print(f"FAIL: Only {n_eff} valid ATR values", file=sys.stderr)
        return 2
    print(f"PASS: {n_eff} valid ATR/ADX observations")

    atr_sorted = sorted(atr_vals)
    atr_p50 = quantile(atr_sorted, 0.50)
    atr_below_2 = percentile_of_threshold(atr_sorted, 2.0)
    print(f"  ATR p50 = {atr_p50:.4f} USD")
    print(f"  ATR < 2.0 = {atr_below_2:.2f}% of observations")
    print(f"  ATR < 2.0 count = {sum(1 for v in atr_vals if v < 2.0)}")

    adx_sorted = sorted(adx_vals)
    adx_p50 = quantile(adx_sorted, 0.50)
    print(f"  ADX p50 = {adx_p50:.4f}")
    print(f"  ADX >= 25 = {sum(1 for v in adx_vals if v >= 25)} / {n_eff}")

    atr_pct_sorted = sorted(atr_pct_vals)
    atr_pct_p50 = quantile(atr_pct_sorted, 0.50)
    print(f"  ATR_pct p50 = {atr_pct_p50:.4f}%")

    if atr_below_2 > 10:
        print("WARNING: Very few candles have ATR < 2.0 -- threshold is scale-wrong")
    else:
        print("PASS: ATR threshold distribution looks reasonable at a glance")

    print("ALL REGIME DISTRIBUTION ANALYSIS IS CONTROLLED_LAB_EVIDENCE ONLY.")
    return 0


if __name__ == "__main__":
    if "--verify-only" in sys.argv:
        sys.exit(verify_only())
    sys.exit(main())
