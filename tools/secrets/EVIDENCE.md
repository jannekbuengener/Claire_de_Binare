# Evidence: cdb-secrets-rotator Security Compliance

**Date:** 2026-01-28
**Tool Version:** v1.1 (State-Based Rotation)
**Auditor:** Claude (Session Lead)

---

## Summary

This document provides **hard evidence** that the cdb-secrets-rotator implementation meets all safety requirements:

1. ✅ **No secrets in repo** (gitleaks + git grep verified)
2. ✅ **Runtime files gitignored** (git status --ignored verified)
3. ✅ **Rotation state tracking** (freshness, not just length)
4. ✅ **Safe logging** (no values, only names/lengths)

---

## 1. Secret Scanning (gitleaks)

**Command:**
```bash
cd D:/Dev/Workspaces/Repos/Claire_de_Binare
gitleaks detect --no-git --verbose
```

**Result:** ✅ **PASS**

**Findings:**
- 3 secrets detected in `.auto-claude/.env`:
  - `OPENAI_API_KEY` (Line 83)
  - `GOOGLE_API_KEY` (Line 96)
  - `GITHUB_TOKEN` (Line 99+)

**Assessment:** ✅ **SAFE**
- `.auto-claude/` directory is **gitignored** (Line 145 in .gitignore)
- Files never committed to repo
- No secrets in tracked files

**Evidence File:** `gitleaks.log` (if available)

---

## 2. Pattern-Based Search (git grep)

**Command:**
```bash
git grep -niE "(password|secret|key|token|credential).*=.*['\"][^'\"]{20,}" \
  -- "*.ps1" "*.yml" "*.json" "*.md"
```

**Result:** ✅ **PASS**

**Findings:** 32 matches
- GitHub Actions workflows: Template variables (`${{ secrets.* }}`) ✅ Safe
- Migration scripts: Placeholders (`<SET_IN_ENV>`) ✅ Safe
- Stack scripts: Path references (`$SECRETS_PATH`) ✅ Safe
- Test fixtures: Mock values (`ci-redis-password`) ✅ Safe

**Assessment:** ✅ **NO HARDCODED SECRETS**
- All matches are placeholders, templates, or references
- No actual secret values in tracked files

---

## 3. Gitignore Verification (git status)

**Command:**
```bash
git status --ignored --porcelain | grep -E "(tools/secrets/)"
```

**Result:**
```
!! tools/secrets/
```

**Assessment:** ✅ **RUNTIME FILES GITIGNORED**
- `!!` prefix indicates ignored directory
- `.env.runtime`, `.rotation_state.json` cannot be committed
- Evidence files (`evidence/`) explicitly whitelisted (tracked)

**Gitignore entries (lines 165-172):**
```gitignore
# =============================================================================
# SECRET ROTATION RUNTIME EXPORTS (cdb-secrets-rotator)
# =============================================================================
*.env.runtime
*.runtime.env
.secrets/*.export
tools/secrets/.env.*
!tools/secrets/README.md
!tools/secrets/evidence/**
# Note: .rotation_state.json now lives in $SECRETS_PATH (outside repo) since v1.2
```

---

## 4. Rotation State Tracking

**File:** `$SECRETS_PATH/.rotation_state.json` (v1.2+, outside repo)
**Old location (v1.1):** `tools/secrets/.rotation_state.json` (auto-migrated on first run)

**Structure:**
```json
{
  "version": 1,
  "secrets": {
    "REDIS_PASSWORD": {
      "last_rotated": "2026-01-28T15:29:26.0000000+01:00",
      "rotated_by": "Rotate-Secrets.ps1 v1.2",
      "length": 32,
      "format": "base64"
    }
  }
}
```

**Skip Logic (v1.1+):**
- ❌ **Old (v1.0):** Skip if `length == expected_length` (weak - compromised secret could persist)
- ✅ **New (v1.1+):** Skip if `age < MAX_AGE_DAYS` (90 days default) (strong - freshness enforced)

**State Location (v1.2 Hardening):**
- ✅ State file now lives in `$SECRETS_PATH` (outside repo tree)
- ✅ Automatic migration from old location on first run
- ✅ Repo remains 100% metadata-free (not just value-free)
- ✅ Zero risk of accidental state commits

**Evidence:**
- `Test-SecretFreshness()` function (Lines 129-147 in Rotate-Secrets.ps1)
- Migration logic in Main function (v1.2)
- Age calculation: `$age.TotalDays -lt $MAX_AGE_DAYS`
- Force override available: `Rotate-Secrets.ps1 apply -Force`

---

## 5. Safe Logging Verification

**Commands executed during smoke test:**
```powershell
.\Rotate-Secrets.ps1 plan
.\Rotate-Secrets.ps1 apply
.\Rotate-Secrets.ps1 export
```

**Log samples (SAFE - no values):**
```
[OK]   UPDATE REDIS_PASSWORD (length: 32)
[INFO] Export POSTGRES_PASSWORD (length: 32)
[INFO] SKIP   REDIS_PASSWORD (fresh, age: 0.0 days, max: 90)
```

**Never logged:**
- ❌ Secret values (full or partial)
- ❌ Hashes (could leak entropy)
- ❌ Base64-decoded content

**Always logged:**
- ✅ Secret names
- ✅ Lengths
- ✅ Actions (CREATE/UPDATE/SKIP)
- ✅ Ages (for freshness)

---

## 6. CI/CD Integration (Future)

**Status:** Not yet implemented

**Planned checks:**
- [ ] Pre-commit hook: Run `gitleaks detect` before commit
- [ ] CI workflow: Scan on every PR
- [ ] Rotation reminder: Warn if state file shows secrets > 80 days old

**Blocking:** None (manual verification sufficient for v1.1)

---

## 7. Acceptance Criteria Status

| Criterion | Status | Evidence |
|-----------|--------|----------|
| No secrets in repo | ✅ PASS | gitleaks + git grep (sections 1-2) |
| Runtime files gitignored | ✅ PASS | git status (section 3) |
| Rotation state tracking | ✅ PASS | State file + freshness logic (section 4) |
| Safe logging | ✅ PASS | Smoke test logs (section 5) |
| Fail-closed validation | ✅ PASS | Manifest validation (smoke test) |
| Manual secret protection | ✅ PASS | `--IncludeManual` hard-fail (smoke test) |
| Idempotency (v1.1) | ✅ PASS | Age-based skip (section 4) |
| B-lite integration | ✅ PASS | stack_up.ps1 auto-load (smoke test) |

---

## 8. Known Limitations (Documented)

### 8.1 State File is Local
- **Issue:** `.rotation_state.json` not shared across machines
- **Impact:** Different machines may have different rotation schedules
- **Mitigation:** Document in runbook: "Re-run apply on all machines after incident"

### 8.2 MAX_AGE_DAYS Hardcoded
- **Issue:** 90-day threshold in script (Line 59)
- **Impact:** No per-secret rotation schedule
- **Mitigation:** Future: Move to manifest (`max_age_days` field)

### 8.3 No Audit Log
- **Issue:** State file overwritten on each rotation
- **Impact:** No history of rotations
- **Mitigation:** Future: Append-only audit log

---

## 9. Verification Commands (Repeatable)

To verify this evidence yourself:

```powershell
# 1. Scan for secrets
cd D:/Dev/Workspaces/Repos/Claire_de_Binare
gitleaks detect --no-git

# 2. Search tracked files
git grep -niE "(password|secret|key).*=.*['\"][^'\"]{20,}" -- "*.ps1" "*.yml" "*.json"

# 3. Check gitignore
git status --ignored --porcelain | grep tools/secrets

# 4. Verify runtime files NOT tracked
git ls-files | grep -E "(.env.runtime|.rotation_state.json)"
# Expected: no output

# 5. Test rotation
.\tools\secrets\Rotate-Secrets.ps1 plan
.\tools\secrets\Rotate-Secrets.ps1 apply -Force
.\tools\secrets\Rotate-Secrets.ps1 export

# 6. Verify stack startup
.\infrastructure\scripts\stack_up.ps1
```

---

## 10. Gitleaks False-Positive Elimination (2026-01-28)

**Context**: CI security gate (Gitleaks) intermittently failed due to legacy commits/test fixtures, NOT from secret-rotator code.

**Findings (5 false-positives identified)**:
1. `tests/unit/surrealdb/test_ledger_importer.py:26`
   - Pattern: `token=ghp_[REDACTED]` (fake GitHub token)
   - Rule: generic-api-key
   - Type: Test fixture (not real secret)

2-5. `reports/shadow_mode/ALERTING_DIGEST_EVIDENCE.md` (Lines 48, 61, 238, 357)
   - Pattern: `curl -u admin:[REDACTED]`
   - Rule: curl-auth-user
   - Type: Documentation examples (not real credentials)

**Fix Applied (Option A: Fixture Refactor)**:
1. Test fixture: `ghp_[REDACTED]` → `FAKE_TEST_TOKEN_NOT_REAL`
   - Breaks entropy/pattern matcher
   - Test semantics preserved

2-4. Documentation: `admin:[REDACTED]` → `admin:$GRAFANA_PASSWORD`
   - Environment variable placeholder
   - Standard practice for documentation

**Validation**:
```bash
# Before fix
gitleaks detect --no-git --source .
# Result: 5 findings

# After fix (current tree)
gitleaks detect --no-git --source .
# Result: 0 findings (clean)

# History scan (CI scans with git history)
gitleaks detect
# Result: 5 findings in legacy commits (before ea4be33)
```

**History Handling**:
Since CI scans git history (not just working tree), legacy commits still trigger findings even though current files are clean.

**Solution:** Fingerprint-based allowlist in `.gitleaksignore` for specific legacy commits:
```gitignore
# Legacy commits (before fixture refactor PR #714)
e12f529094591f848d39a427bb21b3d95d12ae9c:tests/unit/surrealdb/test_ledger_importer.py:generic-api-key:26
5ae1df7eea9eb92b7ce0443ab44bd6dbb0a4c97a:reports/shadow_mode/ALERTING_DIGEST_EVIDENCE.md:curl-auth-user:48
5ae1df7eea9eb92b7ce0443ab44bd6dbb0a4c97a:reports/shadow_mode/ALERTING_DIGEST_EVIDENCE.md:curl-auth-user:61
5ae1df7eea9eb92b7ce0443ab44bd6dbb0a4c97a:reports/shadow_mode/ALERTING_DIGEST_EVIDENCE.md:curl-auth-user:238
5ae1df7eea9eb92b7ce0443ab44bd6dbb0a4c97a:reports/shadow_mode/ALERTING_DIGEST_EVIDENCE.md:curl-auth-user:357
```

This approach:
- ✅ Scoped to specific commit SHA + file + line (narrow, auditable)
- ✅ No broad pattern ignores (scanning remains strict)
- ✅ Documents exactly which legacy commits contain fixtures

**Impact**:
- ✅ CI security gate now consistently green
- ✅ No weakening of scanning (narrow fingerprint-based allowlist only)
- ✅ No real secrets in repo (was never an issue, only pattern matches)
- ✅ Tests remain functional (validated post-fix)
- ✅ Legacy commits explicitly documented in .gitleaksignore

---

## 11. Sign-Off

**Status:** ✅ **PRODUCTION READY**

**Blockers Resolved:**
1. ✅ Skip logic fixed (state-based, not length-based)
2. ✅ Evidence documented (this file)
3. ✅ Gitleaks false-positives eliminated (fixture refactor)

**Deployment Status:**
- ✅ PR #711: Secret rotator v1.1 (MERGED)
- ✅ PR #712: `apply -ExportAfter` (MERGED)
- ✅ PR #59 (Docs Hub): Policy + Runbook (MERGED)

---

**Generated:** 2026-01-28
**Tool Version:** Rotate-Secrets.ps1 v1.1 + apply -ExportAfter
**Evidence Level:** High (automated scans + manual verification + CI validation)

🤖 Generated with [Claude Code](https://claude.com/claude-code)
