# Candles Service (`cdb_candles`)

Aggregiert `market_data` zu 1-Minuten-Candles und schreibt `stream.candles_1m`.

## Current-main Scope

- Konsumiert Redis Pub/Sub `market_data`.
- Emittiert deterministische 1m-Candles auf `stream.candles_1m`.
- Optional Regime-Staleness-Checks gegen `stream.regime_signals`.

## Topics / Streams

- Input: `market_data` (Pub/Sub, `CANDLE_INPUT_CHANNEL`)
- Output Stream: `stream.candles_1m` (`CANDLE_OUTPUT_STREAM`)

## Runtime Surface

- Endpoint-Port: `CANDLE_PORT` (Default `8007`)
- HTTP: `/health`, `/metrics`

Start im BLUE-Stack:

```powershell
docker compose -f infrastructure/compose/compose.blue.yml up -d cdb_candles
```

## Key Config

- `CANDLE_OUTPUT_STREAM`, `CANDLE_INPUT_CHANNEL`
- `CANDLE_WRITE_MARKET_STATE`, `CANDLE_REGIME_STREAM`
- `CANDLE_REGIME_STALENESS_SECONDS`

## Canonical References

- `services/candles/service.py`
- `services/candles/config.py`
- `services/market/README.md`
