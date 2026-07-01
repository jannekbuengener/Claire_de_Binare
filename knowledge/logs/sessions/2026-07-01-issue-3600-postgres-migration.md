# Session Log: 2026-07-01 — Issue #3600 Postgres Runtime Migration

## Auftrag

Operator-GO Phase 3: `cdb_postgres` Migration von `postgres:15.18-alpine` auf `postgres:18.4-alpine` (PR #3530 Nachzug) via dump/restore. Volume `claire_de_binare_postgres_data`; Backup-Basis `F:\Claire_Backups\cdb_backup_20260701_024024.zip`. Closes #3600 bei PASS.

## Scope / Boundaries

- Autorisiert: Postgres stop/recreate, Volume-Tarball, pg_dump restore, Validierung, Stack verify, Issue close
- Nicht autorisiert: Volume delete (`-v`), Redis restore from backup (Redis bereits #3594 auf 8.8.0), LR/Live-Go
- LR: NO-GO (unverändert)

## Preflight

| Check | Ergebnis |
|---|---|
| Backup (pre-migration) | `F:\Claire_Backups\cdb_backup_20260701_024024.zip` — Postgres+Redis PASS, 123.76 MB |
| Volume tarball | `artifacts/postgres_rebuild_3600_20260701_024237/postgres_data_full.tar.gz` — 194 452 677 B, SHA256 `41335A0D3E2DB3BC9BCFFF7C1B0EBC0A3A55DD3D6D1FE57E9AD69C349CD81D6B` |
| Compose-Projekt | `claire_de_binare` |
| Redis (unchanged) | `redis:8.8.0-alpine` healthy (#3594) |

## Before Baseline (PG15)

| Item | Wert |
|---|---|
| Image | `postgres:15.18-alpine` |
| Mount | `claire_de_binare_postgres_data` → `/var/lib/postgresql/data` |
| orders | 10511 |
| trades | 9963 |
| signals | 221161 |

## Migration Steps

1. `make backup` → `cdb_backup_20260701_024024.zip`
2. Stopped: `cdb_db_writer`, `cdb_execution`, `cdb_risk`, `cdb_paper_runner`, `cdb_signal`, `cdb_reports`, `cdb_postgres_exporter`, `cdb_postgres`
3. First recreate → **PG18 crash loop** (PG15 data at volume root incompatible with PG18 mount layout)
4. Archived PG15 cluster files to volume `.pg15_archived/` (tarball + pg_dump retained)
5. Second recreate → PG18 fresh init on `/var/lib/postgresql` — healthy
6. Restore: `docker cp` dump + `psql -f /tmp/postgres_dump.sql` (exit 0, ~4 min)

## After Validation (PG18)

| Gate | Ergebnis |
|---|---|
| Image | `postgres:18.4-alpine@sha256:1b1689b20d16a014a3d195653381cf2caa75a41a92d93b255a9d6ea29fd353aa` |
| Version | PostgreSQL 18.4 |
| Mount | `claire_de_binare_postgres_data` → `/var/lib/postgresql` |
| orders | 10511 (match) |
| trades | 9963 (match) |
| signals | 221161 (match) |
| stack verify | 10/10 healthy, exit 0 |

## Ergebnis

**PASS** — Postgres runtime migration #3600 abgeschlossen. Runtime matches repo compose pins for both data layer services (Redis 8.8.0 + Postgres 18.4).

## Restgaps (non-blocking)

- `cdb_redis_exporter` weiterhin unhealthy (pre-existing)
- Volume enthält `.pg15_archived/` — optional cleanup in separatem Ops-GO
- `stack verify` Volumes/Networks count 0/6 — verify-script quirk, services 10/10 OK
