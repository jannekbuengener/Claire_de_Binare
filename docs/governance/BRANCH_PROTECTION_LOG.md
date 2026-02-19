# Branch Protection Change Log

This document records governance interventions on branch protection rules for audit trail purposes.

---

## 2026-02-15T19:18:00Z - Phase 8C Merge (PR #839)

**Context:** Solo-maintainer repo with `required_pull_request_reviews` blocking merge despite all status checks passing.

**Problem:** PR #839 (Phase 8C: Correlation Chain) was BLOCKED even though:
- All 7 required status checks: PASS
- `required_approving_review_count`: 0 (no approvals actually required)
- `enforce_admins`: true (admins also blocked)

**Actions Taken:**
1. Disabled `enforce_admins` via `gh api ... -X DELETE`
2. Removed `required_pull_request_reviews` via `gh api ... -X DELETE`
3. Merged PR #839 with `gh pr merge 839 --squash --admin`
4. Re-enabled `enforce_admins` via `gh api ... -X POST`

**Final State:**
| Setting | Value |
|---------|-------|
| `required_status_checks` | ✅ ACTIVE (7 checks) |
| `required_pull_request_reviews` | ❌ REMOVED |
| `enforce_admins` | ✅ ACTIVE |
| `required_conversation_resolution` | ✅ ACTIVE |

**Rationale:**
- Solo-maintainer: approval gate provides no security benefit
- CI status checks remain the actual gatekeeper
- `enforce_admins` restored to prevent accidental force-push

**Decision:** CI is the gatekeeper. Reviews are optional for solo-maintainer workflow.

**Approver:** jannekbuengener (repo owner)

---

## 2026-02-16T10:10:00Z - Solo-Maintainer Mode (PR #846)

**Context:** PR #846 (fix: psycopg2-binary for signal service) blocked by `required_approving_review_count: 1` despite self-approval being impossible on GitHub.

**Problem:**
- GitHub blocks self-approval: "Cannot approve your own pull request"
- Solo-maintainer has no one to approve PRs
- All required status checks: PASS

**Action Taken:**
```bash
gh api repos/jannekbuengener/Claire_de_Binare/branches/main/protection/required_pull_request_reviews \
  --method PATCH --field required_approving_review_count=0
```

**Final State:**
| Setting | Before | After |
|---------|--------|-------|
| `required_approving_review_count` | 1 | 0 |

**Rationale:**
- Solo-maintainer mode: approval requirement is unworkable
- CI status checks (7 required) remain the actual gatekeeper
- Bot reviews with suggestions still create unresolved threads (caught by `required_conversation_resolution`)

**Decision:** Reviews remain optional. CI + conversation resolution = sufficient governance for solo-maintainer.

**Approver:** jannekbuengener (repo owner)

---

## GitHub Actions: MODE 1 (Strict Approval) für action_required Runs (Bots/Apps)

**Date/Time (Europe/Berlin):** `2026-02-19T19:47:43+01:00`  
**Date/Time (UTC):** `2026-02-19T18:47:33Z`

### Entscheidung
- Chosen mode: MODE 1 (Strict Approval)
- Kurzbegründung: Sicherheits-/Governance-Default, Approval-Gates bleiben aktiv.
- No workflow/code changes.

### Guardrail Settings (Facts)
- `actions.enabled=true`
- `allowed_actions=all`
- `sha_pinning_required=true`
- `default_workflow_permissions=read` (least privilege)

### Evidence Notes (Before/After)
Before (triage anchors):
- Run `22192989773` (`ci`, PR `#867`, `copilot/sub-pr-865`): `conclusion=action_required`, `jobs total_count=0`  
  Link: `https://github.com/jannekbuengener/Claire_de_Binare/actions/runs/22192989773`
- Run `22192989851` (`E2E Happy Path`): `conclusion=action_required`, `jobs total_count=0`  
  Link: `https://github.com/jannekbuengener/Claire_de_Binare/actions/runs/22192989851`

Unblock action (maintainer):
- `rerun from maintainer context (UI/CLI)`

After:
- Run `22192989773` attempt `2`: `conclusion=success`, jobs present (`ci (Unit/Integration + Lint gesammelt)`)
- Run `22192989851` attempt `2`: `conclusion=success`, jobs present (`E2E Happy Path`)

### Wichtiges operatives Finding
- GitHub fork-approval API endpoint (`/actions/runs/{id}/approve`) returns `403` here because this is not a fork pull request; predictable unblock path is rerun from maintainer context (UI/CLI), which schedules jobs immediately.

### Verweise / Runbook
- `docs/ci/ACTION_REQUIRED_RUNBOOK.md`

### Safety / No-Change Statement
- Docs-only log entry.
- No workflow logic changed.
- No Docker/trading/infrastructure changes.
- No secrets logged.

### Rollback
- Revert commit / revert PR.
