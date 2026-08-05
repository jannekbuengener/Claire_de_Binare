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
| `sensitivity_campaign_authorization.py` | Owner-GO parse / verify + revoke marker + lifetime / per-attempt expiry checks |
| `sensitivity_campaign_runner.py` | `plan` / `validate-authorization` / `execute` / `probe-surface`; orchestrates primary + reproduction phases |
| `sensitivity_campaign_run_plan.py` | Deterministic 819-run expansion + fingerprint |
| `sensitivity_campaign_state.py` | Atomic evidence ledger + campaign phases + primary/reproduction resume + campaign lock |
| `sensitivity_campaign_budget.py` | Resource budget hard caps |
| `sensitivity_campaign_surface.py` | Read-only capability probe + bound dataset identity |
| `sensitivity_campaign_dataset_root.py` | Canonical dataset-root resolver (fail-closed) |
| `sensitivity_campaign_analyzer_contract.py` | 21 slots / 19 physical sets / 2 overlaps |
| `sensitivity_campaign_primary_adoption.py` | Primary evidence inventory + adopt transition (`PRIMARY_EVIDENCE_COMPLETE`) |
| `sensitivity_campaign_reproduction.py` | Executed double-run comparison contract (no new run keys) |
| `sensitivity_campaign_executor.py` | `FakeExecutor` / `StrategyReplayCampaignExecutor` (`attempt_kind: PRIMARY | REPRODUCTION`) |

Adoption SSOT: `docs/strategy/CDB_SENSITIVITY_CAMPAIGN_PRIMARY_EVIDENCE_ADOPTION_V1.md`

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

`expires_at_utc` must be an ISO-8601 timezone-aware timestamp for the
`execute` path (`AUTH_EXPIRES_AT_REQUIRED_FOR_CAMPAIGN` fail-closed on `null`).
Non-campaign contexts still accept `null`. Clock source:
`core.utils.clock.utcnow`. Expired GO → `AUTH_GO_EXPIRED` at load time.
Additionally:

- `assert_authorization_lifetime_covers_budget` is called once before any
  evidence writes; remaining lifetime must be
  `>= max_campaign_wall_time_seconds + max_run_wall_time_seconds`
  (`AUTH_LIFETIME_INSUFFICIENT_FOR_BUDGET` on failure).
- `assert_authorization_not_expired_for_next_attempt` is called before every
  primary, retry, and reproduction attempt so a long-running campaign cannot
  cross a live expiry mid-flight (`AUTHORIZATION_EXPIRED_BEFORE_NEXT_ATTEMPT`).

### Revocation sentinel

A comment body containing the case-sensitive marker
`REVOKED_CAMPAIGN_EXECUTION_CONTRACT_DEFECT` is refused before any JSON
parsing (`AUTH_GO_REVOKED`), even when a fenced payload is still present.
This is the primary mechanism to retire an issued Owner-GO without deleting
the historical comment.

Required bindings also include (non-exhaustive):

- `status = GO_REPLAY_SENSITIVITY_CAMPAIGN_READY`
- `lr_status = NO-GO`
- `bound_main_sha`, `manifest_fingerprint`, `run_plan_fingerprint`
- `execution_surface_id` + `surface_capability_fingerprint`
- `resource_budget` (all required fields; hard caps + logical relations enforced)

Fail-closed reason codes include author / issue / SHA / fingerprint / surface /
budget mismatches (`AUTH_*`, `BUDGET_*`, `SURFACE_*`).

## Execution flow

`execute_campaign` orchestrates the following phases atomically against the
campaign envelope (`campaign_phase` is transitioned via `update_campaign_phase`
with a fail-closed legal-transition table):

1. `PLANNED` / `PRIMARY_PLANNED` → `PRIMARY_RUNNING`
   - **or** governed adoption: `PLANNED` → `PRIMARY_EVIDENCE_COMPLETE` →
     `PRIMARY_COMPLETE` via `adopt-primary-evidence` when an audited primary
     ledger already exists (see adoption contract; no primary rewrite).
2. Run all primary keys (`attempt_kind = "PRIMARY"`, `reproduction_attempt=0`).
   Skipped when resuming from `PRIMARY_EVIDENCE_COMPLETE` / later phases.
3. `count_primary_succeeded` must equal `plan.run_count`; otherwise → `BLOCKED`
   with `PRIMARY_SUCCESS_COUNT_MISMATCH`.
4. `PRIMARY_RUNNING` → `PRIMARY_COMPLETE`.
5. If `reproduction_policy.enabled`: `PRIMARY_COMPLETE` → `REPRODUCTION_PLANNED`
   → `REPRODUCTION_RUNNING`.
6. For each reproduction item (`attempt_kind = "REPRODUCTION"`,
   `reproduction_attempt >= 1`, output under `runs/<run_key>/reproduction/<n>/`):
   inspect resume, run, commit, compare via `compare_reproduction_results`
   (bindings=True, exact-equality over `compared_result_fields`), write
   `comparison.json` evidence.
7. `on_mismatch = block_campaign_completion` (default) → any mismatch/failure
   transitions to `BLOCKED` with `REPRODUCTION_RESULT_MISMATCH` (or
   `REPRODUCTION_EXECUTION_FAILED`) and stops further attempts.
8. `REPRODUCTION_RUNNING` → `REPRODUCTION_COMPLETE` → `COMPLETED`.

Legal transitions:

- `PLANNED | PRIMARY_PLANNED → PRIMARY_RUNNING | BLOCKED`
- `PRIMARY_RUNNING → PRIMARY_COMPLETE | BLOCKED`
- `PRIMARY_COMPLETE → REPRODUCTION_PLANNED | COMPLETED | BLOCKED`
- `REPRODUCTION_PLANNED → REPRODUCTION_RUNNING | BLOCKED`
- `REPRODUCTION_RUNNING → REPRODUCTION_COMPLETE | BLOCKED`
- `REPRODUCTION_COMPLETE → COMPLETED | BLOCKED`
- `COMPLETED` and `BLOCKED` are terminal (idempotent self-transition only)

Under reproduction-enabled policy, the campaign **never** reports `COMPLETED`
after primary alone.

## Reproduction contract

- `build_reproduction_plan` is deterministic (`baseline[:n]` + evenly-spaced
  sample); it emits a `reproduction_plan_fingerprint` stored in the campaign
  envelope extra.
- Reproduction items reuse existing primary run keys; they do **not** add run
  keys and `max_run_count_unchanged = true`.
- `compare_reproduction_results` returns a structured comparison dict with
  `status ∈ {"PASS", "MISMATCH"}`, `reason_code`, `mismatched_fields`,
  `compared_fields`, `primary_result_fingerprint`,
  `reproduction_result_fingerprint`, `comparison_fingerprint`. On structural
  failure (empty `compared_fields`, forbidden volatile field, bindings
  mismatch) it raises `SensitivityReproductionError` fail-closed.
- Volatile fields (timestamps, host paths, attempt/process/log metadata,
  filesystem times) are **never** compared even when opted into.
- Bindings validated on the compare path when `bindings=True`:
  `run_key`, `manifest_fingerprint`, `run_plan_fingerprint`,
  `authorization_fingerprint`.

## Dataset root binding

`resolve_and_verify_dataset_root` is invoked on the `execute` path and its
identity is bound both into the surface probe and the campaign envelope
extra:

- Accepts either the `artifacts/market_data` parent or the full
  `window_bank/binance/spot/BTCUSDT/1m` bank path.
- Verifies **all** 39 manifest window bindings resolve under the resolved
  bank realpath and, when a `dataset_spec.json` is present, that its
  content fingerprint matches the manifest binding.
- Emits a `dataset_identity_fingerprint` derived from the sorted list of
  `(window_id, content_fingerprint)` pairs (path-independent identity).

Fail codes: `DATASET_ROOT_UNBOUND`, `DATASET_ROOT_MISSING`,
`DATASET_ROOT_NOT_ABSOLUTE`, `DATASET_SYMLINK_ESCAPE`, `DATASET_TRAVERSAL`,
`DATASET_WINDOW_MISSING`, `DATASET_CONTENT_FINGERPRINT_MISMATCH`,
`DATASET_MANIFEST_INVALID`. All are prefixed with `RUNNER_DATASET_` when the
runner surfaces them.

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
- Reproduction evidence under `runs/<run_key>/reproduction/<n>/` with
  `envelope.json`, `result.json`, `succeeded.marker`, and `comparison.json`

## Non-goals

- Creating an active Owner-GO in this contract delivery
- Paper / live / echtgeld / order paths
- Relaxing absolute bans via GO
- Publishing `cdb-local-ci` or merging PRs (orthogonal delivery flow)

## Test posture

Unit tests use `FakeExecutor`, injectable replay invokers, `tmp_path`, and
mocked comment fetchers. No live GitHub GO comments and no real campaigns in CI.
