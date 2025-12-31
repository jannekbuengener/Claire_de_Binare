# Legacy Files - Migration Guide

## Overview

This document lists deprecated files and provides migration paths to the canonical infrastructure.

**Status**: Phase 3 - MIGRATION COMPLETE (2025-12-28)

## Deprecated Docker Compose Files

### `docker-compose.base.yml`

**Status**: ⚠️ DEPRECATED - Do not modify

**Replacement**: `infrastructure/compose/base.yml`

**Reason for Deprecation**:
- Located at project root (breaks separation of concerns)
- Mixed with legacy monolithic compose files
- Duplicate configuration with canonical base.yml

**Migration Path**:
```powershell
# OLD (deprecated)
docker-compose -f docker-compose.base.yml up

# NEW (canonical)
.\infrastructure\scripts\stack_up.ps1
```

**Timeline**:
- ✅ Canonical file created: `infrastructure/compose/base.yml`
- ✅ All configs migrated
- ⏳ Deprecation warnings added
- 🔜 File will be removed after verification period

---

### `docker-compose.yml`

**Status**: ⚠️ LEGACY - If exists, do not use

**Replacement**: `infrastructure/compose/base.yml` + `infrastructure/compose/dev.yml`

**Reason for Deprecation**:
- Monolithic configuration (no environment separation)
- No overlay support
- Hardcoded dev-specific settings

**Migration Path**:
```powershell
# OLD (deprecated)
docker-compose up

# NEW (canonical)
.\infrastructure\scripts\stack_up.ps1
```

**What Changed**:
- Infrastructure services → `infrastructure/compose/base.yml`
- Port bindings → `infrastructure/compose/dev.yml`
- Logging → `infrastructure/compose/logging.yml` (optional overlay)

---

### `docker-compose.dev.yml`

**Status**: ⚠️ DEPRECATED - Do not modify

**Replacement**: `infrastructure/compose/dev.yml`

**Reason for Deprecation**:
- Located at project root
- Not part of infrastructure directory structure

**Migration Path**:
```powershell
# OLD (deprecated)
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# NEW (canonical)
.\infrastructure\scripts\stack_up.ps1 -Profile dev
```

**What Changed**:
- File moved to `infrastructure/compose/dev.yml`
- Port bindings now use 127.0.0.1 (localhost-only)
- Volume paths updated for new location

---

## Deprecated Scripts

### Manual `docker-compose` Commands

**Status**: ⚠️ DISCOURAGED - Use stack_up.ps1 instead

**Replacement**: `infrastructure/scripts/stack_up.ps1`

**Reason for Deprecation**:
- Requires manual specification of all overlay files
- Easy to forget required overlays
- No validation or error checking

**Migration Path**:
```powershell
# OLD (manual, error-prone)
docker-compose -f docker-compose.base.yml -f infrastructure/compose/base.yml -f infrastructure/compose/dev.yml up -d

# NEW (automatic, validated)
.\infrastructure\scripts\stack_up.ps1
```

**Benefits of stack_up.ps1**:
- Automatic overlay selection
- Profile support (-Profile dev/prod)
- Feature toggles (-Logging, -StrictHealth, -NetworkIsolation)
- Validation and error checking
- Consistent experience

---

## Deprecated Environment Patterns

### Plaintext Password Environment Variables

**Status**: ❌ FORBIDDEN - Policy violation

**Replacement**: Docker Secrets (`*_PASSWORD_FILE`)

**Reason for Deprecation**:
- Security policy: No plaintext passwords anywhere
- Conflicts with Docker secrets
- Logs may expose passwords

**Migration Path**:
```powershell
# OLD (forbidden)
Set environment variable: POSTGRES_PASSWORD=mysecret
Set environment variable: REDIS_PASSWORD=mysecret

# NEW (required)
1. REMOVE POSTGRES_PASSWORD from Windows User environment
2. REMOVE REDIS_PASSWORD from Windows User environment
3. Ensure secret files exist:
   ../.cdb_local/.secrets/postgres_password (file with password)
   ../.cdb_local/.secrets/redis_password (file with password)
```

**Verification**:
```powershell
# Check compliance
docker inspect cdb_postgres --format '{{json .Config.Env}}' | Select-String PASSWORD
# Should show: POSTGRES_PASSWORD_FILE=/run/secrets/postgres_password
# Should NOT show: POSTGRES_PASSWORD=...
```

---

### `.env` File in Project Root

**Status**: ⚠️ LEGACY - Prefer OS environment variables

**Replacement**: Windows User-Level Environment Variables

**Reason for Deprecation**:
- User explicitly set all vars at OS level
- .env file creates duplicate sources of truth
- Can conflict with OS environment

**Migration Path**:
```powershell
# OLD (deprecated)
Create .env file at project root with:
POSTGRES_USER=claire_user
POSTGRES_DB=claire_de_binare

# NEW (current)
# User has already set these at Windows User level
# Compose files use env_file: .env only for backward compatibility
# No action needed - OS env vars take precedence
```

---

## Deprecated Directory Structures

### `./.secrets/` (Project-Level)

**Status**: ⚠️ IGNORED - Contains invalid directories

**Replacement**: `../.cdb_local/.secrets/` (Workspace-Level)

**Reason for Deprecation**:
- Contains DIRECTORIES instead of FILES (invalid for Docker secrets)
- Project-level secrets mix with codebase
- Workspace-level allows sharing across projects

**Migration Path**:
```powershell
# OLD (invalid)
./.secrets/redis_password      # Directory (wrong!)
./.secrets/postgres_password   # Directory (wrong!)

# NEW (valid)
../.cdb_local/.secrets/redis_password      # File with 24 bytes
../.cdb_local/.secrets/postgres_password   # File with password
```

**Fix**:
```powershell
# Compose files already updated to use workspace-level secrets
# Secret paths in base.yml:
secrets:
  redis_password:
    file: ../../../.cdb_local/.secrets/redis_password
```

---

## Migration Verification

### Step 1: Verify Canonical Files Used
```powershell
# Check that stack_up.ps1 uses canonical files
Get-Content infrastructure/scripts/stack_up.ps1 | Select-String "infrastructure\\compose"
# Should reference: base.yml, dev.yml, logging.yml, etc.
```

### Step 2: Verify Secret Files
```powershell
# Check workspace-level secrets
ls ../.cdb_local/.secrets/
# Should show:
# - redis_password (FILE, 24 bytes)
# - postgres_password (FILE, any size)
```

### Step 3: Verify No Plaintext Passwords
```powershell
# Check OS environment (should NOT have PASSWORD vars)
[Environment]::GetEnvironmentVariable("POSTGRES_PASSWORD", "User")  # Should be empty
[Environment]::GetEnvironmentVariable("REDIS_PASSWORD", "User")     # Should be empty
```

### Step 4: Verify Stack Starts with Canonical Files
```powershell
# Use canonical launcher
.\infrastructure\scripts\stack_up.ps1 -Logging

# Check logs for no errors
docker logs cdb_postgres --tail 10
docker logs cdb_redis --tail 10
```

---

## Timeline for Removal

### Immediate (Completed)
- ✅ Create canonical files in `infrastructure/compose/`
- ✅ Migrate all configurations
- ✅ Update `stack_up.ps1` to use canonical files
- ✅ Fix secret file paths
- ✅ Remove plaintext password environment variables

### Phase 2 (Current - Deprecation)
- ✅ Add deprecation headers to legacy files
- ✅ Create this migration guide (LEGACY_FILES.md)
- ✅ Update all documentation
- ⏳ Communicate to team

### Phase 3 (2025-12-28 - COMPLETE)
- ✅ Verified team adoption (infrastructure/compose/ in use)
- ✅ Removed `docker-compose.base.yml`
- ✅ Removed `docker-compose.yml`
- ✅ Removed `docker-compose.dev.yml`
- ✅ Added `.gitignore` entries for removed files

---

## FAQ

### Q: Why not use docker-compose.override.yml?
**A**: Override files don't support multiple profiles/overlays cleanly. The explicit overlay pattern is more maintainable and understandable.

### Q: Can I still use old files during transition?
**A**: Yes, but you'll get warnings. Use `stack_up.ps1` instead for best experience.

### Q: What if I have local changes in legacy files?
**A**: Migrate them to canonical files manually, or contact team for help.

### Q: Will CI/CD break after removal?
**A**: CI/CD should already use `stack_up.ps1`. Verify before legacy file removal.

---

## Getting Help

If you encounter issues during migration:

1. Check `infrastructure/compose/COMPOSE_LAYERS.md` for architecture
2. Check `DOCKER_STACK_RUNBOOK.md` for operational procedures
3. Run `infrastructure/scripts/stack_doctor.ps1` for automated drift detection
4. Contact team if manual intervention needed

---

## See Also

- `infrastructure/compose/COMPOSE_LAYERS.md` - Canonical architecture
- `DOCKER_STACK_RUNBOOK.md` - Operational procedures
- `infrastructure/scripts/stack_up.ps1` - Unified launcher
- `infrastructure/scripts/stack_doctor.ps1` - Drift detection
