# CI Stabilization Rollup

Timestamp (Europe/Berlin): `2026-02-19T20:29:18+01:00`  
Timestamp (UTC): `2026-02-19T19:29:18Z`  
Scope statement: `Docs/reports only — no workflows/settings/trading/docker changes in this PR.`

## Read-Only PR Status Snapshot (Merged vs Open)

| PR | Status | Branch | What changed (1-2 lines) | Evidence link | Merge commit SHA |
|---|---|---|---|---|---|
| [#868](https://github.com/jannekbuengener/Claire_de_Binare/pull/868) | OPEN | `ci/restore-green-trivy-reporting` | Trivy in `.github/workflows/ci.yaml` switched from hard-fail to reporting-only (`exit-code: "1"` -> `exit-code: "0"`), plus step summary note. | https://github.com/jannekbuengener/Claire_de_Binare/actions/runs/22194378747 | n/a (open) |
| [#869](https://github.com/jannekbuengener/Claire_de_Binare/pull/869) | OPEN | `ci/action-required-runbook` | Added docs runbook `docs/ci/ACTION_REQUIRED_RUNBOOK.md` for deterministic unblock of `action_required` + `jobs=[]` bot/app runs. | https://github.com/jannekbuengener/Claire_de_Binare/actions/runs/22192989773 ; https://github.com/jannekbuengener/Claire_de_Binare/actions/runs/22192989851 | n/a (open) |
| [#871](https://github.com/jannekbuengener/Claire_de_Binare/pull/871) | OPEN | `docs/log-actions-approval-mode1` | Added MODE 1 governance log entry with before/after evidence and explicit operational finding for 403 on `/actions/runs/{id}/approve` in non-fork context. | https://github.com/jannekbuengener/Claire_de_Binare/actions/runs/22192989773 ; https://github.com/jannekbuengener/Claire_de_Binare/actions/runs/22192989851 | n/a (open) |
| [#872](https://github.com/jannekbuengener/Claire_de_Binare/pull/872) | OPEN | `reports/ci-triage-restore-green` | Added read-only triage snapshot report `reports/CI_TRIAGE_RESTORE_GREEN.md` as RedStack evidence baseline for restore-green context. | https://github.com/jannekbuengener/Claire_de_Binare/blob/b12ea984607693ed81faf5b88b11e6f10e6b541a/reports/CI_TRIAGE_RESTORE_GREEN.md | n/a (open) |
| [#873](https://github.com/jannekbuengener/Claire_de_Binare/pull/873) | OPEN | `ci/sentinel-denoise` | Sentinel de-noise by removing recurring auto-runs and keeping manual dispatch path (`required-checks-audit` on-demand). | https://github.com/jannekbuengener/Claire_de_Binare/actions/runs/22195859100 | n/a (open) |

## Executive Summary

Main CI noise came from three deterministic sources: Trivy hard-fail on known CVE backlog in `CI/CD Pipeline`, `action_required` runs with `jobs=[]` on bot/app PRs, and permanently red Sentinel history.  
The stabilization set addressed this as a RedStack evidence chain: non-blocking Trivy reporting, explicit `action_required` runbook, MODE 1 governance decision log with before/after proof, triage snapshot baseline, and Sentinel de-noise.  
Current target state is a quieter and more deterministic signal model: required context stays stable, unblock path for gated runs is documented, and Sentinel no longer floods routine run history.  
MODE 1 (Strict Approval) is intentionally kept; no auto-run loosening was introduced in this rollup.

## Change Log (Chronological)

### PR #868 - Trivy reporting-only in CI/CD Pipeline

- PR: https://github.com/jannekbuengener/Claire_de_Binare/pull/868
- Branch: `ci/restore-green-trivy-reporting`
- Change: `.github/workflows/ci.yaml` updated so Trivy is reporting-only (`exit-code: "1"` -> `exit-code: "0"`), plus summary note that findings remain visible.
- Evidence: https://github.com/jannekbuengener/Claire_de_Binare/actions/runs/22194378747
- Merge commit: n/a (OPEN at snapshot time)

### PR #869 - action_required runbook

- PR: https://github.com/jannekbuengener/Claire_de_Binare/pull/869
- Branch: `ci/action-required-runbook`
- Change: Added `docs/ci/ACTION_REQUIRED_RUNBOOK.md` covering symptom detection (`action_required`, `jobs=[]`), deterministic maintainer unblock path, and MODE 1 vs MODE 2 governance options.
- Evidence anchors: https://github.com/jannekbuengener/Claire_de_Binare/actions/runs/22192989773 ; https://github.com/jannekbuengener/Claire_de_Binare/actions/runs/22192989851
- Merge commit: n/a (OPEN at snapshot time)

### PR #871 - MODE 1 governance log

- PR: https://github.com/jannekbuengener/Claire_de_Binare/pull/871
- Branch: `docs/log-actions-approval-mode1`
- Change: Logged MODE 1 (Strict Approval) decision in governance log with before/after evidence from rerun attempt 2 (success with jobs present).
- Operational finding: GitHub approve endpoint `/actions/runs/{id}/approve` returns `403` in this non-fork case; deterministic unblock remains maintainer rerun/approval path.
- Evidence: https://github.com/jannekbuengener/Claire_de_Binare/actions/runs/22192989773 ; https://github.com/jannekbuengener/Claire_de_Binare/actions/runs/22192989851
- Merge commit: n/a (OPEN at snapshot time)

### PR #872 - CI triage snapshot report

- PR: https://github.com/jannekbuengener/Claire_de_Binare/pull/872
- Branch: `reports/ci-triage-restore-green`
- Change: Added read-only triage baseline report `reports/CI_TRIAGE_RESTORE_GREEN.md` to preserve restore-green context and root-cause classification as audit evidence.
- Evidence (PR artifact): https://github.com/jannekbuengener/Claire_de_Binare/blob/b12ea984607693ed81faf5b88b11e6f10e6b541a/reports/CI_TRIAGE_RESTORE_GREEN.md
- Merge commit: n/a (OPEN at snapshot time)

### PR #873 - Sentinel de-noise

- PR: https://github.com/jannekbuengener/Claire_de_Binare/pull/873
- Branch: `ci/sentinel-denoise`
- Change: `required-checks-audit` de-noised by decommissioning recurring auto-runs while preserving manual dispatch availability.
- Evidence (manual green): https://github.com/jannekbuengener/Claire_de_Binare/actions/runs/22195859100
- Representative historical failing runs: https://github.com/jannekbuengener/Claire_de_Binare/actions/runs/22075752655 ; https://github.com/jannekbuengener/Claire_de_Binare/actions/runs/22075680307
- Merge commit: n/a (OPEN at snapshot time)

## Operational Guidance

- If `action_required` + `jobs=[]`: runbook reference https://github.com/jannekbuengener/Claire_de_Binare/pull/869 and deterministic maintainer rerun/approval path from evidence anchors https://github.com/jannekbuengener/Claire_de_Binare/actions/runs/22192989773 and https://github.com/jannekbuengener/Claire_de_Binare/actions/runs/22192989851.
- MODE 1 is intentionally retained (no auto-run loosening): governance decision log reference https://github.com/jannekbuengener/Claire_de_Binare/pull/871.

## Post-Merge Verification Checklist

- [ ] After merge of `#868`, `CI/CD Pipeline` on `main` is green.
- [ ] Required context `ci (Unit/Integration + Lint gesammelt)` is still emitted unchanged.
- [ ] Sentinel does not auto-run on routine events; manual `workflow_dispatch` remains available.

## Rollback / Revert Strategy

- Each PR in this stabilization set is independently revertable.
- No coupled changes are required across PR boundaries.
