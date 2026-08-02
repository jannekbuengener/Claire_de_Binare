# PG15 Archive Cleanup Runbook

**Scope:** Read-only preflight and operator checklist for removing `/data/.pg15_archived/` after PG18 migration (#3600).
**Issue:** #3612

## Overview

After the Postgres 15 → 18 migration (#3600), the archived PG15 cluster lives at
`/data/.pg15_archived/` inside the Postgres volume. The active PG18 cluster runs
from `/data/18/`. The archive is a temporary rollback reserve only.

This runbook authorizes **preflight evaluation only**. Actual deletion requires a
separate explicit Operator-GO and is out of scope for the preflight tool.

## Read-only Contract

The preflight tool (`tools/postgres/pg15_archive_cleanup_preflight.py`):

- evaluates operator-supplied evidence only
- performs **no** deletes, volume mutations, restores, or live DB queries
- never generates `docker volume rm`, `compose down -v`, `rm -rf`, or restore commands
- always sets `operator_go_required: true`

## Retention Gate

Do not schedule cleanup before **2026-07-15** (14 days stable PG18 per #3612).

## Required Evidence (operator-collected)

| Check | Source |
|---|---|
| Retention window | `check_as_of` date ≥ 2026-07-15 |
| Backup health | `make backup-health` → PASS |
| Fresh backup | `make backup` → recent `cdb_backup_*.zip` path |
| Backup reference | manifest/ZIP verified against `docs/runbooks/BACKUP_AUTOMATION.md` |
| PG18 image | `postgres:18.4-alpine` (compose SSOT) |
| PG18 health | container healthy + `pg_isready` |
| Active cluster | `/data/18/` |
| Row counts | `orders`, `trades`, `signals` match migration baseline |
| Archive reference | `.pg15_archived` must **not** appear in runtime compose/mount config |

### Migration baseline row counts (#3600)

| Table | Count |
|---|---|
| orders | 10511 |
| trades | 9963 |
| signals | 221161 |

## Preflight Usage

Create a JSON evidence file (example `pg15_cleanup_inputs.json`):

```json
{
  "check_as_of": "2026-07-31",
  "backup_health_pass": true,
  "fresh_backup_reference": "F:/Claire_Backups/cdb_backup_20260731_120000.zip",
  "backup_reference_verified": true,
  "pg_image": "postgres:18.4-alpine@sha256:ecafd34249b5",
  "pg_healthy": true,
  "pg_isready": true,
  "active_cluster_path": "/data/18/",
  "row_counts": {
    "orders": 10511,
    "trades": 9963,
    "signals": 221161
  }
}
```

Run:

```bash
python -m tools.postgres.pg15_archive_cleanup_preflight --input pg15_cleanup_inputs.json --json
```

Exit `0` → `READY_FOR_OPERATOR_CLEANUP_GO` (still requires separate Operator-GO for delete).
Exit `1` → one or more `NOT_READY_*` reason codes.

## Reason Codes

| Code | Meaning |
|---|---|
| `READY_FOR_OPERATOR_CLEANUP_GO` | All checks passed; operator may proceed to separate cleanup GO |
| `NOT_READY_RETENTION` | Retention window not met |
| `NOT_READY_BACKUP` | Backup health or fresh backup reference missing/unverified |
| `NOT_READY_PG18_HEALTH` | PG18 image/health/`pg_isready` evidence insufficient |
| `NOT_READY_CLUSTER_PATH` | Active cluster path is not `/data/18/` |
| `NOT_READY_ROW_COUNTS` | Row-count sanity mismatch or missing |
| `NOT_READY_ARCHIVE_REFERENCE` | Archive path referenced by runtime config |

## Authorized Future Cleanup Shape (Operator-GO only)

When a separate cleanup GO is granted:

- **target:** `/data/.pg15_archived/` only
- **forbidden:** `docker volume rm`, `compose down -v`, full volume delete, Postgres recreate without separate justification, Redis/SurrealDB mutation

## Hard Non-Goals

- Do not delete during preflight.
- Do not remove the Postgres data volume.
- Do not run destructive restore.
- Do not mutate Redis or SurrealDB.
- Do not change LR status.
- Do not touch live/echtgeld paths.
- Do not print secrets.

## Related

- Backup automation: [`BACKUP_AUTOMATION.md`](./BACKUP_AUTOMATION.md)
- Migration evidence: `knowledge/logs/sessions/2026-07-01-issue-3600-postgres-migration.md`
- Issue: #3612
