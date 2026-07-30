# Regime Service (`cdb_regime`)

Deterministische Marktregime-Erkennung (ADX/ATR) auf Basis von OHLCV-Marktdaten. **BLUE** stack service (port 8008).

## Streams
- Input: `stream.market_data` / `stream.candles_1m` (Compose-Default)
- Output: `stream.regime_signals`

## Pflicht-ENV
- `REGIME_ADX_PERIOD`
- `REGIME_ATR_PERIOD`
- `REGIME_ADX_TREND_THRESHOLD` (ADX 0–100 Skala)
- `REGIME_ADX_RANGE_THRESHOLD` (ADX 0–100 Skala; muss `<` Trend-Threshold)
- `REGIME_ATR_HIGH_VOL_THRESHOLD` — **Einheit: `atr_over_close`** (dimensionsloses ATR/close-Verhältnis; Default Compose/`dev.yml`/`.env.example`: `0.001` = 0.1% des Close). Nicht absolute Preis-ATR.
- `REGIME_CONFIRMATION_BARS`

Optional:
- `REGIME_HEARTBEAT_INTERVAL_S` (Default `60`) — Re-Emit ohne Regimewechsel

## Klassifikationsreihenfolge
1. Warmup: ADX und ATR müssen berechenbar sein (sonst kein Emit).
2. **ATR/close** ≥ Threshold → `HIGH_VOL_CHAOTIC` (vor ADX).
3. sonst ADX ≥ Trend → `TREND`
4. sonst ADX ≤ Range → `RANGE`
5. sonst Hysterese: aktuelles Regime halten
6. Confirmation: Wechsel erst nach `REGIME_CONFIRMATION_BARS` Roh-Labeln

Emit enthält `atr_over_close` und `atr_high_vol_unit=atr_over_close`.

## Missing / Invalid
- Fehlende OHLCV → Emit `UNKNOWN` (fail-closed).
- `close <= 0` → Roh-Label `UNKNOWN` (keine High-Vol-Annahme).
- Kein stiller `TREND`-Fallback.

## Freshness / Heartbeat / TTL Matrix

| Contract | Param | Default | Unit | Owner | Primary consumers | Fail mode |
|---|---|---|---|---|---|---|
| Regime-Heartbeat | `REGIME_HEARTBEAT_INTERVAL_S` | 60 | s | `cdb_regime` | candles/market regime lookup, signal `regime_id`, risk RC_001 | kein Refresh → stale/`regime_id` fehlt |
| Regime accept (candles) | `CANDLE_REGIME_STALENESS_SECONDS` | 300 | s | `cdb_candles` | `market_state.regime_id` | `regime_id` weglassen |
| Regime accept (market) | `MARKET_REGIME_STALENESS_SECONDS` | 300 | s | `cdb_market` | `market_state.regime_id` | `regime_id` weglassen |
| Market-State-TTL | `MARKET_STATE_TTL_SECONDS` / `CANDLE_MARKET_STATE_TTL_SECONDS` | 120 | s | market (+ candles dual-write) | signal, risk, Redis | Key fehlt |
| Signal freshness | `SIGNAL_MARKET_STATE_STALENESS_S` | 30 | s | `cdb_signal` | PB1 entry (`market_state.ts_ms`) | entry blocked |
| Risk freshness | `staleness_s_max` | 5 | s | `cdb_risk` (hardcoded) | `decide_trade` | RC_003 |
| Risk data silence | `data_silence_s_max` | 30 | s | `cdb_risk` (hardcoded) | `decide_trade` | RC_004 |

Hinweise:
- Heartbeat muss ≪ Regime-Accept (300s) bleiben.
- Signal-Freshness (30s) bezieht sich auf tick-getriebenes `market_state.ts_ms`, nicht direkt auf den Regime-Heartbeat.
- Risk-Grenzen werden von diesem Service nicht gelockert.
