# .github — Control Plane Entrypoint

**Repo:** Claire de Binare (`jannekbuengener/Claire_de_Binare`)
**Branch canon:** `github-meta-layer` → merged into `main`
**LR verdict:** NO-GO (see `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`)
**Board stage:** `trade-capable` (orthogonal to LR; no live capital)

---

## What is this folder?

`.github` is the **automation and governance control plane** of this repo.

It contains:
- CI/CD and quality gates
- Scheduled triage, digest, and reconciliation automation
- AI/agent-backed control workflows (Gemini, Claude, Copilot)
- GitHub Project board and label management
- Issue templates, PR templates, and governance config
- Scripts, prompts, and commands backing the workflows
- The manifest-driven collection layer (`control-plane/`)

Without understanding `.github`, the repo's automation is a black box.
This folder and its docs make it navigable.

---

## Folder layout

```
.github/
  workflows/         65 YAML workflow definitions + labels.json (66 files total)
  ISSUE_TEMPLATE/    10 issue form templates (yml + md)
  prompts/           1 active prompt: cdb-control-followup.prompt.yml
  scripts/           9 scripts backing operational workflows
  commands/          4 Gemini command stubs (toml)
  control-plane/     Manifest-driven collection layer (introduced #1644)
    README.md        Collection layer overview
    schema/          Manifest schema spec
    src/<unit>/      Per-unit manifests + notes
    test/<unit>/     Per-unit smoke scripts
    generated/       workflow-register.json (generated artifact)
  CODEOWNERS         @jannekbuengener owns all
  dependabot.yml     Automated dependency update config
  pull_request_template.md  PR checklist
  SECURITY.md        Security policy and disclosure
  LABELS.md          Label spec documentation (canonical: labels.json)
  MILESTONES.md      Milestone documentation
  emoji-config.yaml  Emoji filter/bot configuration
```

---

## Navigation guide

### When debugging a failing workflow
1. Start here → find the workflow in [`docs/runbooks/GITHUB_WORKFLOW_REGISTER.md`](../docs/runbooks/GITHUB_WORKFLOW_REGISTER.md)
2. Note its scripts, prompts, and required files
3. Check the runbook: [`docs/runbooks/GITHUB_CONTROL_PLANE_RUNBOOK.md`](../docs/runbooks/GITHUB_CONTROL_PLANE_RUNBOOK.md)
4. For manifested units (3 so far): check `control-plane/src/<unit>/NOTES.md`
5. Check Actions log → cross-reference the script output

### When changing a workflow
1. Read the full workflow file first
2. Check `docs/runbooks/GITHUB_CONTROL_PLANE_RUNBOOK.md` § "Before editing"
3. Check if the workflow has a manifest in `control-plane/src/` — if yes, update manifest too
4. Update `docs/runbooks/GITHUB_WORKFLOW_REGISTER.md` entry if the change affects documented fields
5. Run `python .github/scripts/control_plane_validate.py` if you touched a manifested unit

### When adding a new workflow
1. Add the YAML under `workflows/`
2. Add an entry to `docs/runbooks/GITHUB_WORKFLOW_REGISTER.md`
3. If it's a control-plane unit worth cataloging: add manifest + notes + smoke under `control-plane/src/<unit>/`
4. Run the validator

### When something is creating unexpected issues/comments
1. Check `CONTROL_REGISTER.md` → active infra workflows list
2. Check the register for workflows with `auto_issue_creation: true`
3. Key suspects: `cdb-daily-delta-triage.yml`, `cdb-weekly-control-hygiene-classifier.yml`, `cdb-backlog-anomaly-escalation.yml`, `smart-insights.yml`, `triage_guard.yml`

---

## Key reference surfaces

| Document | What it answers |
|---|---|
| [`docs/runbooks/GITHUB_CONTROL_PLANE_RUNBOOK.md`](../docs/runbooks/GITHUB_CONTROL_PLANE_RUNBOOK.md) | How to read, change, debug, and maintain workflows |
| [`docs/runbooks/GITHUB_WORKFLOW_REGISTER.md`](../docs/runbooks/GITHUB_WORKFLOW_REGISTER.md) | Full register: all 67 workflows, triggers, scripts, outputs |
| [`docs/runbooks/GITHUB_CONTROL_PLANE_GRAPH.md`](../docs/runbooks/GITHUB_CONTROL_PLANE_GRAPH.md) | Relationship matrix + Mermaid coupling graph |
| [`control-plane/README.md`](control-plane/README.md) | Manifest-driven collection layer docs |
| [`control-plane/generated/workflow-register.json`](control-plane/generated/workflow-register.json) | Machine-readable register (3 manifested units) |
| [`docs/runbooks/CONTROL_REGISTER.md`](../docs/runbooks/CONTROL_REGISTER.md) | Board stage, LR verdict, active infra workflow list |

---

## Workflow inventory at a glance

**Total:** 65 workflow definitions + 1 `labels.json` = 66 tracked files

| Group | Count | Key workflows |
|---|---|---|
| Reconcile (label/milestone/project) | 14 | sync-labels, project_reconcile_daily, control_board_upsert |
| CI / quality gates | 11 | ci.yml (canonical), contracts, lr021_replay_smoke |
| Spezialpfad (AI/agent/MCP/docker) | 9 | opencode, gemini-dispatch, docker-publish |
| Hygiene | 7 | stale, branch-policy, copilot-housekeeping |
| Audit/governance | 6 | policy-gate, governance-audit, required-checks-audit |
| Sonstiges | 5 | emoji-filter, emoji-bot, performance-monitor, smart-insights |
| Delivery/gates | 4 | delivery-gate, core-guard, triage_guard, docs-conflict-guard |
| Reporting | 6 | weekly_digest, cdb-daily-delta-triage, cdb-post-merge-followup-scanner, cdb-backlog-curation, cdb-backlog-anomaly-escalation |
| Security | 3 | gitleaks, trivy, security-scan |

**Status breakdown:**
- Aktiv: 54
- Manual-only: 4
- Fail-closed geparkt: 4
- Historisch: 2
- Frozen legacy: 1 (`ci.yaml`)

`cdb-backlog-curation.yml` is a bounded issue-scoped companion workflow for qualified `issues.labeled` events (`task` or paired `type:*` + `scope:*`). It uploads `artifacts/backlog-curation/issue-<number>.json` with typed handoff classes (`must_read`, `supporting`, `background`, `constraints`, `watchouts`, `implementation_targets`) and posts a dedupe-safe receipt comment on the source issue.
`cdb-backlog-anomaly-escalation.yml` is the separate phase-1 escalation lane. It consumes backlog-curation handoff artifacts, classifies typed anomalies fail-closed (`report_only` / `follow_up_issue` / `unclear`), blocks sensitive/private findings from public issue emission, and emits at most one dedupe-safe follow-up issue per run.

---

## Scripts at a glance

| Script | Backing workflow(s) |
|---|---|
| `scripts/daily_delta_triage.py` | `cdb-daily-delta-triage.yml` |
| `scripts/backlog_curation.py` | `cdb-backlog-curation.yml` |
| `scripts/backlog_anomaly_escalation.py` | `cdb-backlog-anomaly-escalation.yml` |
| `scripts/post_merge_followup_scanner.py` | `cdb-post-merge-followup-scanner.yml` |
| `scripts/weekly_control_hygiene_classifier.py` | `cdb-weekly-control-hygiene-classifier.yml` |
| `scripts/run_cdb_control_followup.sh` | `cdb-control-followup-classifier.yml` |
| `scripts/advanced-emoji-filter.py` | `emoji-filter.yml`, `emoji-bot.yml` |
| `scripts/root_session_hygiene_warn.py` | `root-session-hygiene-warning.yml` |
| `scripts/control_plane_validate.py` | `control-plane/test/*/smoke.sh`, `tests/test_control_plane.py` |

## Prompts at a glance

| Prompt | Consuming workflows |
|---|---|
| `prompts/cdb-control-followup.prompt.yml` | `cdb-control-followup-classifier.yml`, `cdb-post-merge-followup-scanner.yml` |

## Commands at a glance

| Command file | Backing workflow |
|---|---|
| `commands/gemini-invoke.toml` | `gemini-invoke.yml` (reusable) |
| `commands/gemini-review.toml` | `gemini-review.yml` (reusable) |
| `commands/gemini-scheduled-triage.toml` | `gemini-scheduled-triage.yml` (parked) |
| `commands/gemini-triage.toml` | `gemini-triage.yml` (reusable) |

---

## Issue templates as control-plane surface (in scope)

Issue templates are not decorative text files; they are part of the `.github` control plane because they define intake shape, governance expectations, and downstream label/state signals.

| Template family | Files | Role in control plane |
|---|---|---|
| Intake-first | `bug_report.yml`, `feature_request.yml` | Captures problem/request intake; may later be promoted to tracked work |
| Tracked-work | `task.yml`, `live-readiness.yml` | Implementation/gate-oriented intake with explicit closure + bookkeeping contract |
| Governance-heavy / meta | `standard.md`, `meta_cluster.md`, `meta_phase.md`, `meta_tracking.md`, `meta_governance.md` | Coordination/policy framing with merge-gated closure semantics and governance obligations |
| Template config | `config.yml` | Controls issue-template UX and contact links |

**Intake-only vs tracked/governance-heavy**
- Intake-only forms can remain discussion/intake artifacts.
- Tracked-work and governance-heavy forms explicitly define merge-gated closure and bookkeeping expectations.

**Relation to PR/merge closure semantics**
- Template text defines that issue closure is tied to merged target-branch reality.
- This is a governance contract for humans/reviewers; workflows do not currently parse template files directly at runtime.

**Relation to bookkeeping/governance expectations**
- Tracked templates carry checklist expectations (status sync, ledger hygiene, control-surface updates when relevant).
- These expectations align with `pull_request_template.md`, `docs/governance/GITHUB_CONTROL_PLANE_SEAL.md`, and the operational runbooks.

**Relation to workflows, root files, and governance surfaces**
- Issue-event workflows consume issue labels/state shaped at intake (routing, project sync, triage).
- Root governance files (`CODEOWNERS`, `pull_request_template.md`, `SECURITY.md`, labels/milestones docs) provide adjacent policy rails.
- Relationship model and boundaries: `docs/runbooks/GITHUB_CONTROL_PLANE_GRAPH.md` (§ `Workflow → Issue Template Relationships`).

## Root-file reference

| File | Purpose |
|---|---|
| `CODEOWNERS` | All paths owned by `@jannekbuengener` |
| `dependabot.yml` | Weekly dep updates: pip (all services), actions, docker; `.worktrees_backup` explicitly ignored |
| `pull_request_template.md` | PR checklist: scope, tests, governance, LR guardrails |
| `SECURITY.md` | Security policy and responsible disclosure process |
| `LABELS.md` | Label system documentation (human-readable); canonical machine form is `workflows/labels.json` |
| `MILESTONES.md` | Milestone structure documentation |
| `emoji-config.yaml` | Configuration for `emoji-filter.yml` and `emoji-bot.yml` |

---

## Collection layer (introduced #1644)

`control-plane/` holds the manifest-driven description layer above real `.github` assets.
- 3 units currently cataloged (Sprint 1): `cdb-control-followup-classifier`, `cdb-post-merge-followup-scanner`, `cdb-daily-delta-triage`
- Validator: `.github/scripts/control_plane_validate.py` — run `python .github/scripts/control_plane_validate.py --generate`
- CI: `tests/test_control_plane.py` — 11 tests, runs under standard `pytest`
- Generated register: `control-plane/generated/workflow-register.json`

See `control-plane/README.md` for full usage.

---

## Governance context

- **Live-Readiness:** NO-GO — `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
- **Board stage:** `trade-capable` — `docs/runbooks/CONTROL_REGISTER.md`
- **These are orthogonal systems.** Stage ≠ LR-GO. Never conflate them.
- **SSOT for `.github` doc canon:** this file + the four runbooks above
- **SSOT for operational workflow list:** `docs/runbooks/CONTROL_REGISTER.md` § Active Infra Workflows

---

## Governance Seal

`.github/` is a protected control-plane surface. A change here is **not complete** until its governance obligations are satisfied.

**Seal policy:** [`docs/governance/GITHUB_CONTROL_PLANE_SEAL.md`](../docs/governance/GITHUB_CONTROL_PLANE_SEAL.md)

**Quick check before merging a `.github/` PR:**

1. Which change class? (`doc-only` / `behavior-neutral` / `behavior-change` / `new-surface` / `removal` / `governance-only`)
2. Sync duties for that class satisfied? (seal doc § 3)
3. New or changed automation side effects declared in PR body?
4. PR template `.github` section checked?
5. Repo policy respected? Auto-merge is disabled repo-wide (`allow_auto_merge=false`), so do not use `gh pr merge --auto`.
6. Final human review completed before merge for control-plane/meta/governance/closure-sensitive work.
7. Closure semantics preserved? Merge state is not completion state; issue closure remains acceptance + merged-`main` based.

Typo fixes and harmless comment updates (`doc-only`) still require rules 1, 4, and 5.
