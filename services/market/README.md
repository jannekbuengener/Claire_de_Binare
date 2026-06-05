# Market Service (`cdb_market`)

Eigentümer von `market_state:{symbol}` in Redis — aggregiert Candles/Regime-Kontext für downstream BLUE-Services.

## Current-main Scope

- Post-cutover Market-State-Owner (Issue #1201).
- Liest `stream.candles_1m` und `stream.regime_signals` für State-Aufbau.
- Fail-closed wenn erforderliche Felder fehlen (siehe `docs/governance/MARKET_STATE_CONTRACT_V1.md`).

## Topics / Streams

- Input: `market_data` (Pub/Sub), `stream.candles_1m`, `stream.regime_signals`
- Redis keys: `market_state:{symbol}` (TTL-konfigurierbar)

## Runtime Surface

- Endpoint-Port: `MARKET_PORT` (Default `8009`)
- HTTP: `/health`, `/status`, `/metrics`

Start im BLUE-Stack:

```powershell
docker compose -f infrastructure/compose/compose.blue.yml up -d cdb_market
```

## Key Config

- `MARKET_CANDLES_STREAM`, `MARKET_REGIME_STREAM`
- `MARKET_STATE_KEY_PREFIX`, TTL-Settings in `services/market/service.py`

## Canonical References

- `services/market/service.py`
- `docs/governance/MARKET_STATE_CONTRACT_V1.md`
- `services/candles/README.md`
- `services/regime/README.md`
