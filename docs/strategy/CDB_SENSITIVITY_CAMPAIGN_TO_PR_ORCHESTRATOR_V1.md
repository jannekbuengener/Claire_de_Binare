# CDB Sensitivity Campaign-to-PR Orchestrator v1

Status: contract / fail-closed  
Issue: `#4366`  
Schema: `cdb.sensitivity_campaign_to_pr_orchestrator.v1`  
Parent closeout: `#4153` / `#4362`  
LR: `NO-GO` (unchanged)

## Purpose

Provide a **repo-local, fail-closed** path from a governed Stage-A sensitivity
campaign `COMPLETED` state (or an already-slim closeout package) to
**PR-safe prepared inputs**:

1. verify analysis / classification artifacts,
2. emit a **slim** evidence package (digests/cards only),
3. emit a **router-ready** batch PR body draft for `tools.pr_routing`.

This contract does **not** create GitHub branches/PRs, publish `cdb-local-ci`,
merge, promote strategies, or authorize Stage-B / OOS / Paper / Live / Echtgeld.

## Problem statement

| Fact | Implication |
| --- | --- |
| Campaign `COMPLETED` ≠ GitHub PR | Operator still packages evidence manually |
| Analyzer may already exist | Orchestrator must verify, not silently re-rank |
| Raw 819 run trees are huge / non-reviewable | Must never be staged as evidence substitute |
| `cdb-pr-router` is mandatory before PR create | Orchestrator stops at prepared inputs by default |

## Verdicts (exactly one)

| Verdict | Meaning |
| --- | --- |
| `ORCHESTRATOR_DRY_RUN_PASS` | Preconditions OK; no files written |
| `ORCHESTRATOR_PREPARE_PASS` | Slim package + PR body draft written |
| `HOLD_CAMPAIGN_PHASE_NOT_COMPLETED` | Envelope phase not `COMPLETED` and no slim closeout marker |
| `HOLD_CLASSIFICATION_MISSING` | `analysis/classification_report.json` missing |
| `HOLD_CLASSIFICATION_INVALID` | Classification not in allowed set |
| `HOLD_BINDING_MISMATCH` | Fingerprint / SHA args disagree with inventory |
| `HOLD_ANALYSIS_MISSING` | Required analysis artifacts missing |
| `HOLD_RAW_RUN_TREE_REJECT` | Candidate paths include raw `runs/` trees |
| `HOLD_FORBIDDEN_TOKEN` | Stage-B / Live / Echtgeld / promotion tokens in outputs |
| `HOLD_ABSOLUTE_PATH_LEAK` | Absolute local paths would be committed |

## Preconditions

Exactly one of:

1. **Full namespace:** `campaign_envelope.json` with `campaign_phase=COMPLETED`,
   plus inventory + analysis under the evidence root; **or**
2. **Slim closeout package:** `primary_evidence_inventory.json` +
   `analysis/classification_report.json` + `CLOSEOUT_CARD.md` (no `runs/`).

Always required:

- `classification` ∈ `{PROMISING, INCONCLUSIVE, REJECTED, BLOCKED}`
- `lr_status=NO-GO` on classification (or explicit `no_automatic_promotion=true`)
- Inventory digests present (`inventory_fingerprint`, `run_key_digest`)
- Optional binding pins (`--expected-*`) must match when supplied

## Slim package allowlist

Only these relative paths may be written into the output package:

- `CLOSEOUT_CARD.md`
- `primary_evidence_inventory.json` (absolute paths redacted to repo-relative)
- `analysis/classification_report.json`
- `analysis/analysis_envelope.json`
- `analysis/analysis_report.md`
- `analysis/campaign_input_inventory.json`
- `analysis/main_effects.json`
- `analysis/interaction_effects.json`
- `analysis/reproduction_summary.json`
- `orchestrator_report.json`
- `pr_body.md` (when `--prepare-pr-inputs`)

Anything under `runs/` is forbidden in the package.

## CLI

```text
python -m tools.arvp_vacation.sensitivity_campaign_to_pr dry-run \
  --evidence-root <path> [--expected-manifest-fp ...] [...]

python -m tools.arvp_vacation.sensitivity_campaign_to_pr prepare-pr-inputs \
  --evidence-root <path> --output-dir <path> \
  --issue 4366 [--batch-key validation-research] ...
```

Defaults:

- dry-run does not write files
- prepare-pr-inputs writes only the allowlist under `--output-dir`
- neither command calls `gh pr create` / branch create / merge

## Forbidden mixes

- commit raw primary/reproduction run trees
- Stage-B / OOS / Stress / Paper / Live / Echtgeld claims
- strategy promotion / LR Go
- auto-merge / `--admin` / `cdb-local-ci` publish from this slice
- mixing `#4347` work-start objective into this orchestrator PR

## Relation to prior contracts

- Adoption: `CDB_SENSITIVITY_CAMPAIGN_PRIMARY_EVIDENCE_ADOPTION_V1.md`
- Execution: `CDB_SENSITIVITY_CAMPAIGN_EXECUTION_CONTRACT_V1.md`
- Analyzer artifacts are inputs; this orchestrator does not replace analysis science
