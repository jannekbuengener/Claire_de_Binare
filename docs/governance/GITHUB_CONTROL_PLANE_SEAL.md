# GitHub Control Plane Governance Seal

**Authority:** Canonical governance policy for `.github/` changes.
**Owner:** `@jannekbuengener` (CODEOWNERS)
**Introduced:** #1643
**Linked to:** `.github/README.md`, `docs/runbooks/GITHUB_CONTROL_PLANE_RUNBOOK.md`

---

## What this seal means

`.github/` is the repo's automation and governance control plane — not just another folder.
A `.github/` change is **not complete** until its governance obligations are satisfied.

The seal does not block harmless changes. It makes governance obligations explicit so that
drift is a deliberate decision, not an accident.

---

## 1. Protected Surface

These paths are in scope:

| Path | Contents |
|---|---|
| `.github/workflows/` | 65 workflow definitions + `labels.json` |
| `.github/ISSUE_TEMPLATE/` | 10 issue form templates |
| `.github/prompts/` | Prompt YAMLs backing operational workflows |
| `.github/scripts/` | Python/Shell scripts backing workflows |
| `.github/commands/` | TOML command stubs (Gemini family) |
| `.github/control-plane/` | Manifest-driven collection layer (introduced #1644) |
| `.github/CODEOWNERS` | Ownership declaration |
| `.github/pull_request_template.md` | PR checklist |
| `.github/SECURITY.md` | Security policy and responsible disclosure |
| `.github/LABELS.md` | Label spec documentation |
| `.github/MILESTONES.md` | Milestone documentation |
| `.github/emoji-config.yaml` | Configuration for emoji-filter/bot workflows |
| `.github/dependabot.yml` | Automated dependency update configuration |

**Note:** Changes to `docs/runbooks/GITHUB_*.md` by themselves are not in scope. But any
`.github/` change that makes those docs stale **does** require a sync per § 3.

---

## 2. Change Classes

Every `.github/` change belongs to exactly one class:

| Class | What it covers | Examples |
|---|---|---|
| `doc-only` | Comment, annotation, README update. No workflow/script logic change. | Add `# PARKED` comment; fix typo in `.github/README.md` |
| `behavior-neutral` | Rename, reformat, pin action SHA. Triggers, permissions, and outputs unchanged. | Pin action to SHA; normalize YAML indentation |
| `behavior-change` | Workflow trigger, permission, script logic, or job step change. Runtime output may differ. | Change `schedule:` cron; add `issues: write` permission; modify script logic |
| `new-surface` | Add a new workflow, script, prompt, command, template, or root file. | New `*.yml` workflow; new script under `scripts/` |
| `removal/deprecation` | Remove, park, or disable an existing workflow or file. | Delete workflow YAML; remove `issues:` auto-trigger (as in #1642) |
| `governance-only` | Changes to CODEOWNERS, PR template, SECURITY.md, LABELS.md, or this seal doc. | Update `SECURITY.md`; add PR checklist item |

If a single PR spans multiple classes, apply the **strictest** sync duties across all classes.

---

## 3. Sync Duties by Change Class

Sync surfaces that **must** be updated:

| Change Class | Required Sync |
|---|---|
| `doc-only` | None unless the change affects a documented register field |
| `behavior-neutral` | If rename/move: update register references + graph if coupling changed |
| `behavior-change` | `GITHUB_WORKFLOW_REGISTER.md` row (trigger/permission/output fields); side effects declared in PR |
| `new-surface` | New `GITHUB_WORKFLOW_REGISTER.md` entry; `GITHUB_CONTROL_PLANE_GRAPH.md` if new coupling; `.github/README.md` folder layout if new category added |
| `removal/deprecation` | Register status updated; graph coupling removed; `CONTROL_REGISTER.md` if was an active infra workflow |
| `governance-only` | This seal doc if policy changed; Runbook linked-docs section if reference added |

**Shared for all non-`doc-only` classes:**
- PR template `.github` section checked (see § 5 and `.github/pull_request_template.md`)
- Side effects declared in PR body if runtime behavior changes or new GitHub API mutations added

---

## 4. Merge-Readiness Rules

A `.github/` PR is merge-ready when **all** of the following are true:

1. **Change class identified** — one of the six classes in § 2
2. **Sync duties satisfied** — every required surface in § 3 is updated
3. **Side effects declared** — any new or changed automation output (issue creation, label mutation, project write, etc.) is stated in the PR body
4. **New files linked** — every new `.github/` file has an entry in the register or folder layout
5. **No silent drift** — no `.github/` file is left in an undocumented state after this PR
6. **Validator passes** — if any manifested unit (`control-plane/src/`) was touched, `python .github/scripts/control_plane_validate.py` passes
7. **PR checklist checked** — the `.github` section of `pull_request_template.md` is complete

**Exception for `doc-only`:** A pure typo fix or comment clarification that changes no documented
field satisfies merge-readiness by completing rules 1 and 7 only.

---

## 5. Review Depth

Solo-maintainer reality: self-review is always sufficient. The seal makes **what to review** explicit.

| Change Class | Review requirement | Gate |
|---|---|---|
| `doc-only` | Self-review | None beyond PR template |
| `behavior-neutral` | Self-review + confirm outputs unchanged | Verify no runtime delta (diff/grep) |
| `behavior-change` | Self-review + explicit "what changes at runtime" note in PR | Side effects must be declared |
| `new-surface` | Self-review + register entry required | No register entry = non-compliant |
| `removal/deprecation` | Self-review + downstream dependency check | Confirm no `workflow_run`/`workflow_call` depends on removed surface |
| `governance-only` | Self-review | None beyond PR template |

No fictional review roles. No multi-person approval theater.

---

## 6. Enforcement Mechanisms

Three lightweight, real enforcement paths:

### 6.1 PR Template Checklist (primary)

`.github/pull_request_template.md` contains a `.github` control-plane section. Every PR author
explicitly identifies the change class and confirms sync duties before merging.
This is the day-to-day gate.

### 6.2 Collection Layer Validator (secondary)

```bash
python .github/scripts/control_plane_validate.py
pytest tests/test_control_plane.py -v
```

Required whenever `.github/control-plane/` manifests are touched. 11 tests cover schema
validation, file existence, and field completeness for all manifested units.

### 6.3 Seal Document as Compliance SSOT (tertiary)

This document is the canonical reference for what "compliant" means. A `.github/` PR that
knowingly deviates from these rules must state the deviation and its rationale explicitly.
**Undocumented drift = non-compliant.**

---

## 7. Seal Preservation

What keeps this seal working over time:

| Mechanism | How it works |
|---|---|
| **CODEOWNERS** | `@jannekbuengener` owns all `.github/` paths; changes are always owner-gated |
| **PR template** | The `.github` section surfaces on every PR touching these paths |
| **Register discipline** | `GITHUB_WORKFLOW_REGISTER.md` is the canonical state; every workflow change requires a register sync |
| **Weekly hygiene signal** | `cdb-weekly-control-hygiene-classifier.yml` fires 2×/week; drift signals surface in #1445 |
| **Control-plane validator** | Manifested units stay verifiable via `control_plane_validate.py` + pytest |
| **This seal doc** | Defines non-compliance explicitly; stale seal = drift by definition |

---

## Reference

| Document | Role |
|---|---|
| `.github/README.md` | Canonical entrypoint; folder layout; navigation guide |
| `docs/runbooks/GITHUB_CONTROL_PLANE_RUNBOOK.md` | Technical operator guide; pre-edit checklist |
| `docs/runbooks/GITHUB_WORKFLOW_REGISTER.md` | Full 65-workflow register |
| `docs/runbooks/GITHUB_CONTROL_PLANE_GRAPH.md` | Relationship matrix + Mermaid graph |
| `.github/control-plane/README.md` | Collection layer (manifest/validator) usage |
| `docs/runbooks/CONTROL_REGISTER.md` | Board stage + LR verdict + active infra workflow list |
| `.github/pull_request_template.md` | PR gate; contains the `.github` checklist section |
