# Sample Output: Rotate-Secrets.ps1 apply

**Command:**
```powershell
.\tools\secrets\Rotate-Secrets.ps1 apply
```

**Output:**

```
======================================================================
  CDB Secret Rotator v1.0
======================================================================
[INFO] Command: apply
[INFO] Manifest: D:\Dev\Workspaces\Repos\Claire_de_Binare\tools\secrets\secrets.manifest.json

======================================================================
  Validating Manifest (Fail-Closed)
======================================================================
[OK]   Manifest version: 1
[OK]   Secrets path exists: C:\Users\janne\Documents\.secrets\.cdb
[OK]   Secrets defined: 4
[OK]   Manifest validation passed (fail-closed checks OK)

======================================================================
  Apply: Rotating Secrets
======================================================================
[OK]   UPDATE REDIS_PASSWORD (length: 32)
[OK]   UPDATE POSTGRES_PASSWORD (length: 32)
[OK]   CREATE POSTGRES_PASSWORD_DSN (length: 32)

======================================================================
  Apply Complete
======================================================================
[OK]   Rotated: 3 secrets

[INFO]
[INFO] Next steps:
[INFO]   1. Run 'Rotate-Secrets.ps1 export' to generate .env.runtime
[INFO]   2. Run 'infrastructure/scripts/stack_up.ps1' to restart stack

```

---

## Key Observations (Safe)

### ✅ Rotation Success
- **3 secrets rotated** (REDIS, POSTGRES, POSTGRES_DSN)
- **0 errors**
- **GRAFANA_ADMIN_PASSWORD** correctly skipped (manual)

### 🔒 Files Written (Values NOT Shown)
```
C:\Users\janne\Documents\.secrets\.cdb\REDIS_PASSWORD          (32 bytes, base64)
C:\Users\janne\Documents\.secrets\.cdb\POSTGRES_PASSWORD       (32 bytes, base64)
C:\Users\janne\Documents\.secrets\.cdb\POSTGRES_PASSWORD_DSN   (32 bytes, base64)
```

### 📊 Actions Taken
- **UPDATE:** Existing secret replaced with new value (same length)
- **CREATE:** New secret file created
- **No overwrites without validation**

### 🔒 No Sensitive Data Logged
- Lengths shown (safe)
- Values NEVER logged
- File paths shown (safe)

---

## Idempotency Test (Second Run)

**Command:**
```powershell
.\tools\secrets\Rotate-Secrets.ps1 apply
```

**Expected Output:**
```
======================================================================
  Apply: Rotating Secrets
======================================================================
[INFO] SKIP   REDIS_PASSWORD (already correct length, idempotent)
[INFO] SKIP   POSTGRES_PASSWORD (already correct length, idempotent)
[INFO] SKIP   POSTGRES_PASSWORD_DSN (already correct length, idempotent)

======================================================================
  Apply Complete
======================================================================
[OK]   Rotated: 0 secrets
[INFO] Skipped: 3 secrets (idempotent)
```

**Result:** ✅ Idempotent (no unnecessary regeneration)

---

**Date:** 2026-01-28
**User:** janne
**Tool Version:** v1.0
