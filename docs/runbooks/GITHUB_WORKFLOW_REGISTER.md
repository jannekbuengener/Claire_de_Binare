# GitHub Workflow Register

**Repo:** Claire de Binare
**Canon date:** 2026-05 (generated for #1640 from #1633 audit + live trigger scan)
**Total workflow definitions:** 67 YAML files
**Non-workflow file in `/workflows/`:** `labels.json` (label spec — consumed by `sync-labels.yml`)

**Related docs:**
- `.github/README.md` — folder layout and navigation
- `docs/runbooks/GITHUB_CONTROL_PLANE_RUNBOOK.md` — how to read and edit workflows
- `docs/runbooks/GITHUB_CONTROL_PLANE_GRAPH.md` — relationship matrix + Mermaid graph
- `docs/runbooks/CONTROL_REGISTER.md` — Board stage, LR verdict, active infra workflows

---

## Column key

| Column | Meaning |
|---|---|
| **File** | Filename under `.github/workflows/` |
| **Status** | `aktiv` / `manual-only` / `parked` / `historisch` |
| **Trigger(s)** | Abbreviated: `push`, `PR`, `sched`, `dispatch`, `wrun` (workflow_run), `wcall` (workflow_call), `issues`, `PRcomment` |
| **Purpose** | One-line description |
| **Scripts / Prompts** | Supporting files from `.github/scripts/`, `.github/prompts/`, or `.github/commands/` where applicable |
| **Key outputs** | Primary outputs / artifacts / mutation surfaces |
| **FP** | Fail posture: `C` = fail-closed (blocks CI/merge), `O` = fail-open (advisory) |
| **HT** | Human touchpoint |

---

## #1640 minimum-field coverage model (repo-true, fail-closed)

This register intentionally uses a compact two-layer model:
1. **Workflow row layer** (`File`, `Purpose`, `Trigger(s)`, support links, outputs/mutations, `FP`, `HT`)
2. **Profile layer** (permissions, primary inputs, owner/canon) with explicit defaults + explicit overrides

If a field cannot be resolved from row + profile + override, treat it as **not satisfied** and inspect the workflow YAML directly before making governance claims.

| #1640 minimum field | Where modeled |
|---|---|
| file path | `File` column |
| purpose | `Purpose` column |
| trigger(s) | `Trigger(s)` column |
| permissions | Profile layer below (`perm:*`) + workflow override table |
| primary inputs | Profile layer below (`in:*`) + workflow override table |
| primary outputs / artifacts | `Key outputs` column |
| linked prompts / scripts / commands | `Scripts / Prompts` column |
| linked issues / project surfaces / labels / comments / repo mutations | `Key outputs` column (surface terms) |
| fail posture | `FP` column |
| human touchpoint | `HT` column |
| owner / canonical doc link | Register-wide defaults below |

### Register-wide defaults (all workflow entries)

- **Owner:** `@jannekbuengener` via `.github/CODEOWNERS`
- **Canonical doc set:** `.github/README.md`, this register, `docs/runbooks/GITHUB_CONTROL_PLANE_RUNBOOK.md`, `docs/runbooks/GITHUB_CONTROL_PLANE_GRAPH.md`
- **Human review rule:** merge/closure decisions are human-gated; no automatic acceptance inference from this document alone

### Permission and primary-input profiles

**Permission profiles**
- `perm:r` — explicit read-only scopes (or no explicit write scopes)
- `perm:w-issues` — includes `issues:write`
- `perm:w-pr` — includes `pull-requests:write`
- `perm:w-contents` — includes `contents:write`
- `perm:w-packages` — includes `packages:write`
- `perm:w-security` — includes `security-events:write`
- `perm:oidc` — includes `id-token:write`
- `perm:models-read` — includes `models:read`
- `perm:checks-read` — includes `checks:read`
- `perm:actions-read` — includes `actions:read`
- `perm:pr-read` — includes `pull-requests:read`
- `perm:implicit` — no explicit top-level permissions block (evaluate YAML/job-level scopes directly)

**Primary-input profiles**
- `in:event` — GitHub event payload for declared trigger
- `in:dispatch` — explicit `workflow_dispatch` inputs
- `in:schedule` — cron/time-based trigger input
- `in:wrun` / `in:wcall` — upstream workflow context
- `in:labels-spec` — `.github/workflows/labels.json`
- `in:script:*` / `in:prompt:*` / `in:command:*` — linked support artifacts
- `in:control-register` — `docs/runbooks/CONTROL_REGISTER.md` consumed at runtime

### Group baselines (inherit unless overridden below)

| Group | Permission baseline | Primary-input baseline |
|---|---|---|
| Group 1 Reconcile | `perm:r` | `in:event` / `in:dispatch` / `in:schedule` |
| Group 2 CI / Quality | `perm:r` | `in:event` / `in:dispatch` / `in:schedule` |
| Group 3 Spezialpfad / AI / Agent | `perm:r` | `in:event` / `in:dispatch` |
| Group 4 Hygiene | `perm:r` | `in:event` / `in:dispatch` / `in:schedule` |
| Group 5 Reporting / Control | `perm:r` | `in:event` / `in:dispatch` / `in:schedule` |
| Group 6 Audit / Governance | `perm:r` | `in:event` / `in:dispatch` / `in:schedule` |
| Group 7 Delivery / Gates | `perm:r` | `in:event` / `in:dispatch` / `in:schedule` |
| Group 8 Security | `perm:r` | `in:event` / `in:dispatch` / `in:schedule` |
| Group 9 Historisch / Unklar | `perm:r` | `in:event` / `in:dispatch` |

### Workflow-specific permission/input overrides

Only entries that differ materially from their group baseline are listed.

| Workflow | Permission override | Primary-input override |
|---|---|---|
| `sync-labels.yml` | `perm:w-issues` | `in:labels-spec` |
| `label-bootstrap.yml` | `perm:w-issues`, `perm:w-pr` | `in:labels-spec` |
| `auto-milestone.yml` | `perm:w-issues` | — |
| `auto-milestone-label-dispatch.yml` | `perm:w-contents` | — |
| `auto-milestone-pr-apply.yml` | `perm:w-issues` | `in:wrun` |
| `control_board_auto_routing.yml` | `perm:w-issues` | — |
| `control-board-routing-label-dispatch.yml` | `perm:w-contents` | — |
| `cdb-backlog-curation.yml` | `perm:w-issues` | `in:script:backlog_curation.py` |
| `cdb-backlog-anomaly-escalation.yml` | `perm:w-issues`, `perm:actions-read` | `in:wrun`, `in:script:backlog_anomaly_escalation.py` |
| `cdb-daily-delta-triage.yml` | `perm:w-issues` | `in:script:daily_delta_triage.py`, `in:control-register` |
| `cdb-weekly-control-hygiene-classifier.yml` | `perm:w-issues` | `in:script:weekly_control_hygiene_classifier.py` |
| `cdb-post-merge-followup-scanner.yml` | `perm:w-issues`, `perm:models-read` | `in:script:post_merge_followup_scanner.py`, `in:prompt:cdb-control-followup.prompt.yml` |
| `cdb-control-followup-classifier.yml` | `perm:w-issues`, `perm:models-read` | `in:script:run_cdb_control_followup.sh`, `in:prompt:cdb-control-followup.prompt.yml` |
| `weekly_digest.yml` | `perm:implicit` | — |
| `weekly_digest_failure_alert.yml` | `perm:w-issues` | `in:wrun` |
| `claude.yml` | `perm:oidc` | — |
| `claude-code-review.yml` | `perm:oidc` | — |
| `opencode.yml` | `perm:oidc` | — |
| `gemini-dispatch.yml` | `perm:implicit` | — |
| `gemini-invoke.yml` | `perm:w-issues`, `perm:w-pr`, `perm:oidc` | `in:wcall`, `in:command:gemini-invoke.toml` |
| `gemini-review.yml` | `perm:w-issues`, `perm:w-pr`, `perm:oidc` | `in:wcall`, `in:command:gemini-review.toml` |
| `gemini-triage.yml` | `perm:w-issues`, `perm:w-pr`, `perm:oidc` | `in:wcall`, `in:command:gemini-triage.toml` |
| `gemini-scheduled-triage.yml` | `perm:w-issues`, `perm:w-pr`, `perm:oidc` | `in:command:gemini-scheduled-triage.toml` |
| `emoji-filter.yml` | `perm:w-issues` | `in:script:advanced-emoji-filter.py` |
| `emoji-bot.yml` | `perm:w-contents` | `in:script:advanced-emoji-filter.py` |
| `e2e-tests.yml` | `perm:w-issues` | — |
| `root-session-hygiene-warning.yml` | — | `in:script:root_session_hygiene_warn.py` |
| `copilot-housekeeping.yml` | `perm:w-issues`, `perm:w-pr` | — |
| `bulk-issue-labeling.yml` | `perm:w-issues` | — |
| `milestone-assignment.yml` | `perm:w-issues` | — |
| `required-checks-audit.yml` | `perm:checks-read` (plus read-only scopes) | — |
| `governance-audit.yml` | `perm:actions-read` (plus read-only scopes) | — |
| `ai-review-router.yml` | `perm:w-pr` | — |
| `smart-insights.yml` | `perm:implicit` | — |
| `delivery-gate.yml` | `perm:pr-read` (plus read-only scopes) | — |
| `docker-publish.yml` | `perm:w-packages` | — |
| `gitleaks.yml` | `perm:w-security` | — |
| `trivy.yml` | `perm:w-security` | — |
| `security-scan.yml` | `perm:w-security` | — |
| `stale.yml` | `perm:implicit` | — |

---

## Group 1: Reconcile — 14 workflows

Label, milestone, and project board management.

> ⚠️ All workflows in this group fire on `issues` labeled events. Label cascades can trigger many of them simultaneously.

| File | Status | Trigger(s) | Purpose | Scripts | Key Outputs | FP | HT |
|---|---|---|---|---|---|---|---|
| `sync-labels.yml` | aktiv | push, dispatch | Sync labels from `labels.json` to GitHub repo | — | Creates/updates/deletes repo labels | O | After `labels.json` edit |
| `label-bootstrap.yml` | manual-only | dispatch | One-shot label init from `labels.json` | — | Creates all labels | O | Operator: initial setup |
| `auto-milestone.yml` | aktiv | issues, dispatch | Assign milestone to issues based on labels | — | Milestone assigned to issue | O | None (automatic) |
| `auto-milestone-label-dispatch.yml` | aktiv | issues | Dispatch milestone label assignment sub-flow | — | Triggers downstream flow | O | None (automatic) |
| `auto-milestone-pr-apply.yml` | aktiv | wrun | Apply milestone to PR after upstream completes | — | Milestone assigned to PR | O | None (automatic) |
| `auto-milestone-pr-intent.yml` | aktiv | PR | Detect milestone intent on PR open | — | PR label, milestone hint | O | None (automatic) |
| `milestone_stage_label_sync.yml` | aktiv | issues | Sync milestone stage to labels | — | Issue labels updated | O | None (automatic) |
| `control_board_upsert.yml` | aktiv | dispatch, sched (Mon 02:30 UTC) | Create/upsert GitHub Project board items | — | Project board items | O | Weekly review in #1445 |
| `control_board_auto_routing.yml` | aktiv | issues, PR | Route issues/PRs to project board | — | Project board item, label | O | None (automatic) |
| `control-board-routing-label-dispatch.yml` | aktiv | issues | Dispatch routing label for board | — | Label on issue | O | None (automatic) |
| `project_reconcile_daily.yml` | aktiv | sched, dispatch | Daily project board reconciliation | — | Project board state reconciled | O | Daily check in #1445 |
| `project_status_label_map.yml` | aktiv | issues | Map project status column to labels | — | Labels on issue | O | None (automatic) |
| `project_status_sync.yml` | aktiv | issues | Sync issue labels back to project status | — | Project status field updated | O | None (automatic) |
| `add_to_project.yml` | aktiv | issues | Add issues to GitHub Project | — | Issue added to project | O | None (automatic) |

**Gold-im-Keller candidate:** The `control_board_upsert.yml` + `project_reconcile_daily.yml` + `project_status_sync.yml` triad powers the automated kanban — mostly underdocumented.

---

## Group 2: CI / Quality Gates — 11 workflows

Build, test, and quality assurance automation.

> `ci.yml` is the **canonical required check**. `ci.yaml` is frozen legacy — do not activate or merge.

| File | Status | Trigger(s) | Purpose | Scripts | Key Outputs | FP | HT |
|---|---|---|---|---|---|---|---|
| `ci.yml` | aktiv | push, PR | Canonical CI gate: lint (ruff, black), pytest unit+integration | — | CI pass/fail on PR | **C** | Required check; blocks merge |
| `ci.yaml` | historisch | push, PR | **FROZEN legacy copy of ci.yml** — do not activate | — | Duplicate CI (frozen) | C | Do not touch |
| `contracts.yml` | aktiv | push, dispatch, sched | Contract/schema smoke tests | — | Contract test results | O | On contract schema changes |
| `lr021_replay_smoke.yml` | aktiv | dispatch, sched | LR-021 offline replay smoke (control-visible artifact bundle) | — | PASS/FAIL + Step Summary + `replay-smoke-<run_id>` artifact | O | Cockpit `#1445` spiegeln; optional `#1784`/`#1786` |
| `python-compat.yml` | aktiv | sched, dispatch, push | Python version compatibility matrix | — | Compat matrix results | O | On major Python upgrade |
| `performance-monitor.yml` | aktiv | push, dispatch, sched | Performance benchmark monitoring | — | Perf report / artifact | O | On regression detection |
| `e2e.yml` | aktiv | push, dispatch, sched | End-to-end test suite (container-required) | — | E2E pass/fail | O | Local/CD env only |
| `e2e-tests.yml` | aktiv | dispatch, sched | E2E test variant (alternate config) | — | E2E pass/fail | O | Manual trigger / scheduled |
| `e2e-happy-path.yaml` | aktiv | push, dispatch, sched | Happy-path E2E post-merge | — | Happy-path pass/fail | O | Post-merge review |
| `core-guard.yml` | aktiv | push, dispatch, sched | Core service guard: validates critical service health | — | Guard pass/fail | O | On core service changes |
| `shadow-soak-evidence.yml` | aktiv | dispatch, sched | Shadow soak evidence runner | — | Evidence artifact | O | Operator: soak review |

**Note:** E2E and `local_only` tests excluded from CI by default. `ci.yml` runs: `pytest -q -k "not test_mcp_time_server_runtime"`.

---

## Group 3: Spezialpfad / AI / Agent — 11 workflows

AI-backed review, triage, agent invocation, emoji automation, and MCP runtime.

> Gemini `workflow_call` workflows (`gemini-invoke`, `gemini-review`, `gemini-triage`) are reusable libraries — they have **no standalone trigger** and currently have **no internal caller** in this repo.
>
> **`.github/commands/*.toml` coupling model:** Each Gemini workflow passes `prompt: '/command-name'` to the `run-gemini-cli` action. By Gemini CLI convention, `/command-name` resolves to `.github/commands/command-name.toml` at runtime. These TOML files are the **actual runtime prompt inputs** — not documentation stubs or placeholders. Without the TOML file the corresponding workflow would have no prompt to execute.
>
> **`gemini-dispatch.yml` is currently a noop placeholder.** Its implementation prints a placeholder string and does not invoke any of the reusable Gemini sub-workflows. The three `workflow_call` workflows are therefore not reachable from within this repo through an internal trigger chain.

| File | Status | Trigger(s) | Purpose | Scripts | Key Outputs | FP | HT |
|---|---|---|---|---|---|---|---|
| `claude.yml` | aktiv | PR, issues | Invoke Claude AI for issue/PR assistance | — | Issue/PR comment from Claude | O | AI-assisted; review response |
| `claude-code-review.yml` | aktiv | PR | Claude automated code review on PRs | — | PR review comment | O | Review AI feedback |
| `opencode.yml` | aktiv | PRcomment | Invoke OpenCode AI on PR review comment | — | PR follow-up comment | O | Review AI feedback |
| `gemini-dispatch.yml` | aktiv | dispatch | **Noop placeholder** — does not invoke reusable Gemini sub-workflows | — | Prints placeholder only; no Gemini invocation | O | Manual trigger |
| `gemini-invoke.yml` | aktiv | wcall | **Reusable:** Invoke Gemini AI on issue/PR | `commands/gemini-invoke.toml` | Issue/PR comment from Gemini | O | No internal caller in this repo |
| `gemini-review.yml` | aktiv | wcall | **Reusable:** Gemini AI code review | `commands/gemini-review.toml` | PR review comment | O | No internal caller in this repo |
| `gemini-triage.yml` | aktiv | wcall | **Reusable:** Gemini AI issue triage + labeling | `commands/gemini-triage.toml` | Issue labels + triage comment | O | No internal caller in this repo |
| `gemini-scheduled-triage.yml` | **parked** | dispatch (schedule removed) | Gemini scheduled triage — **PARKED fail-closed** | `commands/gemini-scheduled-triage.toml` | (Disabled) | — | Re-enable requires explicit decision |
| `emoji-filter.yml` | aktiv | push, sched, dispatch | Filter/enforce emoji usage rules in issues/PRs | `scripts/advanced-emoji-filter.py` | Filtered content / report | O | Config via `emoji-config.yaml` |
| `emoji-bot.yml` | aktiv | dispatch | Manual emoji bot operations | `scripts/advanced-emoji-filter.py` | Bot comment or action | O | Manual-only |
| `mcp_runtime.yml` | aktiv | dispatch, sched | MCP (Model Context Protocol) runtime management | — | MCP runtime state | O | Operator: MCP lifecycle |

---

## Group 4: Hygiene — 7 workflows

Repo health, staleness, documentation quality, and audit cleanliness.

| File | Status | Trigger(s) | Purpose | Scripts | Key Outputs | FP | HT |
|---|---|---|---|---|---|---|---|
| `stale.yml` | aktiv | sched, dispatch | Close stale issues/PRs after inactivity | — | Stale label + issue close | O | Stale list review |
| `docs-hub-guard.yml` | aktiv | push, dispatch, sched | Block tracked `*.log` files and `/logs/` paths from being committed | — | Fail if log committed | **C** | PR block; fix before merge |
| `docs-conflict-guard.yml` | aktiv | PR, push, dispatch | Detect documentation conflicts and drift | — | Conflict flag | O | On docs conflict detection |
| `root-session-hygiene-warning.yml` | aktiv | PR, dispatch | Warn on session-state artifacts in root | `scripts/root_session_hygiene_warn.py` | PR warning comment | O | PR review |
| `copilot-housekeeping.yml` | aktiv | sched, dispatch | Copilot workspace cleanup | — | Cleaned workspace state | O | Post-session cleanup |
| `branch-policy.yml` | aktiv | sched, dispatch | Enforce branch naming / protection policy | — | Policy report | O | On branch policy violation |
| `required-checks-audit.yml` | manual-only | dispatch | Audit required check configuration | — | Required checks report | O | On CI config changes |

**Note:** `docs-hub-guard.yml` is the only fail-closed workflow in this group (blocks tracked log files).

---

## Group 5: Reporting / Control Signals — 9 workflows

Digest, backlog/anomaly triage, post-merge scanning, and issue-signal creation.

> These are the **Gold-im-Keller** candidates from the #1633 audit. Core cockpit and feedback loops.

| File | Status | Trigger(s) | Purpose | Scripts | Key Outputs | FP | HT |
|---|---|---|---|---|---|---|---|
| `weekly_digest.yml` | aktiv | sched (weekly), dispatch | Post weekly digest comment on cockpit issue #1445 | — | Comment on #1445 | O | Weekly review in #1445 |
| `weekly_digest_failure_alert.yml` | aktiv | wrun (after weekly_digest) | Alert when weekly_digest fails | — | Failure alert comment | O | Investigate after failed digest |
| `cdb-backlog-curation.yml` | aktiv | issues:labeled | Bounded issue-scoped curation for implementation issues qualified via `task` or paired `type:*` + `scope:*` labels | `scripts/backlog_curation.py` | JSON artifact `artifacts/backlog-curation/issue-<number>.json` with typed handoff classes/read budgets/fingerprint + dedupe-safe receipt comment on the source issue | O | Review artifact + issue receipt when issue is implementation-relevant |
| `cdb-backlog-anomaly-escalation.yml` | aktiv | wrun (after cdb-backlog-curation), dispatch | Separate phase-1 lane: classify typed backlog-curation anomalies and emit only bounded dedupe-safe follow-up issues when strong and allowed | `scripts/backlog_anomaly_escalation.py` | Escalation artifact + optional bounded follow-up issue creation (max 0..1) | O | Review escalations when curation anomalies are strong |
| `cdb-daily-delta-triage.yml` | aktiv | sched (Tue/Wed/Fri/Sun 06:20 UTC), dispatch | Daily delta scoring: reads CONTROL_REGISTER.md, creates bounded issues | `scripts/daily_delta_triage.py` | Bounded issue creation (delta-scored) | O | Daily check in #1445 |
| `cdb-post-merge-followup-scanner.yml` | aktiv | PR:merged, dispatch | Scan merged PRs for follow-up actions | `scripts/post_merge_followup_scanner.py` + `prompts/cdb-control-followup.prompt.yml` | Follow-up issues/comments | O | Post-merge review |
| `cdb-weekly-control-hygiene-classifier.yml` | aktiv | sched (Mo/Do/Fr 07:30 UTC), dispatch | Weekly hygiene classification: creates hygiene issues | `scripts/weekly_control_hygiene_classifier.py` | Hygiene issues | O | Weekly review |
| `cdb-control-followup-classifier.yml` | manual-only | dispatch only | Classify pending control follow-up items | `scripts/run_cdb_control_followup.sh` → `prompts/cdb-control-followup.prompt.yml` | Issue comments / classifier output | O | Operator: manual classification runs |
| `triage_guard.yml` | aktiv | issues | Guard triage pipeline: fire on issue events, enforce triage structure | — | Triage issue or label | O | Issue triage review |

**Manifest-backed units (from #1644):**
- `cdb-control-followup-classifier` → `.github/control-plane/src/cdb-control-followup-classifier/`
- `cdb-post-merge-followup-scanner` → `.github/control-plane/src/cdb-post-merge-followup-scanner/`
- `cdb-daily-delta-triage` → `.github/control-plane/src/cdb-daily-delta-triage/`

**Shared prompt:** `cdb-control-followup.prompt.yml` consumed by both `cdb-control-followup-classifier.yml` AND `cdb-post-merge-followup-scanner.yml`.

---

## Group 6: Audit / Governance — 4 workflows

Policy gates, governance checks, AI routing, and smart insights.

| File | Status | Trigger(s) | Purpose | Scripts | Key Outputs | FP | HT |
|---|---|---|---|---|---|---|---|
| `policy-gate.yml` | aktiv | PR | Gate PR based on docs-only vs code-change classification | — | PR status check; `docs-only` or `code` path | **C** | Required check pattern; blocks merge |
| `governance-audit.yml` | manual-only | dispatch | Full governance audit: checks repo config, label compliance, runbook currency | — | Governance audit report | O | Operator: on governance review cycle |
| `ai-review-router.yml` | aktiv | sched, dispatch | Route AI review tasks to appropriate AI backend | — | AI review dispatch | O | On AI routing config changes |
| `smart-insights.yml` | aktiv | sched, dispatch | AI-driven insights generation: creates actionable issues | — | AI-generated insight issues | O | Review output issues |

**Gold-im-Keller:** `policy-gate.yml` is strong but possibly underdocumented. Its docs-only path classification can mis-classify `*.md` files under `infrastructure/` as docs-only.

---

## Group 7: Delivery / Gates — 3 workflows

Build publication and Copilot environment setup.

| File | Status | Trigger(s) | Purpose | Scripts | Key Outputs | FP | HT |
|---|---|---|---|---|---|---|---|
| `delivery-gate.yml` | aktiv | dispatch, sched | Gate delivery pipeline: checks readiness before release | — | Delivery gate pass/fail | O | Pre-release operator check |
| `docker-publish.yml` | aktiv | push, dispatch | Build and publish Docker images to registry | — | Docker image published to registry | O | On service changes; registry check |
| `copilot-setup-steps.yml` | aktiv | dispatch, push | Set up Copilot dev environment steps | — | Copilot workspace config | O | On Copilot config changes |

---

## Group 8: Security — 3 workflows

Secret scanning, vulnerability detection, and security audit.

| File | Status | Trigger(s) | Purpose | Scripts | Key Outputs | FP | HT |
|---|---|---|---|---|---|---|---|
| `gitleaks.yml` | aktiv | push, sched, dispatch | Scan for secrets and credentials in commits | — | Gitleaks report; fail on secrets found | **C** | Fix secrets before merge |
| `trivy.yml` | aktiv | push, sched, dispatch | Container/dependency vulnerability scan (Trivy) | — | Trivy vulnerability report | O | Review CVEs |
| `security-scan.yml` | aktiv | sched, push, dispatch | Combined security scan: gitleaks + ruff + bandit | — | Security scan report | O | Weekly security review |

---

## Group 9: Historisch / Unklar — 5 workflows

Legacy label and milestone automation. Not actively maintained; do not enable without scoped review.

> These 5 workflows have overlapping scope with the Reconcile group. Before activating any of them, review for collision with `sync-labels.yml`, `auto-milestone.yml`, and `control_board_auto_routing.yml`.

| File | Status | Trigger(s) | Purpose | Scripts | Key Outputs | FP | HT |
|---|---|---|---|---|---|---|---|
| `auto-label.yml` | parked | dispatch | **Deprecated (#1642)**: Keyword-matching label logic retired. Auto-trigger removed; dispatch-only stub prints deprecation notice. | — | Deprecation notice only | — | Auto-trigger removed in #1642; do not re-enable issues trigger without review |
| `bulk-issue-labeling.yml` | historisch | dispatch | Legacy: bulk-label issues manually | — | Bulk issue labels | — | Do not enable without review |
| `comprehensive-issue-labeling.yml` | parked | dispatch | **Deprecated (#1642)**: Comprehensive keyword-matching and stale issue-range labeling retired. Auto-trigger removed; dispatch-only stub prints deprecation notice. | — | Deprecation notice only | — | Auto-trigger removed in #1642; do not re-enable issues trigger without review |
| `issue-governance.yml` | parked | dispatch | **Deprecated (#1642)**: M1-M9 milestone mapping retired. Auto-trigger removed; dispatch-only stub prints deprecation notice. | — | Deprecation notice only | — | Auto-trigger removed in #1642; do not re-enable issues trigger without review |
| `milestone-assignment.yml` | historisch | dispatch | Legacy: manual milestone assignment | — | Milestone on issue | — | Do not enable without review |

---

## Non-workflow file in `/workflows/`

| File | Purpose | Consumer |
|---|---|---|
| `labels.json` | Canonical label definitions (machine-readable) | `sync-labels.yml`, `label-bootstrap.yml` |

> `labels.json` is **not** a workflow definition. It is a data file. The count of 67 workflows does not include it.

---

## Status summary

| Status | Count |
|---|---|
| aktiv | 56 |
| manual-only | 4 (`label-bootstrap`, `required-checks-audit`, `governance-audit`, `cdb-control-followup-classifier`) |
| parked | 4 (`gemini-scheduled-triage`, `issue-governance`, `auto-label`, `comprehensive-issue-labeling`) |
| historisch | 2 |
| frozen legacy | 1 (`ci.yaml`) |
| **Total** | **67** (aktiv 56 + manual 4 + parked 4 + historisch 2 + frozen 1 = 67... see note below) |

> **Count note:** `ci.yaml` is tracked separately as `frozen legacy`, not folded into the `historisch` bucket.
> Of the 56 active workflows, 3 (`gemini-invoke.yml`, `gemini-review.yml`, `gemini-triage.yml`) are `workflow_call` reusable units and are not independently triggerable.
> `parked` updated from 1→4 in #1642: `issue-governance.yml` (PR #1658), `auto-label.yml` and `comprehensive-issue-labeling.yml` (PR #1702).

| Status | Count |
|---|---|
| aktiv (independently triggered) | 53 |
| reusable (workflow_call only) | 3 (`gemini-invoke`, `gemini-review`, `gemini-triage`) |
| manual-only (dispatch-only) | 4 |
| parked | 4 |
| historisch / unklar | 2 |
| frozen legacy | 1 (`ci.yaml`) |
| **Total** | **67** |

> **Methodology note:** The current repo has 67 tracked workflow YAML files. `ci.yaml` is split out as `frozen legacy`; the three Gemini `workflow_call` units are active but non-standalone reusable workflows.

---

## Fail-closed workflows (blocks CI / merge)

| Workflow | Blocks what |
|---|---|
| `ci.yml` | Required check — blocks merge without explicit bypass |
| `docs-hub-guard.yml` | Blocks tracked log files from being committed |
| `policy-gate.yml` | Gates PR type classification; patterns downstream checks |
| `gitleaks.yml` | Fails on detected secrets |

---

## Gold-im-Keller candidates

From the #1633 audit — strong but potentially underdocumented:

1. **`cdb-post-merge-followup-scanner.yml`** — fires automatically on every PR merge, feeds cockpit #1445. High-leverage, low-visibility.
2. **`cdb-daily-delta-triage.yml`** cluster — 4×/week scheduling, bounded issue creation, reads `CONTROL_REGISTER.md` at runtime. Structural backbone of daily control loop.
3. **`weekly_digest.yml`** — primary cockpit signal. Core operator feedback.
4. **`policy-gate.yml`** — subtle but powerful docs-vs-code gate. Underdocumented edge case around `*.md` misclassification.
5. **`control_board_upsert.yml` + `project_reconcile_daily.yml`** — automated kanban backbone. Hidden complexity.

---

## Drift / orphan findings (#1640 pass)

- `ci.yaml` (frozen) and `ci.yml` (canonical) coexist. `ci.yaml` has never been cleaned up. Risk: accidental activation by future rename or copy.
- 5 historisch label/milestone workflows have overlapping scope with active Reconcile group. Collision risk if accidentally enabled.
- `gemini-scheduled-triage.yml` is parked (schedule removed) but not deleted. Should be explicitly annotated in the YAML with a `# PARKED` comment.
- `auto-milestone-pr-apply.yml` depends on `workflow_run` from an upstream workflow — the exact upstream workflow name should be verified against the current workflow name if `ci.yml` is ever renamed.
- `triage_guard.yml` triggers on all issue events; its scope overlap with `auto-milestone.yml` and `control_board_auto_routing.yml` is worth periodic review.
