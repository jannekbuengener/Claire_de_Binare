# LR-001 Evidence Addendum: Required Checks Scope Change

**Task ID:** LR-001
**Task Title:** P0 Governance CI/CD Shield
**Addendum Date:** 2026-02-22
**Author:** Claude Code (Repo Analyst)
**Type:** Append-only addendum. Does not modify `LR-001-STATE.yaml` or `LR-001-EVIDENCE.md`.

---

## 1. Purpose and Scope

This addendum documents a material change to the branch protection required checks on `main` since the original LR-001 attestation (2026-02-03). The original `LR-001-EVIDENCE.md` attested 8 required status check contexts. Live API verification on 2026-02-22 confirms 1 required status check context.

This document is append-only. It does not rewrite or invalidate the original LR-001 evidence. It records the current state, the delta, and the governance questions that follow.

---

## 2. Live API State (2026-02-22)

**Source:** GitHub API via `gh api` for `repos/jannekbuengener/Claire_de_Binare/branches/main/protection`.

| Setting | Value |
|---|---|
| `enforce_admins.enabled` | `true` |
| `required_status_checks.strict` | `true` |
| `required_status_checks.contexts` | `["ci (Unit/Integration + Lint gesammelt)"]` |
| `required_conversation_resolution.enabled` | `true` |
| `allow_force_pushes.enabled` | `false` |
| `allow_deletions.enabled` | `false` |
| `required_pull_request_reviews.required_approving_review_count` | `0` |
| `required_signatures.enabled` | `false` |

**Verification commands (reproducible):**

```bash
# required checks (full)
gh api -H "Accept: application/vnd.github+json" \
  repos/jannekbuengener/Claire_de_Binare/branches/main/protection/required_status_checks

# required checks (compact)
gh api repos/jannekbuengener/Claire_de_Binare/branches/main/protection/required_status_checks \
  --jq '{strict, contexts}'
```

**Cross-reference:** `reports/REQUIRED_CHECK_CONTEXTS_BASELINE_main.json` (captured 2026-02-19T20:46:22+01:00) shows the same single context. The live API state on 2026-02-22 is consistent with the 2026-02-19 snapshot.

---

## 3. Delta vs LR-001 Original Attestation

### 3.1 Summary

| Attribute | LR-001 Evidence (2026-02-03) | Live API (2026-02-22) | Changed? |
|---|---|---|---|
| `enforce_admins.enabled` | `true` | `true` | No |
| `required_status_checks.strict` | `true` | `true` | No |
| Required contexts count | 8 | 1 | Yes |

### 3.2 Context-by-Context Comparison

| Context String | LR-001 (2026-02-03) | Live (2026-02-22) | Status |
|---|---|---|---|
| `ci (Unit/Integration + Lint gesammelt)` | Required | Required | Retained |
| `validate-branch-name` | Required | Not required | Removed |
| `gitleaks (Secrets-Alarm)` | Required | Not required | Removed |
| `trivy (kritische CVEs/Supply-Chain)` | Required | Not required | Removed |
| `Check Core Duplicates` | Required | Not required | Removed |
| `Check Delivery Gate` | Required | Not required | Removed |
| `guard` | Required | Not required | Removed |
| `E2E Happy Path` | Required | Not required | Removed |

7 contexts were removed from branch protection required checks between 2026-02-03 and 2026-02-19.

### 3.3 When Did the Change Occur?

The exact date of removal is not determined in this analysis. The LR-001 evidence records 8 contexts as of 2026-02-03. The baseline snapshot (`reports/REQUIRED_CHECK_CONTEXTS_BASELINE_main.json`) records 1 context as of 2026-02-19. The change occurred within that window.

---

## 4. Pre-Merge Viability of the Remaining Required Check

### 4.1 Workflow Identification

The required context `ci (Unit/Integration + Lint gesammelt)` is produced by:

- **File:** `.github/workflows/ci.yml` (not `ci.yaml`)
- **Trigger:** `on: pull_request: branches: [main]` (no paths filter)
- **Job ID:** `ci`
- **Job Name:** `ci (Unit/Integration + Lint gesammelt)` (exact match with required context string)

The workflow runs on all PRs targeting `main`.

### 4.2 Test Coverage in This Workflow

The job executes the following steps (source: `.github/workflows/ci.yml`):

| Step Name | Command | Notes |
|---|---|---|
| MCP Validation | `make mcp-config-validate MCP_CONFIG_PATHS="tests/fixtures/mcp_smoke_config.json"` | merge-blocking |
| Ruff | `ruff check .` | merge-blocking |
| Black | `black --config pyproject.toml --check` | diff-based, changed .py files only |
| Tests | `pytest -q` | runs all collected tests |

The project `pytest.ini` specifies `addopts = -v --strict-markers --tb=short` with no `-m` marker filter, so `pytest -q` runs all collected tests including those marked `@pytest.mark.contract`.

### 4.3 Check-Run Evidence on Real PRs

| PR | Title | Head SHA | Check-Run Name | Status | Conclusion |
|---|---|---|---|---|---|
| #895 | fix(build): restore Makefile targets/vars dropped in #894 | `0230f1a0` | `ci (Unit/Integration + Lint gesammelt)` | completed | success |
| #896 | ci: claude-code-review required check noop-pass (no skip) | `ffe4f425` | `ci (Unit/Integration + Lint gesammelt)` | completed | success |

**Verification command (reproducible):**

```bash
gh api -H "Accept: application/vnd.github+json" \
  repos/jannekbuengener/Claire_de_Binare/commits/<HEAD_SHA>/check-runs \
  --jq '.check_runs[] | {name: .name, status: .status, conclusion: .conclusion}'
```

The remaining required check is reliably produced on PRs and functions as a pre-merge gate.

---

## 5. Security Posture Change

### 5.1 What Is Still Merge-Blocking (Pre-Merge)

The following are enforced pre-merge via the `ci (Unit/Integration + Lint gesammelt)` job in `.github/workflows/ci.yml`:

| Gate | Mechanism |
|---|---|
| MCP config validation | `make mcp-config-validate ...` |
| Ruff lint | `ruff check .` |
| Black formatting (changed .py files) | `black --check ...` |
| All pytest-collected tests (unit, integration, contract) | `pytest -q` |

Additionally enforced by branch protection settings (not by `ci.yml`):

| Gate | Source |
|---|---|
| Branch must be up-to-date with main | `required_status_checks.strict = true` |
| Admin bypass prevented | `enforce_admins.enabled = true` |
| Conversation resolution required | `required_conversation_resolution.enabled = true` |

### 5.2 What Is No Longer Merge-Blocking

The following checks were previously required for merge. They are no longer listed in `required_status_checks.contexts`. PRs can merge without these checks passing or being present:

| Removed Context | Original Workflow | Current Trigger | Notes |
|---|---|---|---|
| `validate-branch-name` | `branch-policy.yml` | `workflow_dispatch` + `schedule` | no `pull_request` trigger |
| `gitleaks (Secrets-Alarm)` | `gitleaks.yml` | `push [main]` + `schedule` + `dispatch` | no `pull_request` trigger |
| `trivy (kritische CVEs/Supply-Chain)` | `trivy.yml` | `push` + `schedule` + `dispatch` | no `pull_request`; `exit-code: "0"` |
| `Check Core Duplicates` | `core-guard.yml` | `push [main]` + `schedule` + `dispatch` | no `pull_request`; `continue-on-error: true` |
| `Check Delivery Gate` | `delivery-gate.yml` | `workflow_dispatch` + `schedule` | no `pull_request` trigger |
| `guard` | `docs-hub-guard.yml` | `push ["main"]` + `schedule` + `dispatch` | no `pull_request` trigger |
| `E2E Happy Path` | `e2e-happy-path.yaml` | `push [main]` + `schedule` + `dispatch` | no `pull_request` trigger |

---

## 6. Compensating Controls

The following controls still operate but are not merge-blocking:

| Control | Workflow | Frequency | Enforcement |
|---|---|---|---|
| Branch name validation | `branch-policy.yml` | daily schedule + manual | post-merge detection |
| Secret scanning | `gitleaks.yml` | push to main + schedule | post-merge detection |
| Container vulnerability scan | `trivy.yml` | push to main + schedule | reporting only (`exit-code: "0"`) |
| Core duplicates guard | `core-guard.yml` | push to main + weekly schedule | advisory (`continue-on-error: true`) |
| Delivery gate | `delivery-gate.yml` | daily schedule + manual | post-merge detection |
| Docs hub guard | `docs-hub-guard.yml` | push to main + weekly schedule | post-merge detection |
| E2E Happy Path | `e2e-happy-path.yaml` | push to main + weekly schedule | post-merge detection |
| Governance audit | `governance-audit.yml` | weekly schedule | reporting only |
| Required checks audit sentinel | `required-checks-audit.yml` | manual | on-demand audit |

These controls detect issues after merge to main or on schedule. They do not prevent merging of PRs that would fail these checks.

---

## 7. Open Governance Questions

### 7.1 Was the 8-to-1 Reduction Deliberate?

Unknown from repo evidence alone. The audit report `reports/CI_REQUIRED_CHECKS_AUDIT_2026-02-19.md` documents the current state and describes a promotion plan for Trivy and E2E Happy Path back to required status. The report does not state whether the reduction was an intentional governance decision or a side effect of workflow refactoring.

### 7.2 Is 1 Required Check Sufficient?

The remaining check covers: MCP validation, ruff lint, black formatting, and all pytest-collected tests (unit, integration, contract). It does not cover: secret scanning, vulnerability scanning, branch naming, delivery gate, E2E tests, core duplicates guard, docs hub guard.

Whether 1 check is sufficient depends on the project's risk tolerance. This addendum does not make that judgment.

### 7.3 What Is the Status of the Promotion Plan?

`reports/CI_REQUIRED_CHECKS_AUDIT_2026-02-19.md` (Section "Step 4") defines promotion criteria for Trivy and E2E Happy Path:

- Trivy: Main-Streak 1 (gate requires 10). PR-Streak 0 (gate requires 3). Status: not promotion-ready.
- E2E Happy Path: Main-Streak 6 (gate requires 10). PR-Streak 6 (gate requires 3). Status: approaching but not met.

No evidence of promotion execution found in repo as of 2026-02-22.

---

## 8. Recommendation

LR-001 re-attestation is recommended.

The original LR-001 attestation stated: "8 Required Checks -- All critical guards enforced" (`LR-001-EVIDENCE.md`, line 38). The current state is 1 required check. This is a material scope change to the attested governance posture.

What is unchanged and still valid:

- `enforce_admins: true` (admin bypass still prevented)
- `strict: true` (branch must be up-to-date)
- The remaining 1 check functions correctly as a pre-merge gate

What changed:

- 7 of 8 attested required checks are no longer merge-blocking
- The governance posture shifted from pre-merge prevention (8 gates) to partial pre-merge (1 gate) plus post-merge detection (7 workflows on push/cron)

Re-attestation means documenting the new scope as the attested state. Options (for governance decision, not this document):

**(A)** Re-attest LR-001 with 1 required check as the new baseline. Accept that the remaining 7 checks operate as post-merge detection. Document this as a deliberate governance posture change.

**(B)** Restore some or all of the 7 removed checks to required status (requires workflow trigger changes to add `pull_request:` back, plus branch protection API update). Then re-attest with the restored count.

**(C)** Follow the existing promotion plan in `reports/CI_REQUIRED_CHECKS_AUDIT_2026-02-19.md`. Wait for Trivy and E2E Happy Path to meet promotion gates, then promote and re-attest with the expanded set.

This addendum does not choose between these options. That is a governance decision.

---

## Appendix: Reproduction Commands

```bash
# Branch protection state (full)
gh api -H "Accept: application/vnd.github+json" \
  repos/jannekbuengener/Claire_de_Binare/branches/main/protection/required_status_checks

# Branch protection state (compact: strict + contexts only)
gh api repos/jannekbuengener/Claire_de_Binare/branches/main/protection/required_status_checks \
  --jq '{strict, contexts}'

# enforce_admins (full)
gh api -H "Accept: application/vnd.github+json" \
  repos/jannekbuengener/Claire_de_Binare/branches/main/protection/enforce_admins

# enforce_admins (compact)
gh api repos/jannekbuengener/Claire_de_Binare/branches/main/protection/enforce_admins \
  --jq '.enabled'

# Check-runs on a specific PR commit
gh api -H "Accept: application/vnd.github+json" \
  repos/jannekbuengener/Claire_de_Binare/commits/<HEAD_SHA>/check-runs \
  --jq '.check_runs[] | {name: .name, status: .status, conclusion: .conclusion}'

# Check-runs (compact: names only)
gh api repos/jannekbuengener/Claire_de_Binare/commits/<HEAD_SHA>/check-runs \
  --jq '[.check_runs[].name]'

# Workflow trigger inspection
grep -n "^on:" -A 10 .github/workflows/ci.yml
grep -n "^on:" -A 10 .github/workflows/ci.yaml

# pytest config (marker filter check)
grep -n "addopts\|markers\|contract" pytest.ini
```

---

**End of addendum. No files modified beyond this document. No commits created.**
