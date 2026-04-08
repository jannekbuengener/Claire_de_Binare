# Tools

Authoritative repo-wide PowerShell index for Claire de Binare.

Scope:
- Discovery and navigation for repo-local PowerShell entrypoints.
- Classification only; this file does not change script behavior.

Important:
- `Makefile` is the operative front door for common runtime flows such as `make docker-up`, `make docker-health`, and `make docker-down`.
- `Makefile` is not itself part of the PowerShell v1 toolchain.
- The canonical 431B Docker CI lab baseline is `infrastructure/compose/base.yml` + `infrastructure/compose/test.yml`; it sits outside the PowerShell v1 toolchain.
- The canonical 431C security simulation source of truth is repo-native under `scripts/drills/` + `tests/chaos/`.
- `tools/test_pack/` remains an experimental/secondary drill pack and is not the repo-wide default verification path.

## Canonical v1 Front Door

- `tools/cdb.ps1` - Thin Windows/PowerShell dispatcher for the canonical v1 corridor.

| Command | Underlying script |
|---------|-------------------|
| `.\tools\cdb.ps1 secrets init` | `infrastructure/scripts/init-secrets.ps1` |
| `.\tools\cdb.ps1 runtime up` | `infrastructure/scripts/setup_blue_red.ps1` |
| `.\tools\cdb.ps1 stack verify` | `tools/verify_stack.ps1` |
| `.\tools\cdb.ps1 service logs -ServiceName cdb_risk -Lines 100` | `tools/cdb-service-logs.ps1` |
| `.\tools\cdb.ps1 runtime smoke` | `infrastructure/scripts/smoke_test.ps1` |

Non-interactive form:
- `pwsh -ExecutionPolicy Bypass -File .\tools\cdb.ps1 runtime up`

## Canonical v1 Scripts

- `infrastructure/scripts/init-secrets.ps1` - Initialize local secrets in `~/Documents/.secrets/.cdb`.
- `infrastructure/scripts/setup_blue_red.ps1` - Canonical PowerShell runtime entrypoint for the BLUE+RED stack.
- `tools/verify_stack.ps1` - Verify Docker stack health, expected volumes, networks, and optional endpoints.
- `tools/cdb-service-logs.ps1` - Read focused service logs during runtime diagnosis.
- `infrastructure/scripts/smoke_test.ps1` - Validate the current BLUE core flow path. This does not validate the full BLUE+RED stack end-to-end.

## Secrets Entrypoints

- `infrastructure/scripts/manage_secrets.ps1` - **Primary CRUD / Ops entrypoint** for secret setup, single-secret rotation, validation, and listing.
- `tools/secrets/Rotate-Secrets.ps1` - **Primary Rotation / Export entrypoint** for plan/apply bulk rotation and `.env.runtime` export.
- `scripts/manage_secrets.ps1` - Compat copy of the infrastructure version; prefer the infrastructure path.
- `tools/set_secrets.ps1` - Secondary legacy interactive setup helper.

## Secondary

- `infrastructure/scripts/bootstrap_local.ps1` - Secondary convenience wrapper; not the canonical PowerShell v1 front door.
- `infrastructure/scripts/bootstrap_local.sh` - Secondary non-Windows bootstrap helper; retains legacy convenience behavior and is not the PowerShell v1 front door.
- `tools/cdb-stack-doctor.ps1` - Broader ad-hoc stack diagnostics helper outside the v1 corridor.
- `scripts/secrets/sync_cdb_secrets.ps1` - Repo-local helper for syncing GitHub Actions secrets when PAT fallback is used.

## Legacy/Stale

- `infrastructure/scripts/legacy/cdb-secrets-sync.ps1` - Former sync helper; moved from `tools/` per #1404; not an active operator path.
- `infrastructure/scripts/stack_up.ps1` - Older PowerShell stack launcher; keep for reference, not as the v1 discovery default.
- `infrastructure/scripts/stack_verify.ps1` - Older verification path; use `tools/verify_stack.ps1` for v1 discovery.
- `infrastructure/scripts/stack_doctor.ps1` - Older infra-local diagnostic entrypoint; prefer `tools/cdb-stack-doctor.ps1` when that style of helper is needed.
- `tools/stack_boot.ps1` - Legacy bootstrap helper; not the canonical BLUE+RED runtime entrypoint.
