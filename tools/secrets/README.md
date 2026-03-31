# cdb-secrets-rotator

Automated secret rotation tool with governance guardrails for Claire de Binare.

## Overview

This tool rotates **machine-readable secrets** (DB passwords, Redis, app keys) while protecting **manual secrets** (Grafana admin password stored in password manager/browser).

**Canonical secrets path:** `C:\Users\janne\Documents\.secrets\.cdb`

## Quickstart

### 1. Incident / Leak Response
```powershell
# Plan what will be rotated
.\tools\secrets\Rotate-Secrets.ps1 plan

# Apply rotation and auto-export (auto secrets only)
.\tools\secrets\Rotate-Secrets.ps1 apply -ExportAfter

# Restart stack (canonical BLUE+RED runtime)
docker network create cdb_network 2>$null
docker compose -f infrastructure/compose/compose.blue.yml up -d
docker compose -f infrastructure/compose/compose.red.yml up -d
```

### 2. Normal Stack Start
```powershell
# Canonical BLUE+RED runtime
docker network create cdb_network 2>$null
docker compose -f infrastructure/compose/compose.blue.yml up -d
docker compose -f infrastructure/compose/compose.red.yml up -d
```

### 3. Audit Current Secrets
```powershell
# Show what would be rotated (dry-run)
.\tools\secrets\Rotate-Secrets.ps1 plan
```

## Commands

### `plan`
Shows what secrets would be rotated, which services would be restarted, and which secrets are manual.

**Example:**
```powershell
.\Rotate-Secrets.ps1 plan
```

### `apply`
Rotates all auto secrets (rotation_mode=auto, exclude_by_default=false) and writes new values to `$SECRETS_PATH`.

**Hard-fail protection:** `--IncludeManual` flag is FORBIDDEN and will cause immediate error.

**Flags:**
- `--ExportAfter` (Alias: `--Export`): Automatically run export after successful rotation

**Example:**
```powershell
# Apply only (manual export needed)
.\Rotate-Secrets.ps1 apply

# Apply + auto-export (recommended for incidents)
.\Rotate-Secrets.ps1 apply -ExportAfter
```

### `export`
Generates `.env.runtime` file with all auto secrets for injection into Docker stack.

**Example:**
```powershell
.\Rotate-Secrets.ps1 export
```

## Governance Rules

### ✅ What Gets Rotated (AUTO)
- `REDIS_PASSWORD` - Redis pub/sub + streams (all services)
- `POSTGRES_PASSWORD` - PostgreSQL database
- `POSTGRES_PASSWORD_DSN` - PostgreSQL DSN connection string
- *(Future: App signing keys, webhook secrets, etc.)*

### ❌ What Does NOT Get Rotated (MANUAL)
- `GRAFANA_ADMIN_PASSWORD` - Stored in password manager/browser
  - **Runbook:** `knowledge/runbooks/GRAFANA_ADMIN_INCIDENT.md`
  - Only rotate on confirmed incident/leak
  - Update password manager entry after manual rotation

### 🔒 Guardrails (Technically Enforced)

1. **Fail-closed**: Missing manifest fields → hard-fail before apply
2. **Repo stays value-free**: Secrets never written to git-tracked files
3. **Explicit allowlist**: Only manifest-defined secrets are touched
4. **Safe logging**: Logs show names/lengths/hashes, NEVER values
5. **Two-step workflow**: `plan` shows changes → `apply` executes
6. **Idempotent**: Repeated `apply` = zero changes (same length check)
7. **Manual protection**: `--IncludeManual` → immediate hard-fail

## Files

| File | Purpose |
|------|---------|
| `Rotate-Secrets.ps1` | Core rotation logic (plan/apply/export) |
| `secrets.manifest.json` | Secret definitions (auto/manual, restart scope) |
| `.env.runtime` | Generated runtime ENV file (gitignored) |
| `README.md` | This file |

## Integration

### With BLUE+RED Runtime
The canonical runtime (`compose.blue.yml` + `compose.red.yml`) loads secrets from `SECRETS_PATH`.
- Disable `.env.runtime` auto-load via: `$env:CDB_IGNORE_RUNTIME_ENV=1`

### Active Secret Management Entrypoints

| Entrypoint | Role | Scope |
|---|---|---|
| `infrastructure/scripts/manage_secrets.ps1` | **Primary CRUD / Ops** | setup, rotate single secret, validate, list |
| `tools/secrets/Rotate-Secrets.ps1` | **Primary Rotation / Export** | plan/apply bulk rotation, export `.env.runtime` |
| `scripts/manage_secrets.ps1` | Compat copy | Same as infrastructure version; prefer the infrastructure path |
| `tools/set_secrets.ps1` | Secondary | Legacy interactive setup helper |

### Legacy / Reference-Only
- `infrastructure/scripts/legacy/cdb-secrets-sync.ps1` — moved from `tools/` per #1404; not an active operator path

## Evidence / Audit Trail

All operations log:
- Secret names (safe)
- Lengths (safe)
- Actions (CREATE/UPDATE/SKIP)
- Affected services

**Never logged:**
- Secret values
- Partial values
- Hashes of values (could leak entropy)

## Troubleshooting

### "Secrets path does not exist"
```powershell
mkdir "C:\Users\janne\Documents\.secrets\.cdb"
```

### "Manifest validation failed"
Check `secrets.manifest.json` for:
- Missing required fields (name, rotation_mode, format, bytes)
- Invalid rotation_mode (must be "auto" or "manual")

### "Secret file missing after apply"
Run commands in order:
1. `apply` (generates secrets)
2. `export` (creates .env.runtime)
3. Start BLUE+RED runtime (`docker compose -f infrastructure/compose/compose.blue.yml up -d` + `compose.red.yml`)

## Related Documentation

- **Grafana Admin Incident Runbook (MANUAL rotation)**
  `knowledge/runbooks/GRAFANA_ADMIN_INCIDENT.md`

**Note:** The former Docs Hub repository is retired. All active governance
and runbook content lives in this working repo.
