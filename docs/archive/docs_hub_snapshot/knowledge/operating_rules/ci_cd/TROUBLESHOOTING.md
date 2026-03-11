# CI/CD Troubleshooting Guide

**Issue:** #112
**Version:** 1.0
**Last Updated:** 2025-12-28

---

## Quick Reference

| Symptom | Likely Cause | Quick Fix |
|---------|--------------|-----------|
| PR blocked on Delivery Gate | `DELIVERY_APPROVED.yaml` is false | Update file |
| Security scan fails | CRITICAL CVE in custom image | Fix Dockerfile |
| E2E tests timeout | Service startup failure | Check container logs |
| Gitleaks blocks PR | Secret in code | Remove or allowlist |

---

## 1. Delivery Gate Failures

### Symptom
```
❌ Delivery gate is CLOSED
```

### Cause
The governance file `governance/DELIVERY_APPROVED.yaml` has `approved: false`.

### Fix
1. Edit `governance/DELIVERY_APPROVED.yaml`:
   ```yaml
   delivery:
     approved: true
     reason: "Your reason here"
     approved_by: "Your Name"
   ```
2. Commit and push

### Bypass (Emergency Only)
Add exception label to PR (defined in `DELIVERY_APPROVED.yaml`).

---

## 2. Security Scan Failures

### Symptom: Trivy/Scout fails on custom image

```
CRITICAL: vulnerability found in cdb_signal
```

### Cause
New CRITICAL or HIGH CVE in Python dependencies or base image.

### Fix

**Step 1: Identify the vulnerability**
```bash
docker run --rm aquasec/trivy image cdb_signal:latest \
  --severity CRITICAL,HIGH
```

**Step 2: Fix based on type**

| Type | Action |
|------|--------|
| Python package | Update in `requirements.txt` |
| pip itself | Upgrade: `pip install --upgrade pip` |
| OS package | Update Dockerfile base image |

**Step 3: Rebuild and re-scan**
```bash
docker build -f services/signal/Dockerfile -t cdb_signal:latest .
docker run --rm aquasec/trivy image cdb_signal:latest
```

### Known Accepted Risks
Base images (Redis, Postgres) have gosu CVEs that are documented as accepted risk.
See `docs/security/SECURITY_BASELINE.md`.

---

## 3. E2E Test Failures

### Symptom: Timeout waiting for services

```
Waiting for Redis...
Redis not ready...
[timeout after 60s]
```

### Cause
Container failed to start or health check misconfigured.

### Fix

**Step 1: Check local stack**
```bash
cd infrastructure/compose
docker-compose -f base.yml -f dev.yml up -d
docker-compose ps
docker-compose logs --tail=50
```

**Step 2: Common issues**

| Issue | Fix |
|-------|-----|
| Port conflict | Stop other Docker containers |
| Missing env vars | Check `.env` file |
| Volume permissions | `docker-compose down -v` and restart |
| Image not built | `docker-compose build` |

**Step 3: Manual health check**
```bash
# Redis
docker exec cdb_redis redis-cli ping

# Postgres
docker exec cdb_postgres pg_isready -U claire_user
```

### Symptom: Test assertions fail

```
AssertionError: Expected order approved, got blocked
```

### Cause
Business logic failure or configuration mismatch.

### Fix
1. Check test expectations match current behavior
2. Review circuit breaker state
3. Check kill-switch status: `cat .cdb_kill_switch.state`

---

## 4. Gitleaks Failures

### Symptom: Secret detected

```
Secret detected: AWS_SECRET_ACCESS_KEY
File: config/settings.py
Line: 42
```

### Fix

**Option A: Remove the secret**
1. Remove secret from code
2. Use environment variable or Docker secrets
3. Commit changes

**Option B: Allowlist (if false positive)**

Edit `gitleaks.toml`:
```toml
[[allowlist]]
description = "False positive - not a real secret"
regexTarget = "match"
regexes = ['''your-pattern-here''']
paths = ['''path/to/file\.py''']
```

**Option C: Rotate compromised secret**
If a real secret was committed:
1. Rotate the secret immediately
2. Use `git filter-branch` or BFG to remove from history
3. Force push (coordinate with team)

---

## 5. Label/Auto-Label Issues

### Symptom: Labels not applied automatically

### Cause
- Path patterns don't match
- Label doesn't exist
- Workflow permissions

### Fix
1. Check `.github/labeler.yml` for path patterns
2. Verify label exists in repository settings
3. Check workflow has `pull-requests: write` permission

---

## 6. Workflow Permission Errors

### Symptom
```
Error: Resource not accessible by integration
```

### Cause
Insufficient `GITHUB_TOKEN` permissions.

### Fix
Check workflow permissions:
```yaml
permissions:
  contents: read
  pull-requests: write
  issues: write
```

---

## 7. Docker Build Failures in CI

### Symptom: Build context errors

```
COPY failed: file not found in build context
```

### Cause
Path mismatch between local and CI environment.

### Fix
1. Use relative paths in Dockerfile
2. Ensure `.dockerignore` isn't excluding required files
3. Build from repository root:
   ```bash
   docker build -f services/signal/Dockerfile -t cdb_signal .
   ```

---

## 8. Stale Bot Closing Active Issues

### Symptom
Bot closes issue that's still active.

### Fix
1. Add comment to reset stale timer
2. Add `keep-open` label (if configured)
3. Adjust stale.yml configuration:
   ```yaml
   exempt-issue-labels: 'keep-open,blocked'
   ```

---

## 9. AI Workflow Failures (Claude/Gemini)

### Symptom: API errors

```
Error: 401 Unauthorized
```

### Cause
API key expired or missing.

### Fix
1. Check repository secrets:
   - `ANTHROPIC_API_KEY` for Claude
   - `GOOGLE_API_KEY` for Gemini
2. Rotate keys if expired
3. Check API quota limits

---

## 10. General Debugging Steps

### Step 1: Check workflow logs
Go to Actions tab → Select run → View logs

### Step 2: Re-run with debug logging
```yaml
env:
  ACTIONS_STEP_DEBUG: true
```

### Step 3: Check artifacts
Download artifacts for detailed reports.

### Step 4: Local reproduction
```bash
# Clone exact commit
git checkout <commit-sha>

# Run same commands as CI
docker build ...
pytest ...
```

---

## Common Error Messages

| Error | Meaning | Action |
|-------|---------|--------|
| `exit code 1` | Command failed | Check command output |
| `canceled` | Workflow canceled | Check for concurrent runs |
| `timeout` | Exceeded time limit | Increase timeout or optimize |
| `ENOSPC` | Out of disk space | Clean up artifacts/images |
| `rate limit exceeded` | API throttling | Wait or increase limit |

---

## Getting Help

1. **Check existing issues:** Search for similar problems
2. **CI/CD Documentation:** See `CI_PIPELINE_GUIDE.md`
3. **Security Issues:** See `docs/security/SECURITY_BASELINE.md`
4. **Create issue:** Use `type:bug` + `scope:ci` labels

---

**Owner:** DevOps Team
**Review Cycle:** As needed
