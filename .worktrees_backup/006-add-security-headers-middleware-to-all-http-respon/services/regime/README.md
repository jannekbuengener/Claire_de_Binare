# Regime Service

Deterministische Marktregime-Erkennung (ADX/ATR) auf Basis von OHLCV-Marktdaten.

## Streams
- Input: `stream.market_data`
- Output: `stream.regime_signals`

## Pflicht-ENV
- `REGIME_ADX_PERIOD`
- `REGIME_ATR_PERIOD`
- `REGIME_ADX_TREND_THRESHOLD`
- `REGIME_ADX_RANGE_THRESHOLD`
- `REGIME_ATR_HIGH_VOL_THRESHOLD`
- `REGIME_CONFIRMATION_BARS`

## Verhalten
- Fehlen OHLCV-Daten, wird kein Regime entschieden (Fallback: `UNKNOWN`).
- Regime-Signale werden deterministisch aus ADX/ATR erzeugt.
