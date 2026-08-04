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
| Manifest schema v1 (non-executable) | `docs/contracts/cdb_sensitivity_experiment_manifest.v1.schema.json` |
| Manifest schema v1.1 (executable) | `docs/contracts/cdb_sensitivity_experiment_manifest.v1.1.schema.json` |
| Canonical executable manifest | `config/arvp/sensitivity_campaign_4153_v1.json` |
| Grid / expansion SSOT code | `tools/arvp_vacation/sensitivity_campaign_grid.py` |
| Readiness schema | `docs/contracts/cdb_sensitivity_campaign_readiness.v1.schema.json` |
| Manifest library | `tools/arvp_vacation/sensitivity_experiment_manifest.py` |
| Preflight CLI | `python -m tools.arvp_vacation.sensitivity_campaign_preflight` |
| Fixtures | `tests/fixtures/arvp/sensitivity/` |

## Verdicts

- `READY_FOR_REPLAY_SENSITIVITY` — repository capability readiness (no concrete executable campaign)
- `READY_FOR_REPLAY_SENSITIVITY_CAMPAIGN` — concrete executable manifest passes full binding/expansion preflight (still **no** auto-start)
- `BLOCKED_EXPERIMENT_NOT_READY`
- `INVALID_EXPERIMENT_MANIFEST`
- `FROZEN_BOUNDARY_VIOLATION`
- `HOLDOUT_ACCESS_BLOCKED`

A PASS requires every mandatory gate to be positively evidenced. Missing,
stale, contradictory, or unverifiable evidence blocks.

## Executable campaign manifest (v1.1)

Owner Grid Ratification (`#4153` comment `5175526900`) binds:

- Correctness baseline SHA: `301bc757be7cb4162db6db114a5c445f2aca392f` (ancestor check; not a self-hash of the PR commit)
- Strategy: `primary_breakout_v1` only
- CDB-021: **OUT**
- Expansion mode: `BASELINE_PLUS_OFAT_WITH_BOUNDED_INTERACTIONS`
- Unique variants / window: **21**
- Runs: **819** (`expected_run_count = max_run_count = 819`)

`executable: true` does **not** start runs. `explicit_bans.campaign_execution_auto_start=true`
keeps preflight fail-closed against auto-execution. A separate Owner Campaign-GO
session is required before any of the 819 runs may execute.

## Expected current repository result

With Effective-Config snapshot capability delivered (`#4151`), the live-repo
preflight should return:

`READY_FOR_REPLAY_SENSITIVITY`

when every mandatory gate PASSes.

With the canonical executable manifest:

```text
python -m tools.arvp_vacation.sensitivity_campaign_preflight \
  --manifest config/arvp/sensitivity_campaign_4153_v1.json
```

→ `READY_FOR_REPLAY_SENSITIVITY_CAMPAIGN`

The synthetic v1 fixture remains non-executable and fails live fingerprint
binding when used as a campaign manifest.

## Allowed claims

- A machine-readable fail-closed readiness preflight exists.
- The experiment manifest contract is versioned and deterministically
  fingerprintable.
- Frozen boundaries and holdout access are technically blocked.
- Effective-Config snapshot capability is present and secret-safe (`#4151`).
- Repo preflight may reach `READY_FOR_REPLAY_SENSITIVITY` when all gates PASS.
- An Owner-ratified executable campaign manifest may reach
  `READY_FOR_REPLAY_SENSITIVITY_CAMPAIGN` without executing runs.

## Forbidden claims

- The sensitivity campaign has been executed.
- Parameters have been investigated.
- A candidate is promising or profitable.
- Stage-A has been passed.
- Replay evidence proves paper, live, or echtgeld readiness.
- Historical `#4151` window-parity / DQ / gap-OOO / rankability ACs are fully
  closed by Effective-Config alone.
- Manifest READY equals Campaign-GO or profitability evidence.

## Non-goals

- No sensitivity campaign runs
- No Stage-A survivor search from this contract alone
- No OOS / Stress / Stage-B data reads
- No Stage-A/B gate or risk/kill/live boundary changes
- No paper / runtime / live / echtgeld paths
- Closing `#4153` requires the full campaign acceptance criteria, not preflight alone

## Execution contract (follow-on)

Separate Owner-GO + runner contract: docs/strategy/CDB_SENSITIVITY_CAMPAIGN_EXECUTION_CONTRACT_V1.md.
CLI: python -m tools.arvp_vacation.sensitivity_campaign_runner plan|validate-authorization|execute.
Manifest READY ≠ Campaign-GO. Authorization schema: cdb.sensitivity_campaign_execution_authorization.v1.

## Related

- Parent: `#4147`
- Effective-Config capability: `#4151`
- Safety track (independent): `#4152`
- Correctness residuals closed via `#4336` / CDB-049..052
- Owner Grid Ratification: `#4153` comment `5175526900`
