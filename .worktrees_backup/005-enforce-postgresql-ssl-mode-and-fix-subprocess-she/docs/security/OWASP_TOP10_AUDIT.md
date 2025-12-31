# OWASP Top 10 (2021) Security Audit - Claire de Binare

**Issue:** #105
**Date:** 2025-12-28
**Auditor:** Claude (Session Lead)
**Status:** ✅ Completed
**Result:** 0 CRITICAL, 0 HIGH, 0 MEDIUM (2 fixed), 1 LOW finding

---

## Executive Summary

This audit reviews the Claire de Binare trading system against the OWASP Top 10 (2021) security risks.
The codebase demonstrates **solid security practices** with no critical vulnerabilities identified.

| Category | Risk Level | Status |
|----------|------------|--------|
| A01 - Broken Access Control | LOW | ✅ Pass |
| A02 - Cryptographic Failures | LOW | ✅ Pass |
| A03 - Injection | MEDIUM | ✅ Pass (Fixed) |
| A04 - Insecure Design | LOW | ✅ Pass |
| A05 - Security Misconfiguration | LOW | ✅ Pass (Fixed) |
| A06 - Vulnerable Components | LOW | ✅ Pass (CI monitors) |
| A07 - Auth Failures | LOW | ✅ Pass |
| A08 - Integrity Failures | LOW | ✅ Pass |
| A09 - Logging Failures | LOW | ⚠️ Improvement possible |
| A10 - SSRF | LOW | ✅ Pass |

---

## A01:2021 – Broken Access Control

### Status: ✅ PASS

**Analysis:**
- Internal trading system with no public-facing web UI
- Service-to-service communication via Redis pub/sub
- No user roles or multi-tenant access to audit
- Kill-switch controlled via file-based state (local access only)

**Files Reviewed:**
- `core/safety/kill_switch.py`
- `core/auth.py`

**Findings:** None

---

## A02:2021 – Cryptographic Failures

### Status: ✅ PASS

**Positive Findings:**
- ✅ Secrets loaded via Docker Secrets (`/run/secrets/`) with ENV fallback
- ✅ SSL/TLS support for PostgreSQL (`core/utils/postgres_client.py`)
- ✅ No hardcoded credentials in source code
- ✅ `.env` files properly gitignored

**Files Reviewed:**
- `core/secrets.py` - Secure secret loading implementation
- `core/utils/postgres_client.py` - SSL/TLS support
- `.gitignore` - Excludes `.env`, secrets, keys

**Findings:** None

---

## A03:2021 – Injection

### Status: ✅ PASS (Finding Fixed)

**Positive Findings:**
- ✅ SQL queries use static strings (no f-string interpolation with user input)
- ✅ Parameterized queries used for data insertion
- ✅ No `eval()` or `exec()` with user input
- ✅ Subprocess calls use list-based arguments without shell=True

**Finding #1: shell=True in subprocess** ✅ FIXED

| Field | Value |
|-------|-------|
| File | `infrastructure/scripts/smart_startup.py:19` |
| Severity | MEDIUM |
| Type | Command Injection Risk |
| Original Code | `subprocess.run(cmd, shell=True, ...)` |
| Status | **✅ FIXED** |

**Resolution (2025-12-29):**
- Refactored `run_command()` function to accept commands as list instead of string
- Removed `shell=True` parameter (now uses default `shell=False`)
- Updated docker-compose call to use list-based arguments: `['docker', 'compose', 'up', '-d']`
- Added security rationale documentation to function docstring

---

## A04:2021 – Insecure Design

### Status: ✅ PASS

**Positive Findings:**
- ✅ Kill-switch safety mechanism for emergency stop
- ✅ Circuit breakers for risk management
- ✅ Clear separation of concerns (services architecture)
- ✅ Feature flags for controlled rollout

**Files Reviewed:**
- `core/safety/kill_switch.py`
- `services/risk/circuit_breakers.py`
- `core/config/feature_flags.py`

**Findings:** None

---

## A05:2021 – Security Misconfiguration

### Status: ✅ PASS (Finding Fixed)

**Positive Findings:**
- ✅ Docker images use non-root users
- ✅ Base images pinned to specific versions
- ✅ Trivy scanning in CI pipeline
- ✅ SSL/TLS configured for database connections
- ✅ PostgreSQL sslmode defaults to 'require' (prevents downgrade attacks)

**Finding #2: Default sslmode=prefer** ✅ FIXED

| Field | Value |
|-------|-------|
| File | `core/utils/postgres_client.py:82` |
| Severity | MEDIUM |
| Type | Potential Downgrade Attack |
| Original Code | `sslmode = sslmode or os.getenv("POSTGRES_SSLMODE", "prefer")` |
| Status | **✅ FIXED** |

**Resolution (2025-12-29):**
- Default sslmode changed from `prefer` to `require` in `get_postgres_dsn()` and `create_postgres_connection()`
- Added POSTGRES_SSLMODE configuration with security guidance in `.env.example`
- Updated module docstring with security rationale for the new default
- Environment variable override still available for local development needs

---

## A06:2021 – Vulnerable and Outdated Components

### Status: ✅ PASS (Monitored)

**Positive Findings:**
- ✅ Trivy scanning in GitHub Actions (`security-scan.yml`)
- ✅ Gitleaks for secret detection (`gitleaks.yml`)
- ✅ Base images pinned (redis:7.4.1-alpine, postgres:15.11-alpine)
- ✅ pip upgraded to 25.3 (CVE-2025-8869 resolved)

**Known Accepted Risks:**
- gosu binary CVEs (documented in SECURITY_BASELINE.md)
- Attack surface limited (startup-only usage)

**Files Reviewed:**
- `.github/workflows/security-scan.yml`
- `.github/workflows/gitleaks.yml`
- `docs/security/SECURITY_BASELINE.md`

**Findings:** None (monitoring in place)

---

## A07:2021 – Identification and Authentication Failures

### Status: ✅ PASS

**Positive Findings:**
- ✅ Auth validation on startup prevents restart loops (`core/auth.py`)
- ✅ Clear error messages for auth failures (no credential leaks)
- ✅ Connection timeouts configured
- ✅ No default credentials in codebase

**Files Reviewed:**
- `core/auth.py` - validate_redis_auth, validate_postgres_auth

**Findings:** None

---

## A08:2021 – Software and Data Integrity Failures

### Status: ✅ PASS

**Positive Findings:**
- ✅ No auto-update mechanisms
- ✅ Docker images built from Dockerfile (not pulled arbitrarily)
- ✅ CI/CD pipeline with security scanning
- ✅ Kill-switch state persisted to file (tamper-evident)

**Findings:** None

---

## A09:2021 – Security Logging and Monitoring Failures

### Status: ⚠️ LOW - 1 Finding

**Positive Findings:**
- ✅ Structured logging throughout services
- ✅ Prometheus metrics exported
- ✅ Grafana dashboards configured
- ✅ Kill-switch state changes logged

**Finding #3: Security Event Logging**

| Field | Value |
|-------|-------|
| Severity | LOW |
| Type | Audit Trail Improvement |
| Description | Security events (auth failures, kill-switch) could be centralized |

**Recommendation:**
- Implement dedicated security event log
- Consider Loki for centralized log aggregation
- Add alerting for suspicious patterns

---

## A10:2021 – Server-Side Request Forgery (SSRF)

### Status: ✅ PASS

**Analysis:**
- No user-controlled URLs in HTTP requests
- MEXC API client uses hardcoded endpoint
- No proxy/redirect functionality

**Files Reviewed:**
- `core/clients/mexc.py`
- `services/market/service.py`

**Findings:** None

---

## Summary of Findings

| # | Category | Severity | File | Status |
|---|----------|----------|------|--------|
| 1 | A03 Injection | MEDIUM | `smart_startup.py:19` | ✅ Fixed |
| 2 | A05 Misconfiguration | MEDIUM | `postgres_client.py:82` | ✅ Fixed |
| 3 | A09 Logging | LOW | General | Enhancement |

---

## Recommendations

### Immediate (Before Production)
1. ✅ ~~Set `POSTGRES_SSLMODE=require` in production compose files~~ — **FIXED:** Default changed to `require` (2025-12-29)
2. ✅ ~~Refactor `shell=True` to list-based subprocess calls~~ — **FIXED:** List-based args implemented (2025-12-29)

### Short-Term
3. ⏳ Implement centralized security event logging
4. ⏳ Add SIEM/alerting for auth failures

### Long-Term
5. 📅 Schedule quarterly OWASP audits
6. 📅 Consider DAST tools (OWASP ZAP) for API testing

---

## Audit Evidence

### Files Analyzed
```
core/auth.py
core/secrets.py
core/utils/postgres_client.py
core/utils/redis_client.py
core/safety/kill_switch.py
core/clients/mexc.py
services/execution/database.py
services/risk/real_validation_fetcher.py
infrastructure/scripts/smart_startup.py
.github/workflows/security-scan.yml
.github/workflows/gitleaks.yml
```

### Tools Used
- Manual code review
- Grep pattern matching for dangerous functions
- File structure analysis

---

## Approval

| Role | Name | Date |
|------|------|------|
| Auditor | Claude (Session Lead) | 2025-12-28 |
| Reviewer | [Pending] | |

---

**Next Review:** Q1 2026
**Issue:** #105
