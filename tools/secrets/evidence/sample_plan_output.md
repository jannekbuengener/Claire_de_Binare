# Sample Output: Rotate-Secrets.ps1 plan

**Command:**
```powershell
.\tools\secrets\Rotate-Secrets.ps1 plan
```

**Output:**

```
======================================================================
  CDB Secret Rotator v1.0
======================================================================
[INFO] Command: plan
[INFO] Manifest: D:\Dev\Workspaces\Repos\Claire_de_Binare\tools\secrets\secrets.manifest.json

======================================================================
  Validating Manifest (Fail-Closed)
======================================================================
[OK]   Manifest version: 1
[OK]   Secrets path exists: C:\Users\janne\Documents\.secrets\.cdb
[OK]   Secrets defined: 4
[OK]   Manifest validation passed (fail-closed checks OK)

======================================================================
  Plan: Secret Rotation Analysis
======================================================================
[INFO] AUTO secrets (will be rotated):
[INFO]   [UPDATE] REDIS_PASSWORD                  24 bytes, restart: cdb_redis, cdb_ws, cdb_signal, cdb_risk, cdb_execution, cdb_paper_runner, cdb_core
[INFO]   [UPDATE] POSTGRES_PASSWORD               24 bytes, restart: cdb_postgres
[INFO]   [CREATE] POSTGRES_PASSWORD_DSN           24 bytes, restart: cdb_postgres

[INFO]
[INFO] MANUAL secrets (will NOT be rotated):
[INFO]   [SKIP]   GRAFANA_ADMIN_PASSWORD           MANUAL: stored in password manager / browser; rotate only on incident via runbook

[INFO]
[INFO] Affected services (will need restart):
[INFO]   - cdb_redis
[INFO]   - cdb_ws
[INFO]   - cdb_signal
[INFO]   - cdb_risk
[INFO]   - cdb_execution
[INFO]   - cdb_paper_runner
[INFO]   - cdb_core
[INFO]   - cdb_postgres

======================================================================
  Plan Complete
======================================================================
[INFO] Next step: Run 'Rotate-Secrets.ps1 apply' to execute rotation

```

---

## Key Observations (Safe)

### ✅ Safety Checks Passed
- Manifest validation: OK
- Secrets path exists: OK
- All required fields present: OK

### 📊 Rotation Scope
- **Auto secrets:** 3 (REDIS, POSTGRES, POSTGRES_DSN)
- **Manual secrets:** 1 (GRAFANA_ADMIN_PASSWORD) - correctly skipped
- **Services affected:** 8 (will restart after apply)

### 🔒 No Sensitive Data Logged
- No secret values shown
- Only names, lengths, and actions
- Safe for sharing/auditing

---

**Date:** 2026-01-28
**User:** janne
**Tool Version:** v1.0
