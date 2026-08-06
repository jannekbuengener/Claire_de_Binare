# hh_hl Campaign Execution-Preparation Evidence (#4374)

Status: PREPARATION COMPLETE — execution-capable, NOT execution-authorized.
Scope: Issue #4374 execution-preparation slice. No campaign execute, no Owner-GO
posting, no merge, no `cdb-local-ci`. LR = **NO-GO**.

## 1. Brain / Safety posture

- `brain_source=repo-only`, `brain_status=not-used` — no DB reads/writes.
- `execution_capable != execution_authorized`. All repo artifacts keep
  `campaign_execution_authorized=false` and `requires_external_owner_go=true`.
- No post-merge `main` SHA and no execution surface fingerprint are invented.
  The pre-finalization receipt binds the pre-merge base only.
- No change to risk/execution core or productive signal wiring. The
  ~1500-line `sensitivity_campaign_runner.py` was **not** copied; the lifecycle
  adapter composes the frozen #4153 state primitives.

## 2. Design-GO ratification (verified live upstream, re-derived here)

- `comment_id=5206657394`, `author=jannekbuengener`, `issue=4374`.
- `created_at=updated_at=2026-08-06T15:08:54Z` → not mutated.
- `status=GO_HH_HL_CAMPAIGN_DESIGN`,
  `bound_main_sha=7875651ba3c907a1e5cc815f974085e42a1807bc`.
- `source_manifest_fingerprint=ab095923a795445ff41d319b1b3941412c9429d38128a5edd2256f4a777afa80`
  (unchanged; source draft is immutable).
- **Design body fingerprint =
  `415400720d28c998dad6b311c71f9107395e3dd17528d4137d097918d682887d`**
  (canonical hash of the parsed Design-GO payload; matches
  `design_ratification.body_fingerprint` in the final manifest).
- Grid = 1 variant / slot `hh_hl_baseline_001`; dataset
  selection `3e9ed687…`, content `10f94c34…`.
- `does_not_authorize` includes campaign_execute, paper, live, echtgeld,
  promotion, stage_b, oos, stress. `lr_status=NO-GO`.

Reason codes for negative paths: `HOLD_DESIGN_GO_COMMENT_MUTATED`,
`HOLD_DESIGN_GO_AUTHOR_NOT_ALLOWLISTED`, `HOLD_DESIGN_GO_STATUS_INVALID`,
`HOLD_DESIGN_GO_BINDING_MISMATCH` (see module + tests).

## 3. Final manifest (frozen, execution-capable, not authorized)

- Path: `config/arvp/hh_hl_campaign_4374_v1.json`
  (`schema_version=cdb.hh_hl_campaign_manifest.v1`).
- **Manifest fingerprint =
  `1b1165b8b049099324cfc97c0858919f7f04fab985584cff54ad7161ecfcfc07`**
  — distinct from the immutable source draft `ab095923…`.
- `execution_mode=offline_replay_only`, `execution_enabled=true`,
  `campaign_execution_authorized=false`, `requires_external_owner_go=true`,
  `non_executable_without_owner_go=true`.
- `expected_window_count=39`, `expected_variant_count=1`,
  `expected_run_count=39`. Grid status `CAMPAIGN_GRID_OWNER_RATIFIED`.
- Contains `design_ratification`, `dataset_binding`, `output_contract`,
  `resume_policy`, `reproduction_policy`, `resource_budget_contract`,
  `absolute_bans`, `lr_status`. No local absolute paths; no execution-GO data
  (no `execution_sha`, no `surface_capability_fingerprint`, no `expires_at_utc`).

## 4. Execution-capable replay profile

- Path: `config/arvp/campaign_profiles/hh_hl_continuation_replay_v1.json`
  (`profile_id=hh_hl_continuation_replay_v1`, derived from
  `hh_hl_continuation_prep_v1`).
- `execution_enabled=true`, `planning_enabled=true`,
  `campaign_authorized=false`, `requires_external_owner_go=true`.
- `authorization_schema=cdb.hh_hl_campaign_execution_authorization.v1`,
  `executor_provider_id=hh_hl_single_run_replay_v1`,
  `evidence_namespace=artifacts/arvp_campaign/hh_hl_continuation/4374`.
- Same strategy/adapter/grid/dataset as prep; `absolute_bans` all off; NO-GO.
- `campaign_profile.py` registers `HH_HL_REPLAY_PROFILE_ID`, binds the replay
  strategy/adapter, keeps planning-enabled required, and refuses
  `campaign_authorized=true` in any repo profile.

## 5. Run plan + post-merge finalizer

- `hh_hl_campaign_run_plan.py` accepts both prep and replay profiles, binds the
  Design-GO receipt fields into the plan fingerprint body, and keeps
  `executable=false` without an `AuthorizationContext`.
- `build_hh_hl_final_run_plan(...)`:
  - `FINAL` requires a real post-merge `main` SHA distinct from the pre-merge
    base; otherwise `HOLD_POST_MERGE_MAIN_SHA_REQUIRED`.
  - `--pre-final` emits a `PRE_FINALIZATION` receipt that binds the pre-merge
    base and never claims a post-merge final fingerprint.
- Materialized pre-finalization receipt:
  `docs/evidence/arvp_hh_hl_prefinalization_run_plan_4374.json`
  (`status=PRE_FINALIZATION`, `executable=false`,
  `campaign_execution_authorized=false`, `execution_sha=null`,
  pre-final `run_plan_fingerprint=a6b3b635…`).

## 6. Execution authorization + AuthorizationContext

- `hh_hl_campaign_execution_authorization.py`:
  `schema_version=cdb.hh_hl_campaign_execution_authorization.v1`,
  `status=GO_HH_HL_CAMPAIGN_EXECUTION`, fence
  ```` ```cdb.hh_hl_campaign_execution_authorization.v1 ````.
- `verify_owner_execution_go_comment(...)` enforces: author allowlist,
  mutation check (`created_at==updated_at`), full binding match
  (manifest/run-plan/dataset/surface), finite **and** future expiry, and
  resource-budget coverage. It rejects the #4372 Implementation-GO, sensitivity
  GO, and any wrong schema/status (`HOLD_EXECUTION_GO_WRONG_GO_TYPE`).
- `AuthorizationContext` is a frozen dataclass constructible **only** via
  `authorization_context_from_verified_go(verified)`; a non-verified input
  raises `HOLD_EXECUTION_GO_CONTEXT_REQUIRES_VERIFIED_GO`.
- Schema: `docs/contracts/cdb_hh_hl_campaign_execution_authorization.v1.schema.json`.

## 7. Executor AuthorizationContext wiring

- `HhHlSingleRunReplayProvider` accepts the replay profile.
  `execute(envelope, authorization_context=None)`:
  - No `AuthorizationContext` → `HOLD_EXECUTION_OWNER_GO_REQUIRED`; the injected
    `single_run_callable` is never reached (profile/manifest flags alone are
    insufficient).
  - Valid `AuthorizationContext` → the injectable `single_run_callable`
    (default real single-run) is invoked; output is bound with the campaign
    bindings (`campaign_id`, manifest/run-plan/authorization fingerprints).
  - Refuses PB1/other strategy (`HH_HL_ENVELOPE_STRATEGY_MISMATCH`) and any
    `scenario_group_id` (`HH_HL_SCENARIO_GROUP_FORBIDDEN`).
- Prep profile still resolves to `PlanningOnlyExecutor`.

## 8. Lifecycle / state / resume adapter

- `hh_hl_campaign_lifecycle.py` reuses `CampaignBindings` and the resume state
  machine from `sensitivity_campaign_state` (no #4153 hardcodes; a dedicated
  `hh_hl_evidence_root_for` roots evidence at
  `artifacts/arvp_campaign/hh_hl_continuation/4374`).
- Validates exactly 39 unique primary run keys, mints `CampaignBindings` only
  from a verified `AuthorizationContext`, and plans resume actions
  (skip-identical / retry / start). Fails closed on `RUNNING` without a
  completion marker and on binding drift.

## 9. CLI (`tools/arvp_vacation/hh_hl_campaign_execution_prep.py`)

Write-free by default (materializes only with `--out`); never starts a replay.
Subcommands: `verify-design-go`, `build-final-manifest`, `finalize-plan`
(`--pre-final`), `prepare-execution-go`, `probe-surface`,
`negative-execute-probe`.

## 10. Validation

- `pytest tests/unit/arvp/test_hh_hl_campaign_execution_prep.py` → 24 passed.
- Full `tests/unit/arvp` (`-k "not physical and not live"`) → 519 passed,
  8 skipped, 14 deselected. #4153 regression green
  (`test_sensitivity_campaign_authorization`, `_grid`, `_runner`, `_state`,
  `_to_pr`, `_executor_budget`, `_reproduction`), hh_hl prep + dataset proof
  green.
- `ruff check` clean; `black --check` clean; `git diff --check` clean.

## 11. HOLDs left intentionally (require a separate, GO-gated session)

- `HOLD_POST_MERGE_MAIN_SHA_REQUIRED` — a real post-merge `main` SHA is needed
  for the `FINAL` plan and the Execution-GO package.
- `HOLD_EXECUTION_SURFACE_PROOF_REQUIRED` — a live surface-capability receipt
  is required to assemble the Execution-GO package.
- `HOLD_EXECUTION_OWNER_GO_REQUIRED` — no run without a verified live Owner
  `GO_HH_HL_CAMPAIGN_EXECUTION`.

## 12. Post-merge commands (run only in a separate GO-gated session)

```
# FINAL plan on the real post-merge main SHA
python -m tools.arvp_vacation.hh_hl_campaign_execution_prep finalize-plan \
  --planning-sha <POST_MERGE_MAIN_SHA>

# Assemble the Owner Execution-GO package (still authorized=false)
python -m tools.arvp_vacation.hh_hl_campaign_execution_prep prepare-execution-go \
  --planning-sha <POST_MERGE_MAIN_SHA> \
  --execution-sha <EXECUTION_MAIN_SHA> \
  --surface-receipt <SURFACE_RECEIPT_JSON> \
  --expires-at-utc <FUTURE_UTC_ISO8601>
```

Only after Jannek posts the resulting `GO_HH_HL_CAMPAIGN_EXECUTION` comment does
`verify_owner_execution_go_comment` mint an `AuthorizationContext` and unlock the
39-run single-run replay campaign. LR remains NO-GO throughout.

## 13. Materialized artifacts

- `config/arvp/hh_hl_campaign_4374_v1.json` (final manifest, authorized=false).
- `config/arvp/campaign_profiles/hh_hl_continuation_replay_v1.json`.
- `docs/contracts/cdb_hh_hl_campaign_manifest.v1.schema.json`,
  `docs/contracts/cdb_hh_hl_campaign_design_authorization.v1.schema.json`,
  `docs/contracts/cdb_hh_hl_campaign_execution_authorization.v1.schema.json`.
- `docs/evidence/arvp_hh_hl_design_go_ratification_receipt_4374.json`.
- `docs/evidence/arvp_hh_hl_prefinalization_run_plan_4374.json`.
