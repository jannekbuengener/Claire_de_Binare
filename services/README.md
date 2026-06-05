# Microservices (`services/`)

Stateless runtime services for the BLUE+RED stack. Persistent state lives in Postgres/Redis, not in service containers.

## Where to write / Where not to write
*   **Write here:** Service code, service-local config, Dockerfiles, requirements.
*   **Do NOT write here:** Shared domain logic (`core/`), governance docs (`knowledge/`), compose canon (`infrastructure/compose/`).

## Service index

| Service | Stack | README |
|---|---|---|
| [allocation/](allocation/) | BLUE | [README](allocation/README.md) |
| [candles/](candles/) | BLUE | [README](candles/README.md) |
| [db_writer/](db_writer/) | BLUE | [README](db_writer/README.md) |
| [execution/](execution/) | BLUE | [README](execution/README.md) |
| [market/](market/) | BLUE | [README](market/README.md) |
| Paper runner (`tools/paper_trading/`) | BLUE | [README](../tools/paper_trading/README.md) |
| [regime/](regime/) | BLUE | [README](regime/README.md) |
| [risk/](risk/) | BLUE | [README](risk/README.md) |
| [signal/](signal/) | RED | [README](signal/README.md) |
| [validation/](validation/) | offline lib | [README](validation/README.md) |
| [ws/](ws/) | RED | [README](ws/README.md) |

## Redis transport

- **market_data:** Redis Pub/Sub (not Streams) — `XLEN market_data` returns 0 by design.
- **signals, orders, allocation_decisions, stream.fills:** Redis Streams for durable logs.

## Runtime entry

```bash
docker compose -f infrastructure/compose/compose.blue.yml up -d
docker compose -f infrastructure/compose/compose.red.yml up -d
```

See `infrastructure/compose/README.md` and linked service READMEs above.
