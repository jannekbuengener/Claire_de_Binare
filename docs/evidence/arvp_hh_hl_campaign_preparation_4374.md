# hh_hl_continuation_v1 Campaign Preparation Evidence (#4374)

**Status:** preparation slice (planning-only)  
**Issue:** #4374  
**Lineage:** #4372 / PR #4373  
**Parent:** #1900  
**LR:** NO-GO · `campaign_authorized=false` · no Campaign Execute

## Architecture Verdict

`PROFILE_DRIVEN_EXTENSION_SAFE`

- Frozen #4153 stack remains untouched (`legacy_4153_pb1` profile binds identity only).
- New `cdb.campaign_profile.v1` sits beside the legacy chain.
- hh_hl uses `hh_hl_continuation_prep_v1` with `execution_enabled=false`.

## Dry-Plan (write-free)

Command:

```text
python -m tools.arvp_vacation.hh_hl_campaign_plan plan
```

Observed fields (planning session):

- `writes=false`, `replays=false`
- `campaign_execution_authorized=false`
- `strategy_id=hh_hl_continuation_v1`
- `variant_count=1`, `window_count=39`, `expected_run_count=39`
- `grid_status=HOLD_CAMPAIGN_GRID_OWNER_RATIFICATION_REQUIRED`
- `dataset_binding_status=HOLD_DATASET_BINDING_LOCAL_PROOF_REQUIRED`
- missing gates: `GO_HH_HL_CAMPAIGN_DESIGN`, `GO_HH_HL_CAMPAIGN_EXECUTION`

## Local dataset proof command

```text
python -m tools.arvp_vacation.hh_hl_campaign_plan prove-dataset --dataset-root <LOCAL_WINDOW_BANK_ROOT>
```

Do not invent content fingerprints from cloud.

## Owner-GO packages (copyable templates)

- `docs/contracts/examples/go_hh_hl_campaign_design.v1.template.json`
- `docs/contracts/examples/go_hh_hl_campaign_execution.v1.template.json`

Agents must not post Owner-GO in Jannek's name.

## Allowed claims

- Campaign-core is profile-bound for preparation.
- #4153 behavior remains regression-protected.
- hh_hl has a planning-only campaign profile.
- Manifest/run-plan are deterministically prepared (non-executable).
- Dataset binding is precisely locally blocked pending proof.
- Owner-GO packages are prepared.
- No campaign was executed.

## Forbidden claims

- Campaign ready without full dataset+grid binding
- Campaign authorized without Owner-GO
- Campaign started / Primary complete / Reproduction PASS
- Analyzer result from a real campaign
- Stage A passed / strategy profitable / promotable
- Paper/Live/Echtgeld clearance
- Merge candidate from targeted tests alone
