# CDB Sensitivity Campaign Readiness Contract v1

Status: Canonical readiness / manifest contract for Issue `#4153`
Scope: Replay-only sensitivity **preflight + experiment manifest** (no campaign runs)
LR: `NO-GO` — orthogonal to Board stage `trade-capable`

## Purpose

Provide a machine-readable, fail-closed readiness gate and a versioned,
deterministically fingerprintable experiment manifest contract so a later
replay-only sensitivity campaign cannot start improvisationally.

## Surfaces

| Artifact | Path |
|---|---|
| Manifest schema | `docs/contracts/cdb_sensitivity_experiment_manifest.v1.schema.json` |
| Readiness schema | `docs/contracts/cdb_sensitivity_campaign_readiness.v1.schema.json` |
| Manifest library | `tools/arvp_vacation/sensitivity_experiment_manifest.py` |
| Preflight CLI | `python -m tools.arvp_vacation.sensitivity_campaign_preflight` |
| Fixtures | `tests/fixtures/arvp/sensitivity/` |

## Verdicts

- `READY_FOR_REPLAY_SENSITIVITY`
- `BLOCKED_EXPERIMENT_NOT_READY`
- `INVALID_EXPERIMENT_MANIFEST`
- `FROZEN_BOUNDARY_VIOLATION`
- `HOLDOUT_ACCESS_BLOCKED`

A PASS requires every mandatory gate to be positively evidenced. Missing,
stale, contradictory, or unverifiable evidence blocks.

## Expected current repository result

Because Issue `#4151` has not delivered a full Effective-Config snapshot
capability (PR `#4243` only separated request vs content fingerprints), the
live-repo preflight must return:

`BLOCKED_EXPERIMENT_NOT_READY`

This is the correct fail-closed result, not a preflight defect.

## Allowed claims

- A machine-readable fail-closed readiness preflight exists.
- The experiment manifest contract is versioned and deterministically
  fingerprintable.
- Frozen boundaries and holdout access are technically blocked.
- The current repository is correctly classified as
  `BLOCKED_EXPERIMENT_NOT_READY` while Effective-Config evidence is missing.

## Forbidden claims

- `#4151` is complete.
- The campaign is execution-ready.
- Parameters have been investigated.
- A candidate is promising or profitable.
- Stage-A has been passed.
- Replay evidence proves paper, live, or echtgeld readiness.

## Non-goals

- No sensitivity campaign runs
- No parameter grids / Stage-A survivor search
- No Effective-Config snapshot implementation (`#4151`)
- No OOS / Stress / Stage-B data reads
- No Stage-A/B gate or risk/kill/live boundary changes
- No paper / runtime / live / echtgeld paths
- No merge and no issue close for `#4153` from this slice alone

## Related

- Parent: `#4147`
- Blockers remaining for campaign start: `#4151` (Effective-Config)
- Safety track (independent): `#4152`
- Reused locks: Batch-A 39 development windows, Stage-A/B gate contracts,
  parameter-control register, execution-economics v1, dataset identity split
