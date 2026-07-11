"""Provider-neutral offline regime assignment for historical candle JSONL."""

from __future__ import annotations

from collections import Counter
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


def assign_regime_ids(raw_candles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Mirror services/regime/service.py offline ADX/ATR regime derivation."""
    current_regime = "UNKNOWN"
    candidate_regime: str | None = None
    candidate_count = 0
    assigned_regime_id = 0

    buffer: list[dict[str, Any]] = []
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

    return derived


def regime_distribution(candles: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(int(row.get("regime_id", 0)) for row in candles)
    return {
        str(regime_id): {
            "regime_name": REGIME_ID_TO_NAME.get(regime_id, "UNKNOWN"),
            "count": count,
        }
        for regime_id, count in sorted(counts.items())
    }
