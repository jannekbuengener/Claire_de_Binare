## CI Exception Semantics
GREEN + EXCEPTION != Real E2E PASS.
Meaning: Pipeline passed with STUB/guardrails (missing secrets).
Action: Treat as warning requiring follow-up.
On protected/nightly: an Issue is auto-created.
Only GREEN without EXCEPTION = real E2E validated.

## Local Docker CI Phase 1

Canonical docs: [`ci/README.md`](../../ci/README.md).

- Local Docker CI wraps existing Make/Python/script commands and writes
  commit-bound evidence under `ci/artifacts/<run_id>/`.
- Local evidence is **not** a GitHub Required Check and must not be treated as
  merge authority.
- GitHub workflows and Branch Protection remain unchanged in Phase 1.
- `policy-gate` and CodeQL Security-tab coverage remain GitHub-native.
- Preferred Windows command: `pwsh -File ci/scripts/run_all.ps1`

## workflow_run Dependency Map

Audit date: `2026-03-03` (last full map review; re-verify on workflow `name:` renames)

`workflow_run` dependencies in this repo currently resolve cleanly against existing
workflow `name:` values. No string mismatches were found in the current tree.

| Upstream workflow name | Upstream file | Downstream workflow name | Downstream file | Status |
|-------|-------|-------|-------|-------|
| `Auto Milestone PR Intent` | `.github/workflows/auto-milestone-pr-intent.yml` | `Auto Milestone PR Apply` | `.github/workflows/auto-milestone-pr-apply.yml` | `OK` |
| `Weekly Project Digest` | `.github/workflows/weekly_digest.yml` | `Weekly Digest Failure Alert` | `.github/workflows/weekly_digest_failure_alert.yml` | `OK` |

## Governance Rule

`workflow_run.workflows` binds downstream automation to the upstream workflow
display name, not to the filename. That makes renames fragile by default.

Operational contract:

- Any rename of a workflow `name:` that is used as a `workflow_run` upstream must
  update the downstream `workflows: [...]` string in the same change set.
- Any new `workflow_run` edge must be added to this map so the dependency remains
  reviewable without scanning all workflow files.
- If a future audit finds a mismatch, the minimal fix is the exact string update in
  the downstream workflow only. No trigger refactor is required for this issue.

## Quick Verify: Workflow Name Drift

If you change any workflow `name:`, verify `workflow_run` bindings in the same PR.

```bash
rg -n "^name:" .github/workflows
rg -n "workflow_run" .github/workflows
rg -n "workflows:\\s*\\[" .github/workflows
```

Then confirm the documented map in this file still matches the repository state.
