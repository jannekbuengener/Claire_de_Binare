# Session Log: 2026-07-01 — Backup Manifest Redis Drift (#3614)

## Auftrag

Fix `Components.Redis=false` while `redis_dump.rdb` present in backup ZIP (`cdb_backup_20260701_030012.zip`). Closes #3614.

## Root Cause

`docker cp` can write `redis_dump.rdb` successfully while `$LASTEXITCODE` is non-zero on Windows. Manifest was written from `$componentStatus` without artifact reconciliation.

## Delivered

- `infrastructure/scripts/backup_manifest_helpers.ps1` — `Test-BackupArtifactPresent`, `Sync-BackupComponentManifest`, `Resolve-BackupComponentInclusion`
- `backup_all.ps1` — artifact-based Redis success + sync before manifest
- `restore_all.ps1` — legacy drift tolerance when artifact present but flag false
- `tests/unit/scripts/test_backup_manifest_sync.py` — 5 unit tests
- `docs/runbooks/BACKUP_AUTOMATION.md` — Components vs ComponentSelection note

## Validation

- `pytest -m unit tests/unit/scripts/test_backup_manifest_sync.py` — 5/5 PASS
- No runtime mutation, no restore drill

## Boundaries

- LR NO-GO; no Docker/backup/restore execution in session
