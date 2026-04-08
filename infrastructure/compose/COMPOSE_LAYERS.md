# Docker Compose Layer Architecture

## Overview

The Claire de Binare stack uses a **multi-layer compose architecture** to separate concerns and enable flexible configuration for different environments and use cases.

## Canonical Runtime (Use These)

The normal operator/runtime path is **BLUE+RED**:
- **`infrastructure/compose/compose.blue.yml`** - Core trading stack
- **`infrastructure/compose/compose.red.yml`** - Optional signals + monitoring

See `infrastructure/docs/BLUE_RED_SPLIT.md` for the full architecture.

## Canonical Docker CI Lab Baseline

For 431B, the canonical Docker CI lab baseline is:
- **`infrastructure/compose/base.yml` + `infrastructure/compose/test.yml`**
  - Shared infra base plus isolated `_test` services
  - Separate `cdb_test_network` and test-only volumes
  - Containerized pytest execution via `cdb_test_runner` and `Dockerfile.test`

### Shared Base Layer
- **`infrastructure/compose/base.yml`** - Shared base configuration
  - Core infrastructure services (Redis, Postgres, Prometheus, Grafana)
  - Production-ready defaults (no port bindings, secret-based auth)
  - Healthchecks for infrastructure services
  - Network: `cdb_network` (bridge)
  - Shared by local overlays and the canonical CI lab baseline

### Canonical Test Overlay
- **`infrastructure/compose/test.yml`** - Canonical 431B CI lab overlay
  - `_test` service variants for isolated E2E execution
  - `cdb_test_runner` executes pytest inside the lab
  - Uses `Dockerfile.test` as the existing runner image
  - Preferred over `dev.yml` when the goal is an isolated CI/test lab

### Secondary Dev/Compatibility Overlay
- **`infrastructure/compose/dev.yml`** - Development profile
  - Port bindings for local access (127.0.0.1 only)
  - Application services:
    - Active: cdb_signal, cdb_risk, cdb_execution, cdb_db_writer
    - Disabled (missing config): cdb_allocation, cdb_regime
    - Disabled (not implemented): cdb_ws, cdb_market, cdb_paper_runner
  - Debug volumes (logs mounted for easy access)
  - Port mappings: Fixed to match Dockerfile EXPOSE directives (PORT:PORT instead of PORT:8000)
  - Still used by some older/secondary workflow paths, but not the canonical 431B baseline

### Feature Overlays
- **`infrastructure/compose/logging.yml`** - Centralized logging
  - Loki log aggregation server
  - Promtail log collector (scrapes Docker container logs)
  - 7-day retention policy
  - Direct usage: `docker compose -f infrastructure/compose/compose.blue.yml -f infrastructure/compose/logging.yml up -d`

- **`infrastructure/compose/network-prod.yml`** - Network isolation
  - Sets all services to `internal: true` (no external access)
  - For production deployments only
  - Direct usage: `docker compose -f infrastructure/compose/compose.blue.yml -f infrastructure/compose/network-prod.yml up -d`

- **`infrastructure/compose/healthchecks-strict.yml`** - Strict health dependencies
  - Adds `depends_on` with `condition: service_healthy`
  - Prevents cascade failures during startup
  - Direct usage: `docker compose -f infrastructure/compose/compose.blue.yml -f infrastructure/compose/healthchecks-strict.yml -f infrastructure/compose/healthchecks-mounts.yml up -d`

- **`infrastructure/compose/healthchecks-mounts.yml`** - External healthcheck scripts
  - Mounts `infrastructure/healthchecks/` directory for custom scripts
  - Used together with `healthchecks-strict.yml`
  - Example: `db_writer_redis_ping.py`

- **`infrastructure/compose/rollback.yml`** - Tag-based rollback
  - Overrides image tags for fast rollback
  - Generated dynamically by `stack_rollback.ps1`
  - Not committed to Git

### Standalone Stacks
- **`infrastructure/compose/surrealdb.yml`** - SurrealDB sidecar stack (cdb_database)
  - Joins existing `cdb_network` from base stack (external)
  - No port bindings by default
  - Use `surrealdb-dev.yml` for localhost-only ports
  - Requires secrets via `SECRETS_PATH/SURREALDB_ENV`

## Legacy Files (Deprecated - Do Not Use)

### ⚠️ `docker-compose.base.yml`
- **Status**: LEGACY - Use `infrastructure/compose/base.yml` instead
- **Reason**: Located at project root, mixing concerns
- **Migration**: All configs migrated to `infrastructure/compose/base.yml`
- **Will be removed**: After final migration verification

### ⚠️ `docker-compose.yml` (if exists)
- **Status**: LEGACY - Use `infrastructure/compose/base.yml` + overlays
- **Reason**: Monolithic, no separation of concerns
- **Migration**: Split into base.yml + dev.yml
- **Will be removed**: After migration

### ⚠️ `docker-compose.dev.yml` (if exists)
- **Status**: LEGACY - Use `infrastructure/compose/dev.yml`
- **Reason**: Located at project root
- **Migration**: Moved to `infrastructure/compose/dev.yml`
- **Will be removed**: After migration

## Usage

### Local Runtime (Default)
```powershell
docker compose -f infrastructure/compose/compose.blue.yml up -d
docker compose -f infrastructure/compose/compose.red.yml up -d
```

### Docker CI Lab Baseline (431B)
```powershell
docker compose `
  -f infrastructure/compose/base.yml `
  -f infrastructure/compose/test.yml `
  up --abort-on-container-exit
```

### Secondary Dev/Compatibility Path
```powershell
docker compose `
  -f infrastructure/compose/base.yml `
  -f infrastructure/compose/dev.yml `
  up -d
```
This path remains valid for local/dev-oriented flows and older CI consumers, but is not the canonical 431B baseline.

### With Logging Overlay
```powershell
docker compose -f infrastructure/compose/compose.blue.yml -f infrastructure/compose/logging.yml up -d
docker compose -f infrastructure/compose/compose.red.yml up -d
```
Adds:
- Services: Loki + Promtail (via `logging.yml`)
- Access Loki: `http://localhost:3100` (via Grafana)

### With Network Isolation + Strict Healthchecks
```powershell
docker compose -f infrastructure/compose/compose.blue.yml -f infrastructure/compose/network-prod.yml -f infrastructure/compose/healthchecks-strict.yml -f infrastructure/compose/healthchecks-mounts.yml up -d
docker compose -f infrastructure/compose/compose.red.yml up -d
```
Adds:
- `infrastructure/compose/network-prod.yml` (internal network)
- `infrastructure/compose/healthchecks-strict.yml` (strict dependencies)
- `infrastructure/compose/healthchecks-mounts.yml` (custom healthchecks)

## Architecture Principles

### 1. Separation of Concerns
- **Base**: Common infrastructure across all environments
- **Profile**: Environment-specific settings (dev/prod)
- **Overlays**: Optional features that can be mixed-and-matched

### 2. Security by Default
- No port bindings in base.yml (prevents accidental exposure)
- Secret-based authentication only (no plaintext passwords)
- Dev profile binds to 127.0.0.1 only (localhost-only)

### 3. Composability
- Each overlay is self-contained
- Overlays can be combined freely
- No conflicts between overlays

### 4. Git-Friendly
- Configuration files are committed
- Secrets are NOT committed (external files in `~/Documents/.secrets/.cdb/`, via `SECRETS_PATH`)
- Generated files (rollback-temp.yml) are gitignored

## File Hierarchy

```
Claire_de_Binare/
├── docker-compose.base.yml         [LEGACY - do not use]
├── docker-compose.yml              [LEGACY - do not use]
├── docker-compose.dev.yml          [LEGACY - do not use]
└── infrastructure/
    ├── compose/
    │   ├── base.yml                ✓ Shared base
    │   ├── test.yml                ✓ Canonical 431B CI lab overlay
    │   ├── dev.yml                 ✓ Secondary dev/compat overlay
    │   ├── logging.yml             ✓ Loki + Promtail overlay
    │   ├── network-prod.yml        ✓ Network isolation overlay
    │   ├── healthchecks-strict.yml ✓ Strict healthcheck overlay
    │   ├── healthchecks-mounts.yml ✓ Healthcheck mounts overlay
    │   ├── rollback.yml            ✓ Rollback overlay (tag-based)
    │   └── COMPOSE_LAYERS.md       ← This file
    ├── healthchecks/
    │   └── db_writer_redis_ping.py
    ├── monitoring/
    │   ├── prometheus.yml
    │   ├── loki-config.yml
    │   ├── promtail-config.yml
    │   └── grafana/
    └── scripts/
        └── stack_up.ps1            [Legacy helper — nicht der kanonische Operatorpfad]
```

## Overlay Development Guidelines

When creating a new overlay:

1. **Name**: Descriptive, kebab-case (e.g., `feature-name.yml`)
2. **Location**: `infrastructure/compose/`
3. **Documentation**: Add to this file
4. **Self-contained**: Don't depend on other overlays (except base)
5. **Comment**: Add header comment explaining purpose and direct usage

Example overlay header:
```yaml
# Feature Name Overlay
# Brief description of what this overlay does
# Usage: docker compose -f infrastructure/compose/compose.blue.yml -f infrastructure/compose/feature-name.yml up -d
```

## Migration Path (Legacy → Canonical)

**Status:** Abgeschlossen. BLUE+RED ist der kanonische Operator-Runtime-Pfad.
Legacy-Dateien (`docker-compose.base.yml`, `docker-compose.yml`, `docker-compose.dev.yml`) sind deprecated und nicht mehr aktiv genutzt.

## Secret Management

Kanonischer Secrets-Pfad: `~/Documents/.secrets/.cdb/` (via `SECRETS_PATH`-Umgebungsvariable)
- `REDIS_PASSWORD`
- `POSTGRES_PASSWORD`
- `GRAFANA_PASSWORD`

Secret files are referenced in compose as:
```yaml
secrets:
  redis_password:
    file: ${SECRETS_PATH}/REDIS_PASSWORD
```

`SECRETS_PATH` wird beim Stack-Start gesetzt (z.B. durch `tools/stack_boot.ps1` oder manuell).

**NEVER commit secrets to Git!**

## Troubleshooting

### Issue: "secret file does not exist"
**Cause**: Incorrect relative path to secret files
**Fix**: Ensure paths in compose files use correct `../../` levels

### Issue: "both PASSWORD and PASSWORD_FILE are set"
**Cause**: OS environment has plaintext PASSWORD variable
**Fix**: Remove `POSTGRES_PASSWORD` and `REDIS_PASSWORD` from Windows User environment

### Issue: Legacy files being used
**Cause**: Old scripts or manual docker-compose commands
**Fix**: Use canonical BLUE+RED path: `docker compose -f infrastructure/compose/compose.blue.yml up -d && docker compose -f infrastructure/compose/compose.red.yml up -d`

## See Also

- `LEGACY_FILES.md` - Migration guide for deprecated files
- `DOCKER_STACK_RUNBOOK.md` - Operational procedures
