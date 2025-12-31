# CI/CD Pipeline Guide - Claire de Binare

**Issue:** #112
**Version:** 1.0
**Last Updated:** 2025-12-28

---

## Overview

This guide documents all CI/CD workflows in the Claire de Binare project.
The pipeline uses GitHub Actions for automation.

---

## Pipeline Architecture

```
PR Opened/Synced
      │
      ▼
┌─────────────────────────────────────────────────────────────┐
│                    QUALITY GATES                            │
├─────────────────┬─────────────────┬─────────────────────────┤
│  Security       │  Testing        │  Governance             │
│  - Trivy        │  - E2E Tests    │  - Delivery Gate        │
│  - Docker Scout │                 │  - Emoji Filter         │
│  - Gitleaks     │                 │  - Auto-Label           │
└─────────────────┴─────────────────┴─────────────────────────┘
      │
      ▼
   PR Merge → main
```

---

## 1. Security Workflows

### 1.1 Security Scan (`security-scan.yml`)

**Purpose:** Container vulnerability scanning

**Triggers:**
- Weekly (Monday 02:00 UTC)
- PR changes to `services/**/Dockerfile`, `infrastructure/compose/**`
- Manual dispatch

**Tools Used:**
| Tool | Images | Exit on Failure |
|------|--------|-----------------|
| Trivy | Base + Custom | Custom only |
| Docker Scout | Base + Custom | Custom only |

**Base Images Scanned:**
- `redis:7.4.1-alpine`
- `postgres:15.11-alpine`
- `prom/prometheus:v3.1.0`
- `grafana/grafana:11.4.0`

**Custom Services Scanned:**
- allocation, db_writer, execution, market
- regime, risk, signal, ws

**Outputs:**
- SARIF reports → GitHub Security tab
- Text reports → Artifacts (30 days retention)

### 1.2 Gitleaks (`gitleaks.yml`)

**Purpose:** Secret detection in code

**Triggers:**
- All PRs
- Weekly full scan

**Configuration:** `gitleaks.toml`

---

## 2. Testing Workflows

### 2.1 E2E Tests (`e2e-tests.yml`)

**Purpose:** End-to-end paper trading tests

**Triggers:**
- PRs modifying: `services/**`, `tests/e2e/**`, `infrastructure/**`
- Manual dispatch

**Steps:**
1. Set up Python 3.11
2. Start Docker stack (base + dev)
3. Health check Redis, Postgres, Core services
4. Run `pytest tests/e2e/test_paper_trading_p0.py`
5. Capture logs on failure
6. Cleanup containers

**Timeout:** 15 minutes

**Environment Variables:**
```yaml
REDIS_PASSWORD: ${{ secrets.REDIS_PASSWORD }}
E2E_RUN: 1
```

---

## 3. Governance Workflows

### 3.1 Delivery Gate (`delivery-gate.yml`)

**Purpose:** Enforce human approval for merges (Constitution §4.2)

**Triggers:**
- All PRs to `main`

**Mechanism:**
- Checks `governance/DELIVERY_APPROVED.yaml`
- Requires `delivery.approved: true` for merge
- Exception labels bypass the gate

**File Format:**
```yaml
delivery:
  approved: true
  reason: "M7 Release candidate"
  approved_by: "Jannek"
```

### 3.2 Emoji Filter (`emoji-filter.yml`)

**Purpose:** Prevent emojis in production code

**Triggers:**
- All PRs

**Configuration:** Context-aware (ignores comments, strings)

### 3.3 Auto-Label (`auto-label.yml`)

**Purpose:** Automatic PR labeling based on paths

**Labels Applied:**
| Path Pattern | Label |
|-------------|-------|
| `services/**` | `scope:services` |
| `infrastructure/**` | `scope:infra` |
| `tests/**` | `scope:tests` |
| `docs/**` | `type:docs` |

---

## 4. AI Agent Workflows

### 4.1 Claude Code Review (`claude-code-review.yml`)

**Purpose:** AI-assisted code review

**Triggers:**
- PRs with specific labels

### 4.2 Gemini Triage (`gemini-triage.yml`)

**Purpose:** AI-assisted issue triage

**Triggers:**
- New issues
- Scheduled (daily)

### 4.3 Gemini Review (`gemini-review.yml`)

**Purpose:** AI-assisted governance review

**Triggers:**
- PRs modifying governance files

---

## 5. Housekeeping Workflows

### 5.1 Stale Bot (`stale.yml`)

**Purpose:** Close inactive issues/PRs

**Schedule:** Daily

**Configuration:**
- Issues: Stale after 60 days, close after 7 days
- PRs: Stale after 30 days, close after 7 days

### 5.2 Sync Labels (`sync-labels.yml`)

**Purpose:** Synchronize label definitions

**Triggers:**
- Changes to `.github/labels.yml`

---

## 6. All Workflows Summary

| Workflow | Trigger | Purpose | Required |
|----------|---------|---------|----------|
| `security-scan.yml` | Weekly + PR | Container scanning | No |
| `gitleaks.yml` | PR | Secret detection | Yes |
| `e2e-tests.yml` | PR (paths) | E2E testing | Yes |
| `delivery-gate.yml` | PR to main | Human approval | Yes |
| `emoji-filter.yml` | PR | Code quality | No |
| `auto-label.yml` | PR | Auto-labeling | No |
| `stale.yml` | Schedule | Housekeeping | No |
| `claude-code-review.yml` | PR (labeled) | AI review | No |
| `gemini-triage.yml` | Issue/Schedule | AI triage | No |

---

## 7. Local Development

### Running CI Locally

**Security Scan:**
```bash
# Trivy scan
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image cdb_signal:latest

# Gitleaks
gitleaks detect --source=. --config=gitleaks.toml
```

**E2E Tests:**
```bash
cd infrastructure/compose
docker-compose -f base.yml -f dev.yml up -d

# Wait for services
E2E_RUN=1 pytest tests/e2e/test_paper_trading_p0.py -v

# Cleanup
docker-compose -f base.yml -f dev.yml down -v
```

---

## 8. Required Secrets

| Secret | Purpose | Required By |
|--------|---------|-------------|
| `REDIS_PASSWORD` | Redis authentication | E2E tests |
| `GITHUB_TOKEN` | API access | Auto-generated |
| `ANTHROPIC_API_KEY` | Claude integration | Claude workflows |
| `GOOGLE_API_KEY` | Gemini integration | Gemini workflows |

---

## 9. Branch Protection

**Main Branch Rules:**
- Require PR before merging
- Require status checks:
  - `delivery-gate`
  - `gitleaks`
- Require conversation resolution

---

## References

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Trivy Documentation](https://aquasecurity.github.io/trivy/)
- [Gitleaks Documentation](https://gitleaks.io/)
- [CDB Constitution](../../governance/CDB_CONSTITUTION.md)

---

**Next Review:** Quarterly
**Owner:** DevOps Team
