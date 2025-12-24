# Docker Compose Layer Architecture

## Overview

The Claire de Binare stack uses a **multi-layer compose architecture** to separate concerns and enable flexible configuration for different environments and use cases.

## Canonical Files (Use These)

### Base Layer
- **`infrastructure/compose/base.yml`** - Canonical base configuration
  - Core infrastructure services (Redis, Postgres, Prometheus, Grafana)
  - Production-ready defaults (no port bindings, secret-based auth)
  - Healthchecks for infrastructure services
  - Network: `cdb_network` (bridge)

### Profile Overlays
- **`infrastructure/compose/dev.yml`** - Development profile
  - Port bindings for local access (127.0.0.1 only)
  - Application services (cdb_core, cdb_risk, cdb_execution, cdb_db_writer, cdb_paper_runner, cdb_ws)
  - Debug volumes (logs mounted for easy access)

### Feature Overlays
- **`infrastructure/compose/logging.yml`** - Centralized logging
  - Loki log aggregation server
  - Promtail log collector (scrapes Docker container logs)
  - 7-day retention policy
  - Enable with: `stack_up.ps1 -Logging`

- **`infrastructure/compose/network-prod.yml`** - Network isolation
  - Sets all services to `internal: true` (no external access)
  - For production deployments only
  - Enable with: `stack_up.ps1 -NetworkIsolation`

- **`infrastructure/compose/healthchecks-strict.yml`** - Strict health dependencies
  - Adds `depends_on` with `condition: service_healthy`
  - Prevents cascade failures during startup
  - Enable with: `stack_up.ps1 -StrictHealth`

- **`infrastructure/compose/healthchecks-mounts.yml`** - External healthcheck scripts
  - Mounts `infrastructure/healthchecks/` directory for custom scripts
  - Required with `-StrictHealth`
  - Example: `db_writer_redis_ping.py`

- **`infrastructure/compose/rollback.yml`** - Tag-based rollback
  - Overrides image tags for fast rollback
  - Generated dynamically by `stack_rollback.ps1`
  - Not committed to Git

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

### Development (Default)
```powershell
.\infrastructure\scripts\stack_up.ps1
```
Equivalent to:
```powershell
docker-compose `
  -f docker-compose.base.yml `
  -f infrastructure/compose/base.yml `
  -f infrastructure/compose/dev.yml `
  up -d
```

### Development with Logging
```powershell
.\infrastructure\scripts\stack_up.ps1 -Logging
```
Adds:
- `infrastructure/compose/logging.yml`
- Services: Loki + Promtail
- Access Loki: `http://localhost:3100` (via Grafana)

### Production
```powershell
.\infrastructure\scripts\stack_up.ps1 -Profile prod -NetworkIsolation -StrictHealth
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
- Secrets are NOT committed (external files in `../.cdb_local/.secrets/`)
- Generated files (rollback-temp.yml) are gitignored

## File Hierarchy

```
Claire_de_Binare/
├── docker-compose.base.yml         [LEGACY - do not use]
├── docker-compose.yml              [LEGACY - do not use]
├── docker-compose.dev.yml          [LEGACY - do not use]
└── infrastructure/
    ├── compose/
    │   ├── base.yml                ✓ CANONICAL BASE
    │   ├── dev.yml                 ✓ Dev profile
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
        └── stack_up.ps1            ✓ Unified entry point
```

## Overlay Development Guidelines

When creating a new overlay:

1. **Name**: Descriptive, kebab-case (e.g., `feature-name.yml`)
2. **Location**: `infrastructure/compose/`
3. **Documentation**: Add to this file
4. **Switch**: Add to `stack_up.ps1` parameters
5. **Self-contained**: Don't depend on other overlays (except base)
6. **Comment**: Add header comment explaining purpose and usage

Example overlay header:
```yaml
# Feature Name Overlay
# Brief description of what this overlay does
# Usage: stack_up.ps1 -FeatureName
```

## Migration Path (Legacy → Canonical)

### Phase 1: Dual Support (Current)
- Both legacy and canonical files exist
- `stack_up.ps1` uses canonical files
- Old scripts still work with legacy files

### Phase 2: Deprecation Warnings
- Add deprecation headers to legacy files
- Update all documentation to use canonical files
- Create `LEGACY_FILES.md` with migration guide

### Phase 3: Removal
- Remove `docker-compose.base.yml`
- Remove `docker-compose.yml`
- Remove `docker-compose.dev.yml`
- Update CI/CD to use canonical files

**Current Phase**: Phase 2 (Deprecation Warnings)

## Secret Management

All secrets are stored in `../.cdb_local/.secrets/` (workspace-level, outside Git):
- `redis_password` (24 bytes)
- `postgres_password` (empty for existing DB, populated on init)
- `grafana_password` (optional)

Secret files are referenced in compose as:
```yaml
secrets:
  redis_password:
    file: ../../../.cdb_local/.secrets/redis_password  # 3 levels up from infrastructure/compose/
```

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
**Fix**: Use `stack_up.ps1` instead of direct docker-compose

## See Also

- `LEGACY_FILES.md` - Migration guide for deprecated files
- `DOCKER_STACK_RUNBOOK.md` - Operational procedures
- `infrastructure/scripts/stack_up.ps1` - Unified stack launcher
