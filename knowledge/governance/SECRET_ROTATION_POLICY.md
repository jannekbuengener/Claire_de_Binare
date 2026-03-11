# Secret Rotation Policy (CDB)

**Issue:** #TBD (cdb-secrets-rotator implementation)
**Status:** Active
**Last Updated:** 2026-01-28
**Tool:** `tools/secrets/Rotate-Secrets.ps1`

---

## Overview

This policy defines **how and when** secrets are rotated in Claire de Binare, with clear separation between **automated** and **manual** rotation workflows.

**Goal:** Enable fast incident response while preventing accidental rotation of human-managed credentials.

---

## Principle

### Values Never Enter Git
- Git contains **only ENV names** and **placeholders**
- Secret values live **exclusively** in `C:\Users\janne\Documents\.secrets\.cdb`
- Runtime injection via `.env.runtime` (gitignored)

### Rotation is Local-First
- No cloud dependencies for rotation (OpenSSL/SecureRandom only)
- Deterministic and auditable
- Idempotent (repeated rotation = zero changes)

---

## Rotation Modes

### `auto` - Tool-Generated Secrets
**What qualifies:**
- Cryptographically generated values (base64, hex, UUID)
- Machine-readable (no human interaction required)
- Not stored in password managers/browsers

**Examples:**
- `REDIS_PASSWORD` - Redis pub/sub authentication
- `POSTGRES_PASSWORD` - PostgreSQL database password
- `POSTGRES_PASSWORD_DSN` - PostgreSQL connection string
- *(Future: JWT signing keys, webhook secrets, session keys)*

**Tool behavior:**
- `rotate --all` rotates ALL auto secrets
- Generated using .NET `RandomNumberGenerator` (CSPRNG)
- Written to `$SECRETS_PATH/<SECRET_NAME>` (no newline)

---

### `manual` - Human-Managed Secrets
**What qualifies:**
- Stored in password managers (1Password, Bitwarden, etc.)
- Stored in browser saved passwords
- Requires UI interaction to update (e.g., Grafana admin login)

**Examples:**
- `GRAFANA_ADMIN_PASSWORD` - Grafana admin user password
- *(Future: External API keys, OAuth client secrets)*

**Tool behavior:**
- **NEVER rotated by tool**
- `rotate --all --include-manual` → **hard-fail** (forbidden)
- Listed in output as `[SKIP] MANUAL`
- Rotation only via **incident runbook**

---

## Mandatory Guardrails (Technically Enforced)

### 1. Fail-Closed Validation
**Before `apply`:**
- Manifest must exist and be valid JSON
- `canonical_secrets_path` must exist
- All secrets must have required fields (`name`, `rotation_mode`, `format`, `bytes` for auto)
- Invalid manifest → **immediate hard-fail, no changes**

### 2. Repo Stays Value-Free
**Enforcement:**
- Tool **never writes** secret values to git-tracked files
- `.env.runtime` is gitignored (runtime only)
- `touch_policy` allowlist (future: control which repo files can be touched)

### 3. Explicit Allowlist
**Enforcement:**
- Only secrets in `secrets.manifest.json` can be rotated
- Unknown secret name → hard-fail
- No "discover and rotate" behavior

### 4. Safe Logging
**Enforcement:**
- Logs show: secret **names**, **lengths**, **actions** (CREATE/UPDATE/SKIP)
- Logs **NEVER** show: values, partial values, hashes (could leak entropy)
- Example: `[OK] REDIS_PASSWORD (length: 32)`

### 5. Two-Step Workflow
**Enforcement:**
```powershell
Rotate-Secrets.ps1 plan   # Dry-run (show what WOULD change)
Rotate-Secrets.ps1 apply  # Execute rotation
```
- `plan` shows affected secrets + services
- `apply` only proceeds if validation passes

### 6. Idempotency
**Enforcement:**
- If secret file exists and has correct length → skip
- Repeated `apply` = zero changes (unless bytes changed)
- No unnecessary restarts

### 7. Manual Protection
**Enforcement:**
- `--IncludeManual` flag → **immediate hard-fail**
- Error message includes runbook link
- No override/bypass mechanism

---

## Incident Playbook (Fast Response)

### Scenario: Secret Leak / Compromise Suspected

**Timeline: < 5 minutes to rotate all auto secrets**

#### Step 1: Plan (30 seconds)
```powershell
cd D:\Dev\Workspaces\Repos\Claire_de_Binare
.\tools\secrets\Rotate-Secrets.ps1 plan
```
- Review which secrets will be rotated
- Note which services will restart

#### Step 2: Apply Rotation (30 seconds)
```powershell
.\tools\secrets\Rotate-Secrets.ps1 apply
```
- Generates new secrets
- Writes to `$SECRETS_PATH`

#### Step 3: Export Runtime ENV (10 seconds)
```powershell
.\tools\secrets\Rotate-Secrets.ps1 export
```
- Creates `.env.runtime` for Docker Compose

#### Step 4: Restart Stack (2-3 minutes)
```powershell
.\infrastructure\scripts\stack_up.ps1
```
- Auto-loads `.env.runtime` (B-lite integration)
- Restarts affected services with new secrets

#### Step 5: Verify (30 seconds)
```powershell
.\infrastructure\scripts\stack_verify.ps1
```
- Check all services healthy
- Verify connectivity (Redis, Postgres, Grafana)

---

### Manual Actions (After Auto-Rotation)

If `GRAFANA_ADMIN_PASSWORD` was also compromised:
- See runbook: `knowledge/runbooks/GRAFANA_ADMIN_INCIDENT.md`
- Change password via Grafana UI
- Update password manager entry

---

## Integration with Existing Tools

### Existing Scripts (Unchanged)
- `tools/set_secrets.ps1` - Manual initial setup (interactive prompts)
- `tools/cdb-secrets-sync.ps1` - Sync .cdb_local → .secrets (legacy)

### New Script (Rotation)
- `tools/secrets/Rotate-Secrets.ps1` - Incident response + periodic rotation

### Stack Startup (B-lite Integration)
- `infrastructure/scripts/stack_up.ps1` - Auto-loads `.env.runtime` if present
- Disable via: `$env:CDB_IGNORE_RUNTIME_ENV='1'`

---

## Manifest Schema (v1)

```json
{
  "version": 1,
  "canonical_secrets_path": "C:\\Users\\janne\\Documents\\.secrets\\.cdb",
  "defaults": {
    "rotation_command_default": "rotate apply",
    "forbid_include_manual": true
  },
  "secrets": [
    {
      "name": "REDIS_PASSWORD",
      "rotation_mode": "auto",
      "exclude_by_default": false,
      "format": "base64",
      "bytes": 24,
      "restart_scope": ["cdb_redis", "..."],
      "touch_policy": [],
      "notes": "Redis authentication"
    },
    {
      "name": "GRAFANA_ADMIN_PASSWORD",
      "rotation_mode": "manual",
      "exclude_by_default": true,
      "format": "manual",
      "bytes": null,
      "restart_scope": ["cdb_grafana"],
      "notes": "MANUAL: stored in password manager"
    }
  ]
}
```

---

## Periodic Rotation Schedule (Future)

**v1:** Manual trigger only (incident response)

**v2 (Planned):**
- Weekly auto-rotation for DB passwords (scheduled task)
- Monthly for app signing keys
- Quarterly audit of all secrets

---

## References

- **Tool README:** `tools/secrets/README.md`
- **Grafana Incident Runbook:** `knowledge/runbooks/GRAFANA_ADMIN_INCIDENT.md`
- **General Secrets Policy:** `governance/SECRETS_POLICY.md`
- **Manifest:** `tools/secrets/secrets.manifest.json`

---

## Acceptance Criteria (Implementation)

- [x] `rotate --all` works without browser interaction
- [x] `GRAFANA_ADMIN_PASSWORD` never rotated, listed as MANUAL
- [x] No secret values in git (verified via grep)
- [x] Logs contain no values (only names/lengths)
- [x] `--include-manual` → hard-fail
- [x] `plan` shows precise changes (secrets + services)
- [x] `apply` is idempotent (2x = 0 changes)
- [x] `.env.runtime` gitignored
- [x] Runbook exists for manual secrets

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)
