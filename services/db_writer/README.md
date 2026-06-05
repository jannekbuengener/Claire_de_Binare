# DB Writer (`cdb_db_writer`)

Persistiert Redis-Stream-Events nach Postgres (kanonischer Insert-Pfad für Streams).

## Current-main Scope

- Konsumiert Trading-/Lifecycle-Streams und schreibt idempotent nach Postgres.
- Kanonische Candle-Persistenz aus `stream.candles_1m`.
- Kein zweiter unkontrollierter Writer für dieselben Tabellen (siehe Dual-Writer-Reconcile-Historie in `CURRENT_STATUS.md`).

## Streams (typisch)

- `stream.candles_1m` (dedizierter Candle-Writer-Thread)
- Weitere Stream-Consumer gemäß `services/db_writer/db_writer.py`

## Runtime Surface

- Metrics-Port: `DB_WRITER_METRICS_PORT` (Default `8010`)
- Kein öffentlicher Trading-HTTP-API-Pfad — Beobachtung über Metrics/Logs

Start im BLUE-Stack:

```powershell
docker compose -f infrastructure/compose/compose.blue.yml up -d cdb_db_writer
```

## Key Config

- `REDIS_*`, `POSTGRES_*` / `DATABASE_URL`
- Stream-Namen in `db_writer.py` (z. B. `_CANDLE_STREAM_KEY`)

## Canonical References

- `services/db_writer/db_writer.py`
- [`infrastructure/database/README.md`](../../infrastructure/database/README.md)
- `services/execution/README.md` (fills → stream)
