# Session Log: 2026-07-01 — Issue #3594 Redis Runtime Rebuild

## Auftrag

Operator-GO Phase 2: `cdb_redis` Image-Recreate von `redis:7.4.9-alpine` auf `redis:8.8.0-alpine` (PR #3528 Nachzug), Volume `claire_de_binare_redis_data` beibehalten, Backup-Basis `F:\Claire_Backups\cdb_backup_20260701_022424.zip`. Closes #3594 bei PASS.

## Scope / Boundaries

- Autorisiert: Redis stop/recreate, Volume-Tarball, Validierung, Stack verify, Issue close
- Nicht autorisiert: Postgres (#3600), Volume delete, `compose down -v`, SurrealDB-Mutationen
- LR: NO-GO (unverändert)

## Preflight

| Check | Ergebnis |
|---|---|
| Backup | `F:\Claire_Backups\cdb_backup_20260701_022424.zip` — 129 775 436 B; manifest Redis+Postgres PASS |
| Compose-Projekt | `claire_de_binare` (nicht `cdb-blue` aus Compose `name:`) — Recreate mit `-p claire_de_binare` |
| Volume | `claire_de_binare_redis_data` → `/data` |
| SECRETS_PATH | vorhanden (nicht geloggt) |
| Postgres (unchanged) | `postgres:15.18-alpine@sha256:df7bca0066e6…` |

## Before Baseline

| Item | Wert |
|---|---|
| Image | `redis:7.4.9-alpine@sha256:6ab0b6e7381779332f97b8ca76193e45b0756f38d4c0dcda72dbb3c32061ab99` |
| PING | PONG |
| DBSIZE | 12 |
| redis_version | 7.4.9 |
| market_state:BTCUSDT | string |

### Stream XLEN (Before)

| Stream | XLEN |
|---|---|
| stream.candles_1m | 100030 |
| stream.regime_signals | 10042 |
| stream.signals | 10009 |
| stream.orders | 10013 |
| stream.allocation_decisions | 252 |
| stream.order_results | 10013 |
| stream.fills | 10013 |
| stream.orders_blocked | 10010 |

## Phase 1 — Volume Tarball

| Feld | Wert |
|---|---|
| Pfad | `artifacts/redis_rebuild_3594_20260701_023436/redis_data_full.tar.gz` |
| Größe | 16 141 604 B |
| SHA256 | `DAF7A6C4415379D354DF377BB6F6427CBB5DD69E8CDE9D5AA68F862E19F4B4DF` |

## Phase 2 — Recreate

```powershell
docker stop cdb_redis
docker compose -p claire_de_binare -f infrastructure/compose/compose.blue.yml up -d --force-recreate --no-deps cdb_redis
```

After Image: `redis:8.8.0-alpine@sha256:9d317178eceac8454a2284a9e6df2466b93c745529947f0cd42a0fa9609d7005`

AOF-Log: keine Parse-/Format-Fehler; `Ready to accept connections`

## Phase 3 — After Validation

| Gate | Ergebnis |
|---|---|
| PING | PONG |
| DBSIZE | 12 |
| redis_version | 8.8.0 |
| AOF | clean |
| market_state:BTCUSDT | string |

### Stream XLEN (After)

| Stream | Before | After |
|---|---|---|
| stream.candles_1m | 100030 | 100031 |
| stream.regime_signals | 10042 | 10043 |
| stream.signals | 10009 | 10009 |
| stream.orders | 10013 | 10013 |
| stream.allocation_decisions | 252 | 254 |
| stream.order_results | 10013 | 10013 |
| stream.fills | 10013 | 10013 |
| stream.orders_blocked | 10010 | 10010 |

Stream-Probe: `XREVRANGE stream.candles_1m + - COUNT 1` liefert Eintrag (read-only).

## Phase 4 — Dependents

Alle geprüften Services healthy — kein sequentieller Restart erforderlich:

`cdb_db_writer`, `cdb_candles`, `cdb_regime`, `cdb_allocation`, `cdb_signal`, `cdb_risk`, `cdb_execution`, `cdb_paper_runner`, `cdb_market`, `cdb_ws`

Postgres unverändert: `postgres:15.18-alpine`, healthy.

## Phase 5 — Stack Verify

```
.\tools\cdb.ps1 stack verify -Verbose
Services healthy: 10/10
Stack is healthy
Exit code: 0
```

Logging overlay (cdb_loki/cdb_promtail) excluded per default — bekannt, non-blocking.

## Ergebnis

**PASS** — Redis runtime rebuild #3594 abgeschlossen. #3600 (Postgres rebuild) bleibt offen.
