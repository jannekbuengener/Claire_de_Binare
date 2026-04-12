# GitHub Control Plane Runbook

**Repo:** Claire de Binare
**Scope:** `.github/` — workflows, scripts, prompts, commands, templates, collection layer
**SSOT for stage/LR:** `docs/runbooks/CONTROL_REGISTER.md` + `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
**Canonical entrypoint:** `.github/README.md`

---

## 1. Control Plane Structure

The `.github` control plane has four functional layers:

```
Layer 1: Assets
  .github/workflows/*.yml      65 workflow definitions + labels.json
  .github/ISSUE_TEMPLATE/      10 issue form templates
  .github/pull_request_template.md
  .github/CODEOWNERS, dependabot.yml, SECURITY.md, LABELS.md, MILESTONES.md, emoji-config.yaml

Layer 2: Support files
  .github/scripts/             7 Python/Shell scripts (backing operational workflows)
  .github/prompts/             1 prompt YAML (shared: classifier + scanner)
  .github/commands/            4 Gemini TOML stubs (backing gemini-dispatch family)

Layer 3: Collection manifest (introduced #1644)
  .github/control-plane/src/<unit>/manifest.yaml + NOTES.md
  .github/control-plane/schema/manifest.schema.yaml
  .github/control-plane/test/<unit>/smoke.sh
  .github/control-plane/generated/workflow-register.json

Layer 4: Documentation (introduced #1640)
  .github/README.md            Canonical entrypoint
  docs/runbooks/GITHUB_CONTROL_PLANE_RUNBOOK.md  (this file)
  docs/runbooks/GITHUB_WORKFLOW_REGISTER.md
  docs/runbooks/GITHUB_CONTROL_PLANE_GRAPH.md
```

**Key separation rule:** Layers 1–2 are GitHub-functional. Layer 3 is descriptive. Layer 4 is navigational. Do not conflate them.

---

## 1a. Issue templates as control-plane surface

Issue templates under `.github/ISSUE_TEMPLATE/` are in-scope control-plane assets, not passive docs.

| Family | Files | Operational meaning |
|---|---|---|
| Intake-first | `bug_report.yml`, `feature_request.yml` | Initial intake surface; may remain intake-only |
| Tracked-work | `task.yml`, `live-readiness.yml` | Work contract surface with explicit closure/bookkeeping expectations |
| Governance-heavy / meta | `standard.md`, `meta_cluster.md`, `meta_phase.md`, `meta_tracking.md`, `meta_governance.md` | Coordination/policy framing for issue lifecycle and decision gates |
| Config | `config.yml` | Template UX and routing links |

**Runtime boundary (important):**
- Workflows do not currently read `.github/ISSUE_TEMPLATE/*` files directly.
- Template semantics therefore act as governance/intake contract first, runtime coupling second (via issue metadata and labels after issue creation).

**How templates connect to workflows and merge semantics:**
1. Templates shape labels/scope/state at intake.
2. Issue-event workflows consume that state for routing/label/project automation.
3. Merge-gated closure/bookkeeping expectations are enforced by human review and governance process, not by implicit workflow parsing.

Cross-reference:
- `docs/runbooks/GITHUB_CONTROL_PLANE_GRAPH.md` (`Workflow -> Issue Template Relationships`)
- `.github/README.md` (`Issue templates as control-plane surface (in scope)`)
- `docs/runbooks/GITHUB_WORKFLOW_REGISTER.md` (`#1640 minimum-field coverage model`)

---

## 2. How to Read a Workflow Safely

For every workflow you open, extract these fields in order:

### 2.1 Identity
- **File name** (signals group by naming convention: `cdb-*` = control, `auto-*` = reconcile, `gemini-*` = AI)
- **`name:` field** (human label)
- **`concurrency:` group** (critical: tells you if two runs compete or cancel-in-progress)

### 2.2 Trigger map
```yaml
on:
  push:              # auto, on code
  pull_request:      # auto, on PR events
  schedule:          # cron, check UTC offset
  workflow_dispatch: # manual or programmatic trigger
  workflow_run:      # downstream: depends on another named workflow
  workflow_call:     # reusable: must be called from another workflow
  issues:            # auto, on issue events
  pull_request_review_comment: # auto, on PR review comment
```

**Flag for attention:**
- `workflow_run` → the upstream workflow name is the real trigger
- `workflow_call` → this workflow is a library function; it has no standalone trigger
- `issues:` with `labeled:` → fires on every label operation — can cascade

### 2.3 Permissions block
Look for explicit `permissions:` at job or top level. Workflows without an explicit block inherit `GITHUB_TOKEN` defaults (which is write for most actions in `pull_request_target` context). Always check:
- `issues: write` — can create/close/label issues
- `pull-requests: write` — can comment/approve/label PRs
- `contents: write` — can push commits
- `id-token: write` — can mint OIDC tokens (Gemini/AI flows)

### 2.4 Outputs and side effects
Ask explicitly:
- Does it write to issues? (look for `gh issue create`, `gh issue comment`, `gh issue close`)
- Does it write to project boards? (look for `gh project item-add`, project mutations)
- Does it create labels? (look for `gh label create`)
- Does it run scripts? (look for `scripts/*.py`, `scripts/*.sh` calls)
- Does it produce artifacts? (`actions/upload-artifact`)
- Does it trigger downstream workflows? (`workflow_run` or `gh workflow run`)

### 2.5 Fail posture
- **Fail-closed:** workflow blocks the PR/merge path if it fails (e.g., `ci.yml`, `policy-gate.yml`)
- **Fail-open:** workflow is advisory; failure doesn't block (most scheduled workflows)
- **Parked:** workflow has no active trigger or is explicitly disabled

---

## 3. Before Editing a Workflow

Run through this checklist **before** modifying any `.github/workflows/*.yml`:

1. **Read the full workflow** — not just the step you want to change
2. **Check the workflow register** → `docs/runbooks/GITHUB_WORKFLOW_REGISTER.md`
3. **Check for a manifest** → `ls .github/control-plane/src/` — if unit exists, update manifest too
4. **Check for downstream consumers** — search for `workflow_run` referencing this workflow's name
5. **Check trigger overlap** — if adding `schedule:`, verify it doesn't collide with an existing cron
6. **Check permissions impact** — are you adding a permission that didn't exist?
7. **Check `concurrency:` group** — does your change affect run exclusion logic?
8. **Verify scripts if touched** — run `python .github/scripts/control_plane_validate.py` if manifested unit

### Safe changes
- Updating `timeout-minutes`
- Adjusting cron schedule (check UTC — server is UTC)
- Adding `workflow_dispatch` to a schedule-only workflow
- Adding a step inside a job that doesn't change permissions or outputs

### Changes requiring explicit care
- Modifying the trigger block (`on:`)
- Adding or changing `permissions:`
- Adding `issues: write` or `pull-requests: write` to any job
- Changing `concurrency:` group strings
- Adding `workflow_run:` as a trigger (very easy to create infinite chains)
- Modifying `sync-labels.yml` or `label-bootstrap.yml` — these touch all labels
- Modifying any `auto-milestone*` workflow — these can re-label hundreds of issues

### Changes that need a comment in the workflow file
- Disabling a step or job with `if: false`
- Parked workflows (add a `# PARKED` comment with date + reason)

---

## 4. Debugging Guide

### 4.1 A scheduled workflow silently stopped running
1. Check GitHub Actions → filter by workflow name → check last run timestamp
2. Check if GitHub auto-disabled it (inactive >60 days)
3. Check `concurrency:` — is a long-running previous run blocking it?
4. Check if it depends on an upstream `workflow_run` that is now disabled

### 4.2 A workflow is creating unexpected issues
Likely suspects (from #1633 audit):
- `cdb-daily-delta-triage.yml` — creates issues when delta score > threshold
- `cdb-weekly-control-hygiene-classifier.yml` — creates hygiene issues
- `smart-insights.yml` — AI-driven issue creation
- `triage_guard.yml` — creates issues on label events
Check issue labels for `control-delta`, `hygiene`, `triage` prefixes.
Cross-reference with `docs/runbooks/CONTROL_REGISTER.md` § Active Infra Workflows.

### 4.3 A label operation cascaded into many workflows
Label events (`issues: labeled`) trigger: `auto-milestone.yml`, `auto-milestone-label-dispatch.yml`, `control-board-routing-label-dispatch.yml`, `project_status_label_map.yml`, `project_status_sync.yml`. Any unexpected label on an issue can trigger all of these. Check the labeling source first.

### 4.4 `ci.yml` is failing
`ci.yml` is the canonical required check. Before diagnosing the failure, confirm it's `ci.yml` (not `ci.yaml` — the legacy frozen copy). Check:
- Python version (repo targets 3.12)
- `pytest -q -k "not test_mcp_time_server_runtime"` (CI exclusion)
- Ruff and Black (must pass on changed `.py` files)

### 4.5 Gemini workflows are not responding
`gemini-invoke.yml`, `gemini-review.yml`, `gemini-triage.yml` are reusable (`workflow_call`) — they are called by `gemini-dispatch.yml`. `gemini-scheduled-triage.yml` is **parked** (schedule removed, fail-closed). Check `gemini-dispatch.yml` first. The `commands/*.toml` files are command config stubs — they don't trigger independently.

### 4.6 A policy-gate check is blocking unexpectedly
`policy-gate.yml` classifies PRs as `docs-only` (no CI required) vs. `code` (full CI required). Its classification logic is in the YAML itself (`*.md` → docs-only). If a non-docs change is wrongly classified as docs-only, check the changed files list and the path matcher.

### 4.7 Claude / Copilot isn't responding to an issue or PR
- `claude.yml`: responds to `pull_request` + `issues` events (requires `@claude` or configured triggers)
- `claude-code-review.yml`: fires on `pull_request` events
- `opencode.yml`: fires on `pull_request_review_comment`
Check GitHub Actions permissions for the token — AI workflows require `id-token: write`.

---

## 5. Side Effects Catalog

Workflows that **mutate repo state** outside their own run:

| Workflow | Mutation type | Notes |
|---|---|---|
| `sync-labels.yml` | Creates/updates/deletes labels | Reads `labels.json` |
| `label-bootstrap.yml` | Creates labels | Manual-only |
| `auto-label.yml` | Labels issues | Historisch/unklar |
| `auto-milestone.yml` | Assigns milestones | Fires on issue labeled events |
| `auto-milestone-label-dispatch.yml` | Dispatches milestone label assignment | Issues trigger |
| `auto-milestone-pr-apply.yml` | Assigns milestone to PR | workflow_run downstream |
| `control_board_upsert.yml` | Creates/updates GitHub Project board items | Schedule + dispatch |
| `project_reconcile_daily.yml` | Reconciles project board state | Daily schedule |
| `project_status_label_map.yml` | Maps project status to labels | Issues trigger |
| `project_status_sync.yml` | Syncs project status columns | Issues trigger |
| `control_board_auto_routing.yml` | Routes to project board | Issues + PR trigger |
| `add_to_project.yml` | Adds items to project | Issues trigger |
| `cdb-daily-delta-triage.yml` | Creates issues (bounded) | Schedule 4×/week |
| `cdb-weekly-control-hygiene-classifier.yml` | Creates issues | Mo/Do/Fr 07:30 UTC |
| `cdb-post-merge-followup-scanner.yml` | Creates follow-up comments/issues | PR:merged |
| `cdb-control-followup-classifier.yml` | Creates issue comments | Manual-only |
| `smart-insights.yml` | Creates AI-driven issues | Schedule + dispatch |
| `weekly_digest.yml` | Posts issue comment on #1445 | Weekly schedule |
| `milestone_stage_label_sync.yml` | Syncs milestone stage labels | Issues trigger |
| `triage_guard.yml` | Creates triage issues | Issues trigger |
| `stale.yml` | Closes + labels stale issues | Schedule + dispatch |
| `docker-publish.yml` | Pushes Docker image to registry | push + dispatch |

---

## 6. SSOT and Scope Boundaries

### What is authoritative for what

| Question | Authoritative source |
|---|---|
| Is the repo live-trade-ready? | `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` |
| What is the current Board stage? | `docs/runbooks/CONTROL_REGISTER.md` |
| Which workflows are actively operational? | `docs/runbooks/CONTROL_REGISTER.md` § Active Infra Workflows |
| Complete workflow register (all 65)? | `docs/runbooks/GITHUB_WORKFLOW_REGISTER.md` |
| What does a workflow do in detail? | The workflow YAML itself + register entry |
| What scripts back a workflow? | `docs/runbooks/GITHUB_CONTROL_PLANE_GRAPH.md` |
| Which labels exist? | `.github/workflows/labels.json` (canonical); `.github/LABELS.md` (docs) |
| Which milestones exist? | `.github/MILESTONES.md` |
| Who owns all files? | `.github/CODEOWNERS` (`@jannekbuengener`) |

### Frozen/parked assets (do not activate without explicit review)
- `ci.yaml` — legacy copy of `ci.yml`, frozen. Do not activate or merge with `ci.yml`.
- `gemini-invoke.yml`, `gemini-review.yml`, `gemini-triage.yml` — reusable only, no standalone trigger.
- `gemini-scheduled-triage.yml` — parked fail-closed (schedule removed deliberately).
- `auto-label.yml`, `bulk-issue-labeling.yml`, `comprehensive-issue-labeling.yml`, `issue-governance.yml`, `milestone-assignment.yml` — historisch/unklar; do not enable without scoped review.

---

## 7. Solo-Maintainer Reality

This is a solo-maintained repo (`@jannekbuengener` owns everything via `CODEOWNERS`).

**Practical implications:**
- No escalation chain. One person = all approvals, all incident response.
- Runaway automation is a personal cost. Any workflow creating issues, labels, or comments affects the solo operator's inbox directly.
- Weekly cadence is the natural planning horizon. The `weekly_digest.yml` + cockpit issue `#1445` is the primary control surface.
- Prioritize workflows that **reduce** toil over workflows that merely report.
- Parked workflows should stay parked until there is an explicit solo-operator need.
- When in doubt: manual-dispatch > automatic. Observe one cycle before enabling schedules.

---

## 8. Validator and Collection Layer

### Running the validator
```bash
# Validate all manifested units (dry run)
python .github/scripts/control_plane_validate.py

# Validate and regenerate workflow-register.json
python .github/scripts/control_plane_validate.py --generate

# Run CI tests for the collection layer
pytest tests/test_control_plane.py -v
```

### What the validator checks
- All `manifest.yaml` files parse against the schema
- Required fields are present (`unit_id`, `display_name`, `primary_workflow`, `script_deps`, etc.)
- Referenced workflow files exist under `.github/workflows/`
- Referenced script files exist under `.github/scripts/`
- Smoke script files exist under `control-plane/test/<unit>/smoke.sh`

### Adding a new manifested unit
1. Copy an existing unit: `cp -r .github/control-plane/src/cdb-daily-delta-triage .github/control-plane/src/<new-unit>`
2. Edit `manifest.yaml` and `NOTES.md`
3. Create `control-plane/test/<new-unit>/smoke.sh`
4. Run `python .github/scripts/control_plane_validate.py --generate`
5. Verify `tests/test_control_plane.py` passes

---

## 9. Linked documentation

- `.github/README.md` — canonical entrypoint with folder layout
- `docs/runbooks/GITHUB_WORKFLOW_REGISTER.md` — full 65-workflow register
- `docs/runbooks/GITHUB_CONTROL_PLANE_GRAPH.md` — relationship matrix + Mermaid graph
- `.github/control-plane/README.md` — collection layer usage
- `docs/runbooks/CONTROL_REGISTER.md` — board stage + LR verdict + active infra list

---

## 10. Governance Seal Reference

The `.github` control plane is governed by a seal policy introduced in #1643.

**Full policy:** [`docs/governance/GITHUB_CONTROL_PLANE_SEAL.md`](../../docs/governance/GITHUB_CONTROL_PLANE_SEAL.md)

**Core rule:** every `.github/` change must satisfy the sync duties for its change class before merge.

**Six change classes:**
- `doc-only` — comment, annotation, README update; no sync required unless register field affected
- `behavior-neutral` — rename/reformat/pin; update register + graph if renamed
- `behavior-change` — trigger/permission/script change; update register row + declare side effects
- `new-surface` — new workflow/script/prompt/command/template; new register entry required
- `removal/deprecation` — remove or park; update register status + graph coupling
- `governance-only` — CODEOWNERS/PR template/SECURITY.md/seal doc; update seal if policy changes

**Enforcement:**
- PR template `.github` section — day-to-day gate on every PR
- `python .github/scripts/control_plane_validate.py` — required for any manifested-unit change
- Seal doc as compliance SSOT — undocumented drift = non-compliant
