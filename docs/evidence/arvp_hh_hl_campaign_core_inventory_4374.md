# Campaign-Core Hardcode Inventory (#4374)

Architecture verdict: **PROFILE_DRIVEN_EXTENSION_SAFE**

| File / symbol | Value | Class | Note |
|---|---|---|---|
| `cdb_sensitivity_experiment_manifest.v1.1.schema.json` strategy/evidence consts | PB1 + `artifacts/arvp_sensitivity/4153` | LEGACY_4153_PROFILE | Must remain fixed |
| `sensitivity_campaign_grid.py` STRATEGY_ID/21/819 | PB1 matrix | LEGACY_4153_PROFILE | Untouched |
| `sensitivity_campaign_run_plan.py` campaign_id + 819 | `arvp-sensitivity-4153-v1` | LEGACY_4153_PROFILE | Untouched |
| `sensitivity_campaign_authorization.py` ISSUE/MANIFEST | 4153 | LEGACY_4153_PROFILE | Untouched |
| `StrategyReplayCampaignExecutor` | rejects non-PB1 | LEGACY_4153_PROFILE | Untouched; hh_hl uses separate provider |
| `sensitivity_campaign_state.py` evidence path | `.../4153/...` | LEGACY_4153_PROFILE | Untouched |
| Analyzer contract 21/19 | #4153 matrix | LEGACY_4153_PROFILE | Untouched |
| Batch-B scenario-group fail-closed (#4373) | refuse path | MUST_REMAIN_FIXED | Preserved |
| `campaign_profile.py` + schemas | instance bindings | GENERIC_CORE | New |
| `hh_hl_*` prep modules | planning-only | HH_HL_PROFILE_REQUIRED | New |

## Wiring Map

```text
legacy_4153_pb1 → existing sensitivity_* modules (unchanged)
hh_hl_continuation_prep_v1
  → hh_hl_campaign_grid (baseline-only draft)
  → hh_hl_campaign_dataset (selection bind + local proof HOLD)
  → hh_hl_campaign_manifest (non-executable draft)
  → hh_hl_campaign_run_plan (windows × variants)
  → hh_hl_campaign_reproduction / analyzer (plans only)
  → campaign_executor_providers.PlanningOnlyExecutor (execute refuse)
  → HhHlSingleRunReplayProvider (explicit; blocked without execution_enabled)
```
