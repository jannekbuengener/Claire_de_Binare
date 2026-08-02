# Infrastructure Scripts (`infrastructure/scripts/`)

Operator scripts for stack lifecycle, backup/DR, smoke, and evidence — prefer [`tools/cdb.ps1`](../../tools/cdb.ps1) as Windows front door where noted.

## Canonical v1 (BLUE+RED)

| Script | Purpose |
|---|---|
| [`setup_blue_red.ps1`](setup_blue_red.ps1) | Start canonical BLUE+RED stack |
| [`smoke_test.ps1`](smoke_test.ps1) | BLUE core smoke |
| [`run_e2e.ps1`](run_e2e.ps1) | E2E stack + pytest wrapper |
| [`init-secrets.ps1`](init-secrets.ps1) | Local secrets bootstrap |

## Backup / DR

| Script | Purpose |
|---|---|
| [`backup_all.ps1`](backup_all.ps1) | Postgres + Redis backup |
| [`backup_health_check.ps1`](backup_health_check.ps1) | Backup freshness |
| [`dr_backup.ps1`](dr_backup.ps1) / [`dr_restore.ps1`](dr_restore.ps1) | DR flows |

## Evidence / reporting

| Script | Purpose |
|---|---|
| [`generate_shadow_digest.py`](generate_shadow_digest.py) | Shadow daily digest — see [`README_SHADOW_DIGEST.md`](README_SHADOW_DIGEST.md) |
| [`build_shadow_evidence_package.py`](build_shadow_evidence_package.py) | Shadow evidence pack |

## Legacy (reference only)

| Path | Notes |
|---|---|
| [`legacy/`](legacy/) | Quarantined helpers — not v1 discovery default |
| [`legacy/smart_startup.py`](legacy/smart_startup.py) | Single-compose-era startup; fail-closed quarantine (#4125) |
| [`stack_up.ps1`](stack_up.ps1) | Superseded by `setup_blue_red.ps1` |

Repo-root helpers such as `smart_health_check.py`, project PowerShell automation,
`check_core_duplicates.py`, and `dimensionality_audit/` own under [`scripts/`](../../scripts/README.md).
Do not reintroduce identical copies here; Rule 3 in `scripts/check_core_duplicates.py`
guards against new exact clones.

## Related

- [`tools/README.md`](../../tools/README.md)
- [`scripts/README.md`](../../scripts/README.md) — repo-root guards/smoke
- [`infrastructure/compose/README.md`](../compose/README.md)

## SSOT boundary

Scripts do not grant LR/live approval. LR **NO-GO**.
