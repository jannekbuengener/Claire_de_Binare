# CDB Sensitivity Campaign Primary Evidence Adoption v1

Status: contract / fail-closed  
Issue: `#4153`  
Schema: `cdb.sensitivity_campaign_primary_evidence_adoption.v1`  
LR: `NO-GO` (unchanged)

## Purpose

Authorize a **governed transition** from a pre-phase-machine Primary
execution (Hermes runner that emitted CLI `COMPLETED` after 819 primary
results without reproduction) into the post-`#4346` campaign phase machine
on `main`, **without** rewriting primary `result.json` artefacts and
**without** a full primary rerun when inventory proves set equality.

This contract does **not** authorize paper, live, echtgeld, Stage-B, OOS,
stress, promotion, ML/RL, or silent namespace mixing.

## Problem statement

| Fact | Implication |
| --- | --- |
| Old CLI `status=COMPLETED` | Means primary loop finished only |
| Envelope often stays `status=PLANNED` | Not campaign-phase `COMPLETED` |
| Post-`#4346` runner | Requires `PRIMARY_COMPLETE` before reproduction |
| No prior adoption schema | Silent resume would improvise governance |

Reclassification: old CLI `COMPLETED` → `PRIMARY_EVIDENCE_COMPLETE`
(inventory verdict). It must **never** be treated as
`CAMPAIGN_PHASE_COMPLETED`.

## Adoption verdicts (exactly one)

| Verdict | Meaning |
| --- | --- |
| `ADOPT_PRIMARY_EVIDENCE_WITH_EXPLICIT_TRANSITION_RECORD` | Inventory PASS; phase may enter `PRIMARY_EVIDENCE_COMPLETE` |
| `REPRODUCTION_MAY_RUN_AGAINST_EXISTING_PRIMARY_NAMESPACE` | After adopt + auth; same namespace, frozen bindings |
| `NEW_AUTHORIZATION_REQUIRED_FOR_REPRODUCTION` | Live Owner-GO cannot verify |
| `NEW_NAMESPACE_REQUIRED` | Binding collision / foreign evidence |
| `FULL_PRIMARY_RERUN_REQUIRED` | Only when set equality or bindings fail irrecoverably |
| `HOLD_ADOPTION_CONTRACT_MISSING` | Pre-contract HOLD (historical) |
| `HOLD_BINDING_DRIFT_UNRESOLVED` | Fingerprint / SHA mismatch |

## Required inventory fields

Written to `primary_evidence_inventory.json` under the evidence namespace:

- `schema_version` = `cdb.sensitivity_campaign_primary_evidence_adoption.v1`
- `adoption_verdict`
- `primary_verdict` (`PRIMARY_EVIDENCE_COMPLETE` or HOLD_*)
- `campaign_id`, `manifest_fingerprint`, `run_plan_fingerprint`,
  `authorization_fingerprint`
- `bound_execution_sha` / `bound_main_sha` (frozen primary bindings)
- `reproduction_code_sha` (git HEAD of the adopting tooling)
- `expected_run_count` / `observed_run_count`
- `run_key_digest` (SHA-256 over sorted run keys, newline-joined)
- `allowed_evidence_namespace` (path string)
- `forbidden_mixes` (explicit list)
- `power_off_recovery` (operator note; does not rewrite run ledger)
- `lr_status` = `NO-GO`

## Legal phase transitions (addition)

- `PLANNED` → `PRIMARY_EVIDENCE_COMPLETE` (via `adopt-primary-evidence` only)
- `PRIMARY_EVIDENCE_COMPLETE` → `PRIMARY_COMPLETE` (via adopt promote or
  `execute` entry before reproduction)
- `PRIMARY_EVIDENCE_COMPLETE` → `BLOCKED`

Normal path `PLANNED` → `PRIMARY_RUNNING` remains unchanged.

## Frozen bindings

Adoption and subsequent reproduction **must** use the frozen primary
`--main-sha` / execution SHA that produced the primary results. Using a
newer `origin/main` tip as `bound_main_sha` without a new Owner-GO and new
namespace is forbidden.

`reproduction_code_sha` may differ from `bound_execution_sha`; it records
which reproduction comparison code was used, without mutating primary
bindings.

## Resume / null Owner-GO expiry

Primary evidence produced under an Owner-GO with `expires_at_utc: null`
(pre-lifetime-harden path) may continue into reproduction on **resume**
when:

1. `primary_evidence_inventory.json` exists and verifies, and
2. live Owner-GO still verifies all non-lifetime bindings, and
3. campaign phase is `PRIMARY_EVIDENCE_COMPLETE` or later primary-complete
   phases.

This does **not** authorize fresh campaigns with null expiry.

## Forbidden mixes

- Rewriting or normalizing primary `result.json`
- Committing all 819 raw run trees as a substitute for digests
- Mixing foreign authorization namespaces
- Claiming campaign `COMPLETED` from primary-only CLI output
- Full primary rerun without a HOLD that proves adoption impossible

## Surfaces

| Module | Role |
| --- | --- |
| `sensitivity_campaign_primary_adoption.py` | Inventory + adopt CLI logic |
| `sensitivity_campaign_state.py` | `PRIMARY_EVIDENCE_COMPLETE` phase |
| `sensitivity_campaign_runner.py` | `adopt-primary-evidence` command; execute entry |
| This document | Governance SSOT for adoption |

## Absolute bans (unchanged)

Replay-only; 39 development windows; `primary_breakout_v1` only; no Stage-B /
OOS / stress / paper / live / echtgeld; LR remains `NO-GO`.
