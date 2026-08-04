# CDB Sensitivity Campaign Execution Contract v1

Status: contract / fail-closed  
Issue: `#4153`  
Schema: `cdb.sensitivity_campaign_execution_authorization.v1`  
LR: `NO-GO` (unchanged)

## Purpose

This contract defines how the `#4153` replay-only sensitivity campaign may be
**authorized** and **executed**. It does **not** authorize paper, live,
echtgeld, orders, exchange execution, auto-start, holdout/OOS/stress/Stage-B,
or promotion.

## Surfaces

| Module | Role |
| --- | --- |
| `sensitivity_campaign_authorization.py` | Owner-GO parse / verify |
| `sensitivity_campaign_runner.py` | `plan` / `validate-authorization` / `execute` / `probe-surface` |
| `sensitivity_campaign_run_plan.py` | Deterministic 819-run expansion + fingerprint |
| `sensitivity_campaign_state.py` | Atomic evidence ledger + resume + campaign lock |
| `sensitivity_campaign_budget.py` | Resource budget hard caps |
| `sensitivity_campaign_surface.py` | Read-only capability probe |
| `sensitivity_campaign_analyzer_contract.py` | 21 slots / 19 physical sets / 2 overlaps |
| `sensitivity_campaign_reproduction.py` | Double-run plan (no new run keys) |
| `sensitivity_campaign_executor.py` | `FakeExecutor` / `StrategyReplayCampaignExecutor` |

## Owner-GO

Authorization is a **machine-readable GitHub issue comment** on `#4153` with
exactly one fenced JSON block:

````text
```cdb.sensitivity_campaign_execution_authorization.v1
{ ... schema-valid payload ... }
```
````

JSON Schema:
`docs/contracts/cdb_sensitivity_campaign_execution_authorization.v1.schema.json`

### Atomic comment-id finalize flow

`github_comment_id` is self-referential. The only accepted creation procedure is:

1. Create a **non-authorizing** draft comment (`draft_owner_go_placeholder_body`).
2. Read the live GitHub comment id.
3. Build the full schema-valid payload including that exact `github_comment_id`.
4. Update the **same** comment body exactly once with the fenced payload.
5. Live-verify final body, `updated_at`, payload fingerprint, and comment id.
6. Only the final payload can authorize (`verify_owner_go_comment`).

Predicting ids, second comments, or authorizing before the final edit is forbidden.

### Mutability

- Body, author, issue membership (`issue_url`), and `updated_at` are loaded live.
- Resume binds `comment_updated_at` into the campaign envelope; a later edit
  yields `AUTH_COMMENT_MUTATED` / `RUNNER_AUTH_COMMENT_MUTATED`.
- Deleted comments fail closed (`AUTH_COMMENT_FETCH_FAILED`).

### Owner allowlist

`authorizing_github_login` must equal the **live** comment author **and** be an
exact member of `AUTHORIZING_OWNER_ALLOWLIST` (`jannekbuengener`). Payload
self-claims alone are insufficient. Non-ASCII / confusable logins are rejected.

### Required capability fields

`granted_capabilities` and `absolute_bans_unchanged` are **required** (schema +
verifier). Schema defaults are not applied. Exact values:

- `granted_capabilities = ["campaign_execution"]`
- `absolute_bans_unchanged = true`

### Expiry

`expires_at_utc` may be `null` or an ISO-8601 timezone-aware timestamp.
Clock source: `core.utils.clock.utcnow`. Expired GO → `AUTH_GO_EXPIRED`.

Required bindings also include (non-exhaustive):

- `status = GO_REPLAY_SENSITIVITY_CAMPAIGN_READY`
- `lr_status = NO-GO`
- `bound_main_sha`, `manifest_fingerprint`, `run_plan_fingerprint`
- `execution_surface_id` + `surface_capability_fingerprint`
- `resource_budget` (all required fields; hard caps + logical relations enforced)

Fail-closed reason codes include author / issue / SHA / fingerprint / surface /
budget mismatches (`AUTH_*`, `BUDGET_*`, `SURFACE_*`).

## Runner commands

```text
python -m tools.arvp_vacation.sensitivity_campaign_runner plan --manifest PATH
python -m tools.arvp_vacation.sensitivity_campaign_runner validate-authorization ...
python -m tools.arvp_vacation.sensitivity_campaign_runner execute ...
python -m tools.arvp_vacation.sensitivity_campaign_runner probe-surface ...
```

- `plan` and `validate-authorization` are **write-free** (no artifacts, no replays).
- `execute` requires a live-verified Owner-GO, matching surface + budget.
- Default executor: `StrategyReplayCampaignExecutor` (maps `RunEnvelope` →
  `ARVPReplayConfig` / `run_arvp_replay`, `dataset_source=binance_window`).
- There is **no** `--force` / `--yes` / `--admin` / `--resume-anyway` flag.
- `run_plan_fingerprint` is computed dynamically from the current repository SHA
  + manifest fingerprint (never hardcoded to a pre-merge main tip).

## Expansion invariants

- 39 development windows × 21 matrix slots = **819** run keys
- **21** matrix slots map to **19** physical parameter sets (**2** overlaps)
- Overlapping slots share ranking weight (`1 / n` per physical set)
- Reproduction double-runs reuse existing keys; they do **not** add run keys
- Evidence namespace:
  `artifacts/arvp_sensitivity/4153/{campaign_id}/{manifest_fp}/{authorization_id}`

## Non-goals

- Creating an active Owner-GO in this contract delivery
- Paper / live / echtgeld / order paths
- Relaxing absolute bans via GO
- Publishing `cdb-local-ci` or merging PRs (orthogonal delivery flow)

## Test posture

Unit tests use `FakeExecutor`, injectable replay invokers, `tmp_path`, and
mocked comment fetchers. No live GitHub GO comments and no real campaigns in CI.
