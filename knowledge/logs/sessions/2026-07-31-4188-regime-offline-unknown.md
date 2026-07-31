# Session 2026-07-31 — #4188 Offline/Assign UNKNOWN fail-closed

## Scope
Offline-/Assign-/Replay-Helfer: fehlende/unbekannte/Warmup-Regimes dürfen nicht stillschweigend als TREND (`regime_id=0`) erscheinen. Alignment mit Runtime + `DBBackedDatasetProvider` (#4149).

## Brain Evidence
- `brain_source`: repo-only
- `brain_status`: not-used
- `context_tool_status`: absent (nur cursor-cloud MCP)
- `repo_fallback_reason`: unavailable
- `context_trust_level`: none
- `records_found`: none

## Git / Routing
- Base: `origin/main` @ `e96f724c`
- Issue #4188 OPEN; #4149 CLOSED
- PR-Router: `CREATE_NEW_BATCH_PR` / lane `validation-research` / target_branch recommendation `batch/validation-research-issue-4188`
- Working branch (cloud template): `cloud-cursor/regime-offline-unknown-4188-5585`

## Fallback Inventory
| Path | Prior silent fallback | Fix |
| --- | --- | --- |
| `tools/market_data/assign_regime_offline.py` | warmup `=0`; `.get(..., 0)` | `resolve_assigned_regime` → `None` + block reason |
| `scripts/profitability/assign_regime_to_mexc_3091.py` | same | shared helpers |
| `scripts/profitability/assign_regime_calibrate_3032_expansion.py` | same | shared helpers |
| `scripts/profitability/generate_calibration_variants_3032.py` | same | shared helpers |

## Canonical UNKNOWN Semantics
Mirror `services/candles/service.py:_lookup_regime_id`:
- TREND→0, RANGE→1, HIGH_VOL_*→2, CRISIS→3
- UNKNOWN / missing / warmup → `regime_id=null` + `regime_name=UNKNOWN` + `regime_block_reason`

## Validation
- Targeted pytest: 12 new + 2 regression — PASS
- ruff check / black --check — PASS
- `git diff --check` — PASS
- Repo search: no remaining `REGIME_NAME_TO_ID.get(..., 0)` / `assigned_regime_id = 0` in reserved scope

## Non-goals / Boundaries
- No Full Fast-CI, no `cdb-local-ci`, no merge, no issue close
- No parameter tuning, no Stage/Risk/Live changes
- Forbidden paths untouched (`core/replay/dataset_provider.py`, `services/**`, CURRENT_STATUS, …)
- LR: NO-GO

## Status
`DONE_SLICE_ADDED_TO_BATCH_PR` (pending PR handoff)
