# Microservices (`services/`)

Stateless runtime services for the BLUE+RED stack. Persistent state lives in Postgres/Redis, not in service containers.

## Where to write / Where not to write
*   **Write here:** Service code, service-local config, Dockerfiles, requirements.
*   **Do NOT write here:** Shared domain logic (`core/`), governance docs (`knowledge/`), compose canon (`infrastructure/compose/`).

## Service index

| Service | Stack | Notes |
|---|---|---|
| [allocation/](allocation/) | BLUE | Regime → allocation_pct |
| [candles/](candles/) | BLUE | 1m candle aggregation |
| [db_writer/](db_writer/) | BLUE | Redis streams → Postgres |
| [execution/](execution/) | BLUE | Order submission (`MOCK_TRADING` default) |
| [market/](market/) | BLUE | `market_state:{symbol}` owner |
| [paper_runner/](paper_runner/) | BLUE | Paper trading runner |
| [regime/](regime/) | BLUE | ADX/ATR regime classification |
| [risk/](risk/) | BLUE | Central order gate + kill-switch |
| [signal/](signal/) | RED | Strategy signals → `stream.signals` |
| [ws/](ws/) | RED | MEXC WebSocket feed |

## Redis transport

- **market_data:** Redis Pub/Sub (not Streams) — `XLEN market_data` returns 0 by design.
- **signals, orders, allocation_decisions, stream.fills:** Redis Streams for durable logs.

## Runtime entry

```bash
docker compose -f infrastructure/compose/compose.blue.yml up -d
docker compose -f infrastructure/compose/compose.red.yml up -d
```

See `infrastructure/compose/README.md` and `services/risk/README.md` / `services/signal/README.md`.
