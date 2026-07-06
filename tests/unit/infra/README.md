# Infra / Compose / Stack / Secrets / Backup Contract Tests

Static and fixture-backed guards for infra ops contracts. Parent meta: **#3855**.

| Slice | Issues | Focus |
|-------|--------|--------|
| Compose BLUE/RED | #3856 | Layer classification, service canon |
| Stack lifecycle | #3857 | Operator gates, fail-closed secrets dir |
| Secrets SSOT | #3858 | `SECRETS_PATH`, canonical path, no secret echo |
| Backup / Restore / DR | #3859 | Manifest drift, destructive gates, artifacts |

## What these tests prove

- Compose layer classification (`canonical_runtime` vs `legacy_ci` / overlays)
- BLUE/RED service canon, network/volume naming, healthcheck posture
- Canonical secrets path `~/Documents/.secrets/.cdb` / `SECRETS_PATH` (not legacy `.cdb_local/.secrets`)
- Docker secrets + env fallback contracts in `core/secrets.py`
- `.env.runtime` export boundary (gitignored, optional — not required for BLUE+RED)
- Backup manifest reconciliation for Postgres / Redis / SurrealDB artifacts
- Restore destructive paths gated (`-Force`, `Read-Host`, explicit `yes`)
- `restore_all.ps1 -ListAvailable` list semantics documented in source
- Scripts do not echo secret payloads

## What these tests do **not** prove

- No real secrets read, rotated, or written
- No `docker compose up/down` — not a runtime or stack-start proof
- No backup or restore execution, no DB writes, no volume deletion
- No container health at execution time
- No operator authorization to mutate production stacks

Run targeted checks:

```bash
pytest -q tests/unit/infra -m contract
pytest -q tests/unit/scripts -k "backup_manifest"
pytest -q tests/unit -k "secret or secrets or SECRETS_PATH or backup or restore or manifest or dr_"
```
