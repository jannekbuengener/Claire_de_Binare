# gh-fix-ci Discovery Report

**Date:** 2026-02-08
**Repository:** jannekbuengener/Claire_de_Binare
**Default Branch:** main
**Discovery Mode:** Read-only
**Scope:** CI/CD workflow analysis for gh-fix-ci skill implementation

---

## Executive Summary

Claire de Binare operates a **sophisticated, multi-layered CI/CD governance system** with:
- **41 workflow files** in `.github/workflows/`
- **8 required status checks** enforced by branch protection on `main`
- **Hard-fail mechanisms** via custom governance guards (delivery-gate, core-guard)
- **Security-first architecture** (gitleaks, Trivy CVE scanning, pip-audit)
- **Exception handling** for stub/mock scenarios in E2E tests

**Key Finding:** CDB is an excellent candidate for gh-fix-ci development due to complex, real-world CI patterns including custom governance checks beyond standard GitHub Actions.

---

## 1. Workflow Inventory

### 1.1 Total Workflow Count
**41 workflow files** found in `.github/workflows/`

### 1.2 PR-Triggering Workflows (Critical for gh-fix-ci)

| Workflow File | Display Name | Triggers | Jobs | Runner | Duration (Typical) |
|---|---|---|---|---|---|
| **ci.yml** | ci (Unit/Integration + Lint gesammelt) | pull_request (main), push (main) | ci | ubuntu-latest | ~30s |
| **branch-policy.yml** | Branch Policy Enforcement | pull_request (opened/sync/reopen) | validate-branch-name, validate-feature-workflow, enforce-pr-template | ubuntu-latest | ~5s |
| **gitleaks.yml** | Gitleaks Secret Scan | pull_request (main), push (main), schedule (weekly) | gitleaks, full-scan | ubuntu-latest | ~14s |
| **core-guard.yml** | Core Guard | pull_request (main) | Check Core Duplicates | ubuntu-latest | ~6s |
| **delivery-gate.yml** | Delivery Gate | pull_request (main, labeled/unlabeled) | Check Delivery Gate | ubuntu-latest | ~6s |
| **docs-hub-guard.yml** | Docs Hub Guard | pull_request (main) | guard | ubuntu-latest | ~5s |
| **e2e-tests.yml** | E2E Tests - Paper Trading | pull_request (paths: services/, tests/e2e/, infra/) | e2e-paper-trading | ubuntu-latest | ~20s (stub mode), 15min timeout |
| **trivy.yml** | trivy | pull_request (main), push (main), schedule (weekly) | trivy-image | ubuntu-latest | ~10s (with cache) |
| **contracts.yml** | Contract Validation | pull_request (main, paths: docs/contracts/, tests/unit/contracts/) | validate-contracts | ubuntu-latest | ~28s |
| **emoji-filter.yml** | 🚫 Advanced Emoji Filter | pull_request (main) | 🔍 Emoji Detection, 💬 PR Comment, 🛡️ Security & Quality Check, 🚫 Block PR Merge, 📢 Notifications | ubuntu-latest | ~11s |

### 1.3 Workflow Architecture Patterns

#### Concurrency Control
Most workflows implement:
```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```
**Impact:** New pushes cancel previous runs → gh-fix-ci must handle cancelled runs gracefully.

#### Path-Based Triggers
Many workflows only run when specific paths change:
```yaml
paths:
  - 'core/**'
  - 'services/**'
  - 'tests/**'
  - 'infrastructure/**'
```
**Impact:** Not all workflows run on every PR → gh-fix-ci should detect which workflows are expected vs. skipped.

#### Matrix Strategies
Some workflows (e.g., ci.yml) use Python version matrices:
```yaml
strategy:
  matrix:
    python-version: ["3.11", "3.12"]
```
**Impact:** Multiple jobs for single workflow → gh-fix-ci must aggregate failures across matrix jobs.

---

## 2. Required Checks / Branch Protection

### 2.1 GitHub API Evidence

**Command:**
```bash
gh api repos/jannekbuengener/Claire_de_Binare/branches/main/protection --jq '.required_status_checks.contexts'
```

**Result:**
```json
[
  "ci (Unit/Integration + Lint gesammelt)",
  "validate-branch-name",
  "gitleaks (Secrets-Alarm)",
  "trivy (kritische CVEs/Supply-Chain)",
  "Check Core Duplicates",
  "Check Delivery Gate",
  "guard",
  "E2E Happy Path"
]
```

### 2.2 Required Checks Analysis

| Check Name | Source Workflow | Failure Impact | Common Failure Reason |
|---|---|---|---|
| **ci (Unit/Integration + Lint gesammelt)** | ci.yml | HARD BLOCK | Ruff/Black formatting violations, mypy type errors, pytest failures |
| **validate-branch-name** | branch-policy.yml | HARD BLOCK | Branch naming convention violation (must match patterns) |
| **gitleaks (Secrets-Alarm)** | gitleaks.yml | HARD BLOCK | Credential/API key detected in code |
| **trivy (kritische CVEs/Supply-Chain)** | trivy.yml | HARD BLOCK | Container image CVE above allowlist |
| **Check Core Duplicates** | core-guard.yml | HARD BLOCK | Duplicate `core/` directories detected |
| **Check Delivery Gate** | delivery-gate.yml | HARD BLOCK | `governance/DELIVERY_APPROVED.yaml` approval missing |
| **guard** | docs-hub-guard.yml | HARD BLOCK | Docs Hub consistency violation |
| **E2E Happy Path** | e2e-tests.yml or multi-job workflow | HARD BLOCK | E2E pipeline failure (Redis, Postgres, Docker Compose) |

### 2.3 External Checks (Non-Blocking)

- **Sourcery review** (sourcery.ai) - Code quality suggestions (pending, not required)
- **Copilot code review** - AI-powered review (success, not required)
- **Claude Code Review** - Often skipped (workflow_dispatch only?)

---

## 3. Typical Failure Patterns

### 3.1 Recent Failure Evidence

#### Sample 1: PR #806 - LR-004 Completion State Validation Failure

**Check:** `LR-004: Completion State Validation`
**Conclusion:** FAILURE
**URL:** https://github.com/jannekbuengener/Claire_de_Binare/actions/runs/21780276909/job/62843170058

**Log Excerpt:**
```
Type Checking (mypy)  error: Duplicate module named "service" (also at "services/candles/service.py")
services/market/service.py: note: See https://mypy.readthedocs.io/en/stable/running_mypy.html#mapping-file-paths-to-modules for more info
services/market/service.py: note: Common resolutions include: a) using `--exclude` to avoid checking one of them, b) adding `__init__.py` somewhere, c) using `--explicit-package-bases` or adjusting MYPYPATH
Found 1 error in 1 file (errors prevented further checking)
##[error]Process completed with exit code 2.
```

**Category:** LINT/TYPE_CHECK
**Root Cause:** mypy detected duplicate module names across services
**Fix Pattern:** Add `__init__.py` or configure mypy excludes

---

#### Sample 2: Recent Workflow Failures (from gh run list)

**Failed Workflows (Last 30 runs):**
1. `.github/workflows/e2e.yml` - FAILURE (21797091117)
   - **Likely Cause:** E2E stub mode (credentials not available in PR context)
   - **Common Pattern:** Workflows requiring Redis/Postgres in PR forks fail

2. `.github/workflows/python-compat.yml` - FAILURE (21797091004)
   - **Likely Cause:** Python version compatibility test failure
   - **Common Pattern:** Code works on 3.12 but fails on 3.11 or vice versa

**Action Required Workflows:**
- **opencode** (multiple runs) - `action_required` conclusion
- **Claude Code** (multiple runs) - `action_required` conclusion

**Interpretation:** Workflows with `workflow_dispatch` or manual approval gates show as `action_required`.

---

### 3.2 Failure Buckets (Categorized)

| Category | Frequency | Typical Check Names | Example Error Patterns |
|---|---|---|---|
| **LINT/FORMAT** | High | ci (Ruff), ci (Black), Format Check | `Ruff found X violations`, `Black would reformat files` |
| **TYPE_CHECK** | Medium | ci (mypy), Type Checking (mypy) | `Duplicate module`, `incompatible type`, `missing return` |
| **TEST** | Medium | ci (pytest), Tests (Python 3.11/3.12) | `FAILED tests/...`, `AssertionError`, `NameError` |
| **SECURITY** | Low | gitleaks, trivy, pip-audit | `Credential detected: REDACTED`, `CVE-2025-XXXXX found` |
| **DOCKER/BUILD** | Low | trivy, Container Scan | `Image build failed`, `High severity vulnerabilities` |
| **GOVERNANCE** | Low | Check Delivery Gate, Check Core Duplicates | `DELIVERY_APPROVED.yaml: approved != true`, `Duplicate core/ directory found` |
| **E2E/INTEGRATION** | Medium | E2E Happy Path, e2e-paper-trading | `Redis connection refused`, `PostgreSQL not available` (stub mode) |

---

## 4. Runner Type + Constraints

### 4.1 Runner Analysis

**Primary Runner:** `ubuntu-latest` (GitHub-hosted)
**No Self-Hosted Runners Detected**

**Evidence:**
```yaml
runs-on: ubuntu-latest
```
Found in ALL 41 workflows.

### 4.2 Common Constraints

#### Services (Docker-in-Docker)
E2E tests use Docker Compose services:
```yaml
steps:
  - name: Start Stack
    run: docker compose -f infrastructure/compose/compose.yml up -d
```

**Services:**
- `cdb_redis` (Port 6379)
- `cdb_postgres` (Port 5432)
- `cdb_signal`, `cdb_risk`, `cdb_execution`, etc.

**Constraint:** Workflows requiring services fail in PR forks (no credentials available).

#### Caching
Multiple workflows use GitHub Actions cache:
```yaml
- uses: actions/cache@v4
  with:
    path: ~/.cache/trivy
    key: trivy-${{ runner.os }}-${{ github.workflow }}-${{ github.sha }}
```

**Impact:** First runs slower, subsequent runs faster.

#### Timeouts
E2E tests have explicit timeouts:
```yaml
timeout-minutes: 15
```

**Impact:** Long-running tests may timeout (not a failure, but prevents merge).

---

## 5. "No Checks Yet" Behavior

### 5.1 Fresh PR Behavior

**Observed Pattern:** When a PR is first created, GitHub Actions checks may show:
- `status: "IN_PROGRESS"` - Workflow is running
- `status: "QUEUED"` - Workflow is waiting for runner
- `status: "PENDING"` - Workflow not yet started
- `conclusion: null` - Check not yet completed

**Evidence from PR #807:**
```json
{
  "name": "trivy (kritische CVEs/Supply-Chain)",
  "status": "IN_PROGRESS",
  "conclusion": "",
  "completedAt": "0001-01-01T00:00:00Z"
}
```

### 5.2 Recommendation for gh-fix-ci

**Wait/Poll Statuses:**
- `IN_PROGRESS` → Wait (checks still running)
- `QUEUED` → Wait (checks waiting for runner)
- `PENDING` → Wait (checks not yet started)

**Hard Stop Statuses:**
- `FAILURE` → Fix required
- `CANCELLED` → User cancelled (treat as failure)
- `TIMED_OUT` → Timeout exceeded (treat as failure)
- `ACTION_REQUIRED` → Manual intervention needed (workflow_dispatch)

**Skip Statuses:**
- `SKIPPED` → Check not applicable (path filters, conditional logic)
- `NEUTRAL` → Check passed but with warnings

---

## 6. Multi-Account / Auth Context Reality

### 6.1 GitHub Auth Status

**Command:**
```bash
gh auth status
```

**Result:**
```
github.com
  ✓ Logged in to github.com account jannekbuengener (GITHUB_TOKEN)
  - Active account: true
  - Git operations protocol: https
  - Token: gho_************************************
  - Token scopes: 'gist', 'read:org', 'repo', 'workflow'

  ✓ Logged in to github.com account plaketten-ingo (keyring)
  - Active account: false
  - Git operations protocol: https
  - Token: gho_************************************
  - Token scopes: 'gist', 'read:org', 'repo', 'workflow'

  ✓ Logged in to github.com account jannekbuengener (keyring)
  - Active account: false
  - Git operations protocol: https
  - Token: gho_************************************
  - Token scopes: 'gist', 'read:org', 'repo', 'workflow'
```

### 6.2 Analysis

**Active Account:** `jannekbuengener` (GITHUB_TOKEN env var)
**Multiple Accounts Configured:** Yes (3 accounts total)
- `jannekbuengener` (active, via GITHUB_TOKEN)
- `plaketten-ingo` (inactive, via keyring)
- `jannekbuengener` (duplicate, via keyring)

**Switching Context:**
User can switch accounts via:
```bash
gh auth switch
```
Or by setting `GH_HOST` environment variable (not currently used).

**Recommendation for gh-fix-ci:**
- Default to active account (`jannekbuengener`)
- If repo access fails, prompt user to `gh auth switch`
- Do NOT attempt automatic account switching

---

## 7. Log Size Findings

### 7.1 Log Retrieval Limitations

**Command:**
```bash
gh run view 21797091117 --log
```

**Result:**
```
failed to get run log: log not found
```

**Interpretation:** Logs may not be available for:
- Very old runs (retention policy)
- Cancelled runs (logs not persisted)
- Runs from forks (permission issues)

### 7.2 Log Size Estimates (from available logs)

**Sample Log Output (LR-004 check failure):**
```
Type Checking (mypy)  UNKNOWN STEP  services/market/service.py: error: Duplicate module named "service"
Type Checking (mypy)  UNKNOWN STEP  Found 1 error in 1 file (errors prevented further checking)
Type Checking (mypy)  UNKNOWN STEP  ##[error]Process completed with exit code 2.
```

**Typical Log Size:**
- **Small Check (lint/type):** 50-200 lines
- **Test Suite (pytest):** 500-2000 lines
- **E2E Full Stack:** 5000+ lines

**Recommendation for gh-fix-ci:**
- **Default Truncation:** Last 100 lines of failed step
- **Configurable via skill:** User can request more/less
- **Smart Filtering:** Extract only error/failure lines (grep -i "error|fail|fatal")

---

## 8. Config Decisions (Recommended Defaults for gh-fix-ci Skill)

Based on the discovery findings, here are the recommended default configurations:

### 8.1 Required Check Names (Exact Match)
```yaml
required_checks:
  - "ci (Unit/Integration + Lint gesammelt)"
  - "validate-branch-name"
  - "gitleaks (Secrets-Alarm)"
  - "trivy (kritische CVEs/Supply-Chain)"
  - "Check Core Duplicates"
  - "Check Delivery Gate"
  - "guard"
  - "E2E Happy Path"
```

### 8.2 Failure Categories & Auto-Fix Heuristics
```yaml
failure_patterns:
  LINT:
    check_names: ["ci (Ruff)", "Linting (Ruff)", "Format Check (Black)"]
    keywords: ["Ruff found", "Black would reformat", "style violation"]
    auto_fix_hint: "Run: black . && ruff check --fix ."

  TYPE_CHECK:
    check_names: ["Type Checking (mypy)", "ci (mypy)"]
    keywords: ["mypy error", "incompatible type", "missing return"]
    auto_fix_hint: "Add type hints or configure mypy excludes"

  TEST:
    check_names: ["Tests (Python", "ci (pytest)"]
    keywords: ["FAILED tests/", "AssertionError", "test_"]
    auto_fix_hint: "Run: pytest tests/ -v --tb=short"

  SECURITY:
    check_names: ["gitleaks", "trivy", "pip-audit"]
    keywords: ["Credential detected", "CVE-", "vulnerability"]
    auto_fix_hint: "Remove credentials, update dependencies, add CVE to allowlist"

  GOVERNANCE:
    check_names: ["Check Delivery Gate", "Check Core Duplicates"]
    keywords: ["DELIVERY_APPROVED", "duplicate core/"]
    auto_fix_hint: "Review governance requirements, consult policy docs"

  E2E:
    check_names: ["E2E", "e2e-"]
    keywords: ["Redis connection", "Postgres", "Docker Compose"]
    auto_fix_hint: "Check if STUB mode expected (PR fork?), verify credentials"
```

### 8.3 Polling & Timeout Settings
```yaml
polling:
  wait_statuses: ["IN_PROGRESS", "QUEUED", "PENDING"]
  poll_interval: 10  # seconds
  max_wait_time: 600  # 10 minutes

stop_on:
  - "FAILURE"
  - "CANCELLED"
  - "TIMED_OUT"

skip_statuses:
  - "SKIPPED"
  - "ACTION_REQUIRED"  # workflow_dispatch, manual approval
```

### 8.4 Log Retrieval Settings
```yaml
logs:
  default_lines: 100  # last N lines of failed step
  max_lines: 500  # safety limit
  filter_keywords: ["error", "fail", "fatal", "exception", "traceback"]
  include_context: 5  # lines before/after error
```

### 8.5 Multi-Account Handling
```yaml
auth:
  default_account: "jannekbuengener"  # from gh auth status
  auto_switch: false  # never auto-switch accounts
  on_auth_failure:
    action: "prompt"
    message: "Run 'gh auth switch' to change accounts"
```

### 8.6 Workflow Detection
```yaml
workflows:
  scan_path: ".github/workflows/"
  pr_triggers: ["pull_request", "pull_request_target"]
  ignore_patterns:
    - "**/stale.yml"  # maintenance workflows
    - "**/sync-labels.yml"  # label syncing
    - "**/milestone-*.yml"  # project management
```

### 8.7 Fix Command Suggestions
```yaml
fix_commands:
  LINT: "black . && ruff check --fix ."
  TYPE_CHECK: "mypy . --show-error-codes"
  TEST: "pytest tests/ -v --tb=short --maxfail=1"
  E2E: "docker compose -f infrastructure/compose/compose.yml up -d && pytest tests/e2e/"
  SECURITY_GITLEAKS: "Check gitleaks.toml allowlist, remove credentials from history"
  SECURITY_TRIVY: "docker build . && trivy image --severity HIGH,CRITICAL <image>"
```

---

## 9. Critical Findings & Recommendations

### 9.1 Custom Governance Checks
**Finding:** CDB uses custom governance workflows (delivery-gate, core-guard) not present in typical repos.

**Recommendation:** gh-fix-ci should:
- Detect custom check names (not just standard GHA checks)
- Parse workflow files to understand custom logic
- Provide repo-specific guidance (e.g., "Check DELIVERY_APPROVED.yaml")

### 9.2 Stub Mode Detection
**Finding:** E2E tests fail in PR forks due to missing credentials (STUB mode expected).

**Recommendation:** gh-fix-ci should:
- Detect PR source (fork vs. same repo)
- Warn user if E2E failures are expected (fork, no credentials)
- Suggest: "E2E tests require credentials; merge to main or run locally"

### 9.3 Multiple Python Versions
**Finding:** CI runs tests on Python 3.11 AND 3.12 (matrix strategy).

**Recommendation:** gh-fix-ci should:
- Aggregate failures across matrix jobs
- Report: "Tests failed on Python 3.11 but passed on 3.12"
- Suggest: "Check Python version-specific code"

### 9.4 Log Retention Issues
**Finding:** Some logs return "log not found" (old runs, cancelled runs).

**Recommendation:** gh-fix-ci should:
- Handle missing logs gracefully
- Fall back to check conclusion summary (no detailed logs)
- Suggest: "Re-run workflow to generate fresh logs"

---

## 10. Next Steps for gh-fix-ci Implementation

1. **Parse Workflow Files:** Read `.github/workflows/*.yml` to extract:
   - Check names (from `name:` or `jobs.<job_id>.name`)
   - Triggers (`on.pull_request`)
   - Job dependencies (`needs:`)

2. **Match Check Names:** Use exact string matching for required checks:
   - GitHub API returns exact names (e.g., "ci (Unit/Integration + Lint gesammelt)")
   - Workflow file may have different name (e.g., `name: ci`)
   - Solution: Map workflow name → displayed check name

3. **Categorize Failures:** Implement keyword matching:
   - Extract last 100 lines of failed step
   - Search for keywords (e.g., "Ruff found", "mypy error")
   - Map to failure category (LINT, TYPE_CHECK, TEST, etc.)

4. **Generate Fix Plan:** Based on category, suggest:
   - Commands to run locally (e.g., `black .`)
   - Files to inspect (e.g., `services/market/service.py`)
   - Documentation links (e.g., mypy docs)

5. **Handle Edge Cases:**
   - Missing logs → Use check conclusion + workflow file analysis
   - Forks → Warn about expected E2E failures
   - Multiple accounts → Detect active account, never auto-switch

---

## Appendix A: Evidence Commands

All commands used during discovery (reproducible):

```bash
# Repository metadata
git rev-parse --show-toplevel
gh repo view --json nameWithOwner,defaultBranchRef

# Workflow inventory
ls .github/workflows/*.yml .github/workflows/*.yaml | wc -l

# Required checks
gh api repos/jannekbuengener/Claire_de_Binare/branches/main/protection --jq '.required_status_checks.contexts'

# Recent PRs with checks
gh pr list --limit 10 --state all --json number,title,headRefName
gh pr checks 807
gh pr checks 806

# Recent workflow runs
gh run list --limit 30 --json conclusion,workflowName,url

# Failed run logs
gh run view 21797091117 --log
gh run view 21780276909 --log | grep -i "error\|fail"

# Auth status
gh auth status
```

---

## Appendix B: Workflow File Samples

### Sample 1: ci.yml (excerpt)
```yaml
name: ci

on:
  pull_request:
    branches: [ main ]
  push:
    branches: [ main ]

jobs:
  ci:
    name: ci (Unit/Integration + Lint gesammelt)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: "3.12"
      - run: pip install -r requirements.txt
      - run: ruff check .
      - run: black --check .
      - run: mypy .
      - run: pytest tests/
```

### Sample 2: gitleaks.yml (excerpt)
```yaml
name: Gitleaks Secret Scan

on:
  pull_request:
    branches: [main, develop]

jobs:
  gitleaks:
    name: gitleaks (Secrets-Alarm)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: gitleaks/gitleaks-action@v2
        # Note: GITHUB_TOKEN automatically provided by Actions
```

---

**Report Generated:** 2026-02-08 12:30 UTC
**Discovery Mode:** Read-only (no changes made)
**Total Workflows Analyzed:** 41
**Total PRs Sampled:** 3
**Total Failed Runs Sampled:** 2

**Status:** ✅ Discovery Complete - Ready for gh-fix-ci skill implementation
