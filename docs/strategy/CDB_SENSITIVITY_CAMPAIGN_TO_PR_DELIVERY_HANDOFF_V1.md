# CDB Sensitivity Campaign-to-PR Delivery Handoff v1

Status: contract / fail-closed  
Issue: `#4366` (slice 2 — post-foundation)  
Schema: `cdb.sensitivity_campaign_to_pr_delivery_handoff.v1`  
Depends on: `CDB_SENSITIVITY_CAMPAIGN_TO_PR_ORCHESTRATOR_V1.md`  
LR: `NO-GO` (unchanged)

## Purpose

Automate the **post-`COMPLETED` → PR_READY** transition as a **machine-readable
handoff**, without the orchestrator CLI calling `gh pr create` / merge /
`cdb-local-ci` publish.

| Actor | Responsibility |
| --- | --- |
| Campaign runner | After `campaign_phase=COMPLETED`, invoke orchestrator prepare-delivery |
| Orchestrator | Verify analysis + slim evidence; emit delivery package + handoff JSON |
| External agent / Control Plane | Run `cdb-pr-router`, create/update the routed PR/branch/commit |
| Orchestrator `verify-delivery` | Check observed commit/branch/PR-head/evidence against handoff → `PR_READY` |

## Pipeline

```text
COMPLETED
  → prepare-delivery (auto from runner)
  → analysis verified + slim package
  → delivery_handoff.json (HANDOFF_READY_FOR_EXTERNAL_PR_WRITE)
  → external agent writes GitHub (not this CLI)
  → verify-delivery(handoff, observed_facts.json)
  → PR_READY | HOLD_*
```

## Handoff document (required fields)

Written as `delivery_handoff.json` beside the slim package:

- `schema_version` = `cdb.sensitivity_campaign_to_pr_delivery_handoff.v1`
- `handoff_status` = `HANDOFF_READY_FOR_EXTERNAL_PR_WRITE`
- `handoff_fingerprint` (canonical hash of body without this field)
- `issue_number`
- `campaign_id`, `classification`, `inventory_fingerprint`, `run_key_digest`
- `slim_package` — relative paths + package fingerprint
- `pr_body_relpath` — `pr_body.md` inside the package
- `routing_hints` — batch_key / lane / validation_profile (hints only; live router wins)
- `forbidden_actions` — must include `gh_pr_create`, `gh_pr_merge`, `cdb_local_ci_publish`,
  `admin_merge`
- `expected_commit_paths` — allowlisted slim paths that must appear after agent write
- `verification_protocol` = `verify-delivery`
- `lr_status` = `NO-GO`

## Observed facts (agent-supplied; no `gh` inside orchestrator)

`verify-delivery` accepts an **observed facts** JSON produced by the external
agent from live `git`/`gh` (or equivalent). Required keys:

- `branch_name`
- `head_sha` (40-hex)
- `pr_number` (positive int)
- `pr_head_sha` (must equal `head_sha`)
- `pr_base` (must be `main` unless handoff allows otherwise)
- `commit_paths` (list of repo-relative paths in the delivery commit/diff)
- `slim_package_fingerprint` (must equal handoff package fingerprint)

Orchestrator **must not** shell out to `gh` / create PRs.

## Verdicts

| Verdict | Meaning |
| --- | --- |
| `HANDOFF_READY_FOR_EXTERNAL_PR_WRITE` | Package + handoff written; waiting on agent |
| `PR_READY` | Observed facts match handoff; delivery verified |
| `HOLD_HANDOFF_MISSING` | No handoff / invalid schema |
| `HOLD_OBSERVED_FACTS_INVALID` | Observed JSON incomplete/malformed |
| `HOLD_BRANCH_MISMATCH` | Branch empty or disagrees with handoff constraint |
| `HOLD_HEAD_PR_MISMATCH` | `head_sha` ≠ `pr_head_sha` |
| `HOLD_EVIDENCE_FINGERPRINT_MISMATCH` | Slim package fingerprint drift |
| `HOLD_COMMIT_PATHS_INCOMPLETE` | Required slim paths missing from commit |
| `HOLD_FORBIDDEN_PATH_IN_COMMIT` | `runs/` or other banned path present |
| `HOLD_ANALYSIS_UNVERIFIED` | Classification/analysis not verified before handoff |

## Runner wiring

After a successful transition to `COMPLETED`, the execute path **must** attempt
`prepare-delivery` into `<evidence_root>/campaign_to_pr/` (or configured output).

- Failure of prepare-delivery **does not** roll back `COMPLETED`.
- Execute payload includes `campaign_to_pr` with PASS handoff or HOLD reason.
- Opt-out: `--skip-campaign-to-pr-handoff` (explicit; default is wire-on).

## Hard bans

- No `gh pr create` / `gh pr merge` / `--admin` from orchestrator CLI
- No Stage-B / OOS / Stress / Paper / Live / Echtgeld / promotion
- No resurrecting a squash-deleted remote branch (anti-repush); agent opens a **new**
  branch name when required
- No raw `runs/` trees in the delivery package or verified commit paths
