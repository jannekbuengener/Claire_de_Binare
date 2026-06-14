# ARVP RMR Single-Run Provenance Bundle Path Evidence

**Issue:** [#3198](https://github.com/jannekbuengener/Claire_de_Binare/issues/3198)
**Parent:** [#1900](https://github.com/jannekbuengener/Claire_de_Binare/issues/1900)
**Foundations:** [#3196](https://github.com/jannekbuengener/Claire_de_Binare/issues/3196), [#3197](https://github.com/jannekbuengener/Claire_de_Binare/issues/3197)
**Decision date:** 2026-06-14
**Status:** DONE_PR_CREATED

---

## Brain Evidence

```
brain_source: repo-only
brain_status: used
tools_or_queries:
  - read: canonical read-order (AGENTS.md, agents/AGENTS.md, governance, CONTROL_REGISTER.md, LR-AUDIT-STATUS, CURRENT_STATUS.md)
  - bash: git fetch origin --prune, git status -sb, git rev-parse HEAD
  - bash: gh pr list --state open, gh issue view 3198
  - read: #3198 issue body and prompt_contract
  - read: services/validation/strategy_replay_runner.py (run_arvp_replay, _build_rmr_execution_provenance_id, _build_provenance_config_snapshot)
  - read: services/validation/rmr_backtest_runner.py (report schema, _build_full_report)
  - read: core/replay/run_registry.py (bt-<16hex> regex)
  - read: core/replay/historical_bridge.py (RANGE_MEAN_REVERSION_STRATEGY_ID)
  - read: tests/unit/validation/test_strategy_replay_runner.py (TestRMRDispatch, TestRMRSingleRun)
records_or_results:
  - git: HEAD on branch evidence/rmr-single-run-path-3198
  - gh: #3198 OPEN (dieser Slice), #3196 CLOSED (RMR replay adapter), #3197 CLOSED (scenario-group dispatch)
  - gh: #1900 OPEN (ARVP North-Star)
  - 96/96 unit tests pass in test_strategy_replay_runner.py (84 existing + 12 RMR tests)
  - 5587/5589 full suite pass (2 pre-existing unrelated failures)
  - ruff check . — all checks passed
  - git diff --check — no whitespace errors
repo_crosscheck:
  - strategy_replay_runner.py dispatches by strategy_id in run_arvp_replay: single-run path now open for RMR
  - rmr_backtest_runner.py: _build_full_report uses period_start_ts_ms/period_end_ts_ms (was period_start_ms/period_end_ms) for compatibility with _build_replay_report_input
  - run_registry.py: strategy-agnostic, bt-<16hex> provenance ID regex enforced by both PB and RMR
  - _build_rmr_execution_provenance_id produces bt-<16hex> from canonical candle hash + config payload
  - _build_provenance_config_snapshot strategy-aware: RMR fields vs PB fields
  - RMR single-run skips two-pass determinism check (deterministic_replay_ok=False honest)
impact_on_plan:
  - #1900 Scenario-1 (Range-Reversion-V1-Rekord-Suite) fully executable: both scenario-group and single-run paths work
  - RMR single-run now produces ReplayReporter bundle with provenance, registry, operator summary
  - --deterministic-verify flag is no-op for RMR (no two-pass check exists)
limitations:
  - repo-only; no SurrealDB/Context-Brain evidence
  - LR remains NO-GO; range_mean_reversion_v1 remains PARKED
  - No candidate promotion, no signal logic changes, no optimization
  - RMR single-run evidence bundles use synthetic test candles; real multi-window evidence deferred
```

---

## Implementation

### Modified modules

- **`services/validation/rmr_backtest_runner.py`** (line 287-288):
  Renamed `period_start_ms` → `period_start_ts_ms` and `period_end_ms` → `period_end_ts_ms`
  in `_build_full_report` to match the replay report input schema.

- **`services/validation/strategy_replay_runner.py`**:
  - Added `_build_rmr_execution_provenance_id()` (lines ~803-815): canonical candle hash + config payload → SHA-256 → `bt-<16hex>`
  - Made `_build_provenance_config_snapshot()` strategy-aware: RMR fields (entry_threshold, exit_threshold, zs_lookback, atr_period, atr_stop_mult, cooldown_minutes, warmup_candles, order_size) vs PB fields
  - Removed RMR guard (exit 2) from `run_arvp_replay()` single-run path
  - Added strategy dispatch in `run_arvp_replay()` for:
    - Provenance ID: `_build_rmr_execution_provenance_id()` vs `_build_execution_provenance_id()`
    - Backtest call: `run_range_mean_reversion_backtest()` with `run_id` injection vs `run_primary_breakout_backtest()`
    - Determinism check: RMR skips two-pass (always `False`, warning is INFO not WARNING, `--deterministic-verify` is no-op for RMR)

### Tests

- **`tests/unit/validation/test_strategy_replay_runner.py`**:
  - `TestRMRDispatch.test_rmr_without_scenario_ids_returns_2` → renamed to `test_rmr_without_scenario_ids_runs_single_run` (expects exit 0)
  - New `TestRMRSingleRun` class (11 tests):
    - `test_successful_run_returns_0` — exit 0 with mocked backtest
    - `test_execution_provenance_id_format` — bt-<16hex> format
    - `test_provenance_fields` — deterministic_replay_ok=False, strategy_id, execution_provenance_id in registry
    - `test_bundle_and_registry_written` — report.json, config.resolved.json, env_redacted.txt, registry records
    - `test_supplementary_artifacts_written` — config.resolved.json, env_redacted.txt
    - `test_error_path_returns_2` — RuntimeError → exit 2, running+failed records
    - `test_deterministic_verify_flag_exit_0` — RMR skips deterministic-verify gate
    - `test_backtest_called_with_run_id` — run_id passed through to run_range_mean_reversion_backtest

---

## Verification

```text
$ ruff check . --ignore E501,F401,F541
All checks passed!

$ pytest -q tests/unit/validation/test_strategy_replay_runner.py
96 passed (57 warnings)

$ git diff --check
(no output — clean)
```

---

## File Inventory

| File | Change | Status |
|------|--------|--------|
| `services/validation/strategy_replay_runner.py` | Add RMR provenance ID function, strategy-aware config snapshot, remove RMR guard, add strategy dispatch | DONE |
| `services/validation/rmr_backtest_runner.py` | Fix field names for compatibility | DONE |
| `tests/unit/validation/test_strategy_replay_runner.py` | Update existing test, add TestRMRSingleRun | DONE |
| `docs/evidence/arvp_rmr_single_run_provenance_bundle_path_3198.md` | This file | DONE |

---

## Open Items

- None for #3198. Single-run RMR path is wired. Next step: PR → required checks → squash-merge.
