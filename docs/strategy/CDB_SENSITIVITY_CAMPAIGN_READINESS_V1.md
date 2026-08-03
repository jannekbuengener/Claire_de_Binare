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

With Effective-Config snapshot capability delivered (`#4151`), the live-repo
preflight should return:

`READY_FOR_REPLAY_SENSITIVITY`

when every mandatory gate PASSes (parameter-control, regime/signal anchors,
execution-economics, dataset provenance, effective-config, frozen boundaries,
holdout isolation).

Missing, incomplete, secret-bearing, or fingerprint-mismatched Effective-Config
evidence still fails closed as `BLOCKED_EXPERIMENT_NOT_READY`.

## Allowed claims

- A machine-readable fail-closed readiness preflight exists.
- The experiment manifest contract is versioned and deterministically
  fingerprintable.
- Frozen boundaries and holdout access are technically blocked.
- Effective-Config snapshot capability is present and secret-safe (`#4151`).
- Repo preflight may reach `READY_FOR_REPLAY_SENSITIVITY` when all gates PASS.

## Forbidden claims

- The sensitivity campaign has been executed.
- Parameters have been investigated.
- A candidate is promising or profitable.
- Stage-A has been passed.
- Replay evidence proves paper, live, or echtgeld readiness.
- Historical `#4151` window-parity / DQ / gap-OOO / rankability ACs are fully
  closed by Effective-Config alone.

## Non-goals

- No sensitivity campaign runs
- No parameter grids / Stage-A survivor search
- No OOS / Stress / Stage-B data reads
- No Stage-A/B gate or risk/kill/live boundary changes
- No paper / runtime / live / echtgeld paths
- Closing `#4153` requires the full campaign acceptance criteria, not preflight alone

## Related

- Parent: `#4147`
- Effective-Config capability: `#4151` (request/content FP + snapshot capability;
  residual DQ/window/rankability ACs stay on dedicated follow-ups)
- Safety track (independent): `#4152`
- Reused locks: Batch-A 39 development windows, Stage-A/B gate contracts,
  parameter-control register, execution-economics v1, dataset identity split
