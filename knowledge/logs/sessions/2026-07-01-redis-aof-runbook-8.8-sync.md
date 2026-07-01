# Session Log: 2026-07-01 — Redis AOF Runbook 8.8 SSOT Sync

## Auftrag

Docs-only: `redis_aof_corruption_recovery.md` Image-Pin von `7.4.9` auf aktuelle Compose-SSOT `8.8.0` nachziehen. Nebenan: `.pg15_archived/` read-only analysieren (kein Delete).

## Delivered

| Datei | Änderung |
|---|---|
| `docs/runbooks/redis_aof_corruption_recovery.md` | Incident-Historie 7.4.9 beibehalten; Current SSOT + Recovery-One-off auf `redis:8.8.0-alpine@sha256:9d317178…`; Ref #3594 |

## `.pg15_archived/` Analyse (read-only, kein Delete)

| Feld | Wert |
|---|---|
| Volume | `claire_de_binare_postgres_data` |
| Pfad | `/data/.pg15_archived/` |
| Größe | ~951 MB |
| Inhalt | PG15-Cluster-Dateien (archiviert bei #3600 Migration) |
| Aktive PG18-Daten | `/data/18/` (neues Layout) |
| Backup-Referenz | `F:\Claire_Backups\cdb_backup_20260701_024024.zip` + Volume-Tarball `artifacts/postgres_rebuild_3600_20260701_024237/` |

**Empfehlung:** `.pg15_archived/` vorerst belassen. Cleanup nur in separatem Ops-GO nach verifizierter PG18-Stabilität und Backup-Frische.

## Validation

- Docs-only diff
- Keine Runtime-Mutation

## Boundaries

- LR NO-GO unchanged
- Kein Volume-Delete, kein Postgres-Touch
