"""Provider-neutral offline regime assignment for historical candle JSONL."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any

ADX_PERIOD = 14
ATR_PERIOD = 14
ADX_TREND_THRESHOLD = 25.0
ADX_RANGE_THRESHOLD = 20.0
ATR_HIGH_VOL_THRESHOLD = 2.0
CONFIRMATION_BARS = 3
BUFFER_MAXLEN = max(ADX_PERIOD, ATR_PERIOD) * 5
WARMUP_CANDLES = 240

REGIME_NAME_TO_ID = {
    "TREND": 0,
    "RANGE": 1,
    "HIGH_VOL_CHAOTIC": 2,
    "CRISIS": 3,
}
REGIME_ID_TO_NAME = {value: key for key, value in REGIME_NAME_TO_ID.items()}


@dataclass
class RegimeCarryState:
    """Serializable carry-over state for chronological multi-chunk enrichment."""

    current_regime: str = "UNKNOWN"
    candidate_regime: str | None = None
    candidate_count: int = 0
    buffer: list[dict[str, Any]] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "current_regime": self.current_regime,
            "candidate_regime": self.candidate_regime,
            "candidate_count": self.candidate_count,
            "buffer_tail_len": len(self.buffer or []),
        }


def compute_atr(candles: list[dict[str, Any]], period: int) -> float | None:
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


def compute_adx(candles: list[dict[str, Any]], period: int) -> float | None:
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


def assign_regime_ids_with_state(
    raw_candles: list[dict[str, Any]],
    *,
    initial_state: RegimeCarryState | None = None,
) -> tuple[list[dict[str, Any]], RegimeCarryState]:
    """Mirror services/regime/service.py with optional carry-over across chunks."""
    state = initial_state or RegimeCarryState()
    current_regime = state.current_regime
    candidate_regime = state.candidate_regime
    candidate_count = state.candidate_count
    buffer: list[dict[str, Any]] = list(state.buffer or [])

    derived: list[dict[str, Any]] = []

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

            assigned_regime_id = REGIME_NAME_TO_ID.get(current_regime, 0)
        else:
            assigned_regime_id = 0

        row = dict(candle)
        row["regime_id"] = assigned_regime_id
        derived.append(row)

    return derived, RegimeCarryState(
        current_regime=current_regime,
        candidate_regime=candidate_regime,
        candidate_count=candidate_count,
        buffer=list(buffer),
    )


def assign_regime_ids(raw_candles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Mirror services/regime/service.py offline ADX/ATR regime derivation."""
    rows, _ = assign_regime_ids_with_state(raw_candles)
    return rows


def analyze_regime_plausibility(
    candles: list[dict[str, Any]],
    *,
    sample_size: int = 500,
) -> dict[str, Any]:
    """Contract/plausibility check without changing thresholds."""
    if not candles:
        return {"status": "FAIL", "reason": "empty_candles"}

    sample = candles[:sample_size]
    atr_values: list[float] = []
    adx_values: list[float] = []
    buffer: list[dict[str, Any]] = []
    for candle in sample:
        buffer.append(candle)
        if len(buffer) > BUFFER_MAXLEN:
            buffer.pop(0)
        adx = compute_adx(buffer, ADX_PERIOD)
        atr = compute_atr(buffer, ATR_PERIOD)
        if adx is not None:
            adx_values.append(adx)
        if atr is not None:
            atr_values.append(atr)

    dist = regime_distribution(candles)
    high_vol_share = 0.0
    total = len(candles)
    for key, entry in dist.items():
        if entry.get("regime_name") == "HIGH_VOL_CHAOTIC":
            high_vol_share = entry.get("count", 0) / total if total else 0.0

    avg_close = sum(float(c["close"]) for c in sample) / len(sample)
    atr_above_threshold_pct = (
        sum(1 for v in atr_values if v >= ATR_HIGH_VOL_THRESHOLD) / len(atr_values)
        if atr_values
        else 0.0
    )

    blocking = False
    findings: list[str] = []
    if avg_close > 1000 and atr_above_threshold_pct > 0.95:
        findings.append(
            "ATR_HIGH_VOL_THRESHOLD=2.0 is absolute price units; "
            f"BTC avg_close~{avg_close:.2f} yields ATR>>2 → HIGH_VOL_CHAOTIC dominance. "
            "Mirrors runtime compose REGIME_ATR_HIGH_VOL_THRESHOLD=2.0 — contract-consistent, "
            "not a normalization defect."
        )
    if high_vol_share > 0.99:
        findings.append(
            f"HIGH_VOL_CHAOTIC share {high_vol_share:.4f} — expected for absolute ATR "
            "threshold on high-price assets; document in evidence, do not silently repair."
        )

    return {
        "status": "PASS_WITH_CAVEAT" if findings else "PASS",
        "blocking": blocking,
        "findings": findings,
        "distribution": dist,
        "sample_stats": {
            "sample_size": len(sample),
            "avg_close": avg_close,
            "atr_min": min(atr_values) if atr_values else None,
            "atr_max": max(atr_values) if atr_values else None,
            "atr_median": sorted(atr_values)[len(atr_values) // 2] if atr_values else None,
            "adx_median": sorted(adx_values)[len(adx_values) // 2] if adx_values else None,
            "atr_above_threshold_pct": atr_above_threshold_pct,
            "thresholds": {
                "adx_trend": ADX_TREND_THRESHOLD,
                "adx_range": ADX_RANGE_THRESHOLD,
                "atr_high_vol": ATR_HIGH_VOL_THRESHOLD,
            },
        },
        "runtime_mirror": "services/regime/service.py + compose REGIME_ATR_HIGH_VOL_THRESHOLD=2.0",
    }


def regime_distribution(candles: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(int(row.get("regime_id", 0)) for row in candles)
    return {
        str(regime_id): {
            "regime_name": REGIME_ID_TO_NAME.get(regime_id, "UNKNOWN"),
            "count": count,
        }
        for regime_id, count in sorted(counts.items())
    }
