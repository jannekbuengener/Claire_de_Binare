"""
Market Regime Service - Models and indicators.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Candle:
    ts: int
    symbol: str
    timeframe: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    venue: Optional[str] = None

    @classmethod
    def from_payload(cls, payload: dict) -> Optional["Candle"]:
        try:
            ts_raw = payload.get("ts") or payload.get("timestamp")
            symbol = payload.get("symbol")
            timeframe = payload.get("timeframe") or payload.get("interval")
            if ts_raw is None or symbol is None or timeframe is None:
                return None
            open_p = payload.get("open")
            high = payload.get("high")
            low = payload.get("low")
            close = payload.get("close")
            if any(v is None for v in (open_p, high, low, close)):
                return None
            return cls(
                ts=int(ts_raw),
                symbol=symbol,
                timeframe=str(timeframe),
                open=float(open_p),
                high=float(high),
                low=float(low),
                close=float(close),
                volume=float(payload.get("volume", 0.0)),
                venue=payload.get("venue"),
            )
        except (TypeError, ValueError):
            return None


def compute_atr(candles: list[Candle], period: int) -> Optional[float]:
    if len(candles) < period + 1:
        return None
    trs = []
    for i in range(1, len(candles)):
        cur = candles[i]
        prev = candles[i - 1]
        tr = max(
            cur.high - cur.low,
            abs(cur.high - prev.close),
            abs(cur.low - prev.close),
        )
        trs.append(tr)
    atr = sum(trs[:period]) / period
    for tr in trs[period:]:
        atr = (atr * (period - 1) + tr) / period
    return atr


def compute_adx(candles: list[Candle], period: int) -> Optional[float]:
    if len(candles) < period + 1:
        return None
    trs = []
    pdm = []
    ndm = []
    for i in range(1, len(candles)):
        cur = candles[i]
        prev = candles[i - 1]
        tr = max(
            cur.high - cur.low,
            abs(cur.high - prev.close),
            abs(cur.low - prev.close),
        )
        up_move = cur.high - prev.high
        down_move = prev.low - cur.low
        trs.append(tr)
        pdm.append(up_move if up_move > down_move and up_move > 0 else 0.0)
        ndm.append(down_move if down_move > up_move and down_move > 0 else 0.0)

    atr = sum(trs[:period]) / period
    pdm_smooth = sum(pdm[:period])
    ndm_smooth = sum(ndm[:period])

    def _dx(pdm_val: float, ndm_val: float, atr_val: float) -> float:
        if atr_val == 0:
            return 0.0
        pdi = 100.0 * (pdm_val / atr_val)
        ndi = 100.0 * (ndm_val / atr_val)
        denom = pdi + ndi
        if denom == 0:
            return 0.0
        return 100.0 * abs(pdi - ndi) / denom

    dxs = []
    for i in range(period):
        dxs.append(_dx(pdm_smooth, ndm_smooth, atr))
        if i + 1 < period:
            atr = (atr * (period - 1) + trs[i + 1]) / period
            pdm_smooth = (pdm_smooth * (period - 1) + pdm[i + 1]) / period
            ndm_smooth = (ndm_smooth * (period - 1) + ndm[i + 1]) / period

    adx = sum(dxs) / period
    for i in range(period, len(trs)):
        atr = (atr * (period - 1) + trs[i]) / period
        pdm_smooth = (pdm_smooth * (period - 1) + pdm[i]) / period
        ndm_smooth = (ndm_smooth * (period - 1) + ndm[i]) / period
        dx = _dx(pdm_smooth, ndm_smooth, atr)
        adx = (adx * (period - 1) + dx) / period

    return adx
