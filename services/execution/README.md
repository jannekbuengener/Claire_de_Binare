# Execution Service (`cdb_execution`)

Order-Execution-Service: konsumiert freigegebene Orders vom Risk Service und publiziert Fills/Results.

## Current-main Scope

- Subscribes `orders` (Pub/Sub) nur nach Risk-`ALLOW`.
- Default: `MOCK_TRADING=true`, `DRY_RUN=true` — kein unkontrolliertes Live-Trading.
- Publiziert `order_results` und schreibt in `stream.fills` (kanonisch für Persistenz via `cdb_db_writer`).
- Kill-Switch-Volume geteilt mit `cdb_risk` (`CDB_KILL_SWITCH_STATE_FILE`).

## Topics / Streams

- Input Topic: `orders`
- Output Topic: `order_results`
- Output Stream: `stream.fills` (`STREAM_ORDER_RESULTS`)
- Shutdown Stream: `stream.bot_shutdown`

## Runtime Surface

- Endpoint-Port: `8003` (`SERVICE_PORT`)
- HTTP: `/health`, `/status`, `/metrics`

Start im BLUE-Stack:

```powershell
docker compose -f infrastructure/compose/compose.blue.yml up -d cdb_execution
```

## Key Config

- `MOCK_TRADING`, `DRY_RUN`, `MEXC_TESTNET`
- `MEXC_API_KEY` / `MEXC_API_SECRET` (Secrets)
- `STREAM_ORDER_RESULTS`, `STREAM_BOT_SHUTDOWN`

## Canonical References

- `services/execution/service.py`
- `services/execution/config.py`
- `services/risk/README.md`
- `core/contracts/decision_contract_v1.py`
