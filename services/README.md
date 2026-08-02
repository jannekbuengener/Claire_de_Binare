# Microservices (`services/`)

Stateless runtime services for the BLUE+RED stack. Persistent state lives in Postgres/Redis, not in service containers.

## Where to write / Where not to write
*   **Write here:** Service code, service-local config, Dockerfiles, requirements.
*   **Do NOT write here:** Shared domain logic (`core/`), governance docs (`knowledge/`), compose canon (`infrastructure/compose/`).

## Service index

| Service | Stack | Notes |
|---|---|---|
| [`allocation/`](allocation/README.md) | BLUE | Regime → allocation gate |
| [`candles/`](candles/README.md) | BLUE | 1m candle aggregation |
| [`db_writer/`](db_writer/README.md) | BLUE | Redis stream → Postgres |
| [`execution/`](execution/README.md) | BLUE | Order submit (`MOCK_TRADING` default) |
| [`market/`](market/README.md) | BLUE | Owns `market_state:{symbol}` |
| Paper runner (`tools/paper_trading/`) | BLUE | [`README`](../tools/paper_trading/README.md) (not under `services/`) |
| [`regime/`](regime/README.md) | BLUE | ADX/ATR regime classification |
| [`reports/`](reports/README.md) | RED | Reporting / digests |
| [`risk/`](risk/README.md) | BLUE | Central risk gate + kill-switch |
| [`signal/`](signal/README.md) | RED | Signal generation |
| [`validation/`](validation/README.md) | offline lib | Validation helpers (not a compose service) |
| [`ws/`](ws/README.md) | RED | MEXC WebSocket feed |

## Redis transport

- **market_data:** Redis Pub/Sub (not Streams) — `XLEN market_data` returns 0 by design.
- **signals, orders, allocation_decisions, stream.fills:** Redis Streams for durable logs.

## Runtime entry

```bash
docker compose -f infrastructure/compose/compose.blue.yml up -d
docker compose -f infrastructure/compose/compose.red.yml up -d
```

Compose canon: [`infrastructure/compose/README.md`](../infrastructure/compose/README.md). Stack overview: [`infrastructure/README.md`](../infrastructure/README.md).

## Navigation

- [Projektübersicht](../README.md)
- [Dokumentationsindex](../docs/index.md)
- [Shared core](../core/README.md)
