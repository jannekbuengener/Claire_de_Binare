# ARVP Range Mean Reversion Replay Adapter Evidence

**Issue:** [#3196](https://github.com/jannekbuengener/Claire_de_Binare/issues/3196)
**Parent:** [#1900](https://github.com/jannekbuengener/Claire_de_Binare/issues/1900)
**Foundations:** [#3157](https://github.com/jannekbuengener/Claire_de_Binare/issues/3157), [#3194](https://github.com/jannekbuengener/Claire_de_Binare/issues/3194)
**Decision date:** 2026-06-14
**Status:** DONE_EVIDENCE_NEXT_ISSUE_CREATED

---

## Brain Evidence

```
brain_source: repo-only
brain_status: used
tools_or_queries:
  - read: canonical read-order (AGENTS.md, agents/AGENTS.md, governance, CONTROL_REGISTER.md, LR-AUDIT-STATUS)
  - bash: git fetch origin --prune, git status -sb, git rev-parse HEAD
  - bash: gh pr list --state open, gh issue view 3196
  - read: #3196 issue body and plan comment
  - read: services/validation/strategy_replay_runner.py (dispatch points)
  - read: services/validation/strategy_backtest_runner.py (PB reference)
  - read: core/replay/historical_bridge.py (constants)
  - read: scripts/profitability/run_range_mean_reversion_pipeline_3157.py (signal functions)
  - read: services/execution/simulator.py (ExecutionSimulator)
  - python: verified pipeline imports work
  - bash: python -m services.validation.strategy_replay_runner --scenario-group baseline,pessimistic_execution,feed_gap --strategy-id range_mean_reversion_v1 (executed stress comparison)
  - inspect: artifacts/evidence_scenario_runs/rmr_replay_adapter_3196/rmr_replay_adapter_3196/scenario_group_manifest.json
records_or_results:
  - git: HEAD on branch evidence/rmr-replay-adapter-3196
  - gh: #3196 OPEN (dieser Slice), #3157 CLOSED (pipeline)
  - gh: #1900 OPEN (ARVP North-Star)
  - 88/88 unit tests pass (84 existing + 4 new RMR dispatch tests)
  - Scenario group run: 3/3 succeeded (baseline, pessimistic_execution, feed_gap)
  - Group manifest: rmr_replay_adapter_3196, all exit_code=0
  - Run IDs: 4ca2d456-1e17-42aa-bcd0-0270e58a17b1, 14583ef2-6c38-45ee-8a40-abc8e9e8f0e2, e6e903ce-067b-4e54-a509-d5f2e172d812
repo_crosscheck:
  - strategy_replay_runner.py dispatches by strategy_id in _run_scenario_group_path
  - rmr_backtest_runner.py reuses signal functions from pipeline via import
  - historical_bridge.py exports RANGE_MEAN_REVERSION_STRATEGY_ID/SYMBOL
  - Single-run path guard prevents RMR execution without --scenario-group
impact_on_plan:
  - #1900 Scenario-1 (Range-Reversion-V1-Rekord-Suite) is now partially executable
  - Only scenario-group dispatch is wired; single-run replay + ReplayReporter bundle is out of scope for #3196
  - Feed-gap scenario applies bar-level stale-data injection (same as PB path)
limitations:
  - repo-only; no SurrealDB/Context-Brain evidence
  - Single-run replay path returns exit code 2 for RMR
  - Evidence candles are synthetic (300 1m bars with oscillating prices, regime=1)
  - No multi-window backtest; adapter is single-pass only
```

---

## Implementation

### New modules
- **`services/validation/rmr_backtest_runner.py`**: Single-pass RMR backtest runner that reuses `evaluate_range_reversion_candle`, `compute_z_scores`, `compute_atr` from the pipeline. Produces a report dict with `run_metadata.run_id`, metrics, and trades compatible with the scenario harness.

### Modified modules
- **`core/replay/historical_bridge.py`**: Added `RANGE_MEAN_REVERSION_STRATEGY_ID` and `RANGE_MEAN_REVERSION_SYMBOL` constants.
- **`services/validation/strategy_replay_runner.py`**:
  - Added RMR to `_SUPPORTED_STRATEGY_IDS` and `_SUPPORTED_SYMBOLS`
  - Added `range_mean_reversion_runner_v1` to `_SUPPORTED_ADAPTER_IDS`
  - Refactored `_run_scenario_group_path` to dispatch via strategy-specific factory functions
  - Added RMR warmup (240 candles) in `run_arvp_replay`
  - Added single-run guard for RMR (exit code 2 with guidance message)

### Files
| File | Change |
|------|--------|
| `services/validation/rmr_backtest_runner.py` | **NEW** — 239 lines, single-pass RMR backtest runner |
| `core/replay/historical_bridge.py` | +2 lines (RMR constants) |
| `services/validation/strategy_replay_runner.py` | ~40 lines changed (imports, dispatch, warmup, guard) |
| `tests/unit/validation/test_strategy_replay_runner.py` | +60 lines (4 new test cases) |

### Tests (4 new, 88 total in file)

| Test | What it verifies |
|------|-----------------|
| `test_validate_accepts_rmr_strategy_and_adapter` | Config accepts RMR strategy/adapter |
| `test_rmr_scenario_group_dry_run_returns_0` | Dry-run with RMR scenario group exits 0 |
| `test_rmr_without_scenario_ids_returns_2` | Single-run RMR exits 2 (guard) |
| `test_rmr_runtime_error_in_scenario_group_returns_2` | Harness error propagates correctly |

### Scenario Group Run (Evidence)

```
Group ID:        rmr_replay_adapter_3196
Total scenarios: 3
Succeeded:       3
Failed:          0
Scenarios:
  ✓ baseline              4ca2d456-1e17-42aa-bcd0-0270e58a17b1
  ✓ pessimistic_execution 14583ef2-6c38-45ee-8a40-abc8e9e8f0e2
  ✓ feed_gap              e6e903ce-067b-4e54-a509-d5f2e172d812
```

---

## Gate Result

**Decision:** `FREIGABEFAEHIG` — Single-pass RMR replay adapter is verified, tested, and scenario-group-executable.

**Conditions for release:**
1. Single-run replay (provenance, registry, artifact bundle) is out of scope — will be wired under a follow-up issue
2. The adapter produces a compatible report dict with `run_metadata.run_id` as required by the scenario harness
3. No live trading, no real credentials, no testnet execution — LR remains NO-GO

**Next steps:**
1. PR created from branch `evidence/rmr-replay-adapter-3196`
2. CI validation
3. Squash-merge to `main`
4. Close #3196
5. Comment on #1900 with status update: RMR dispatch wired for scenario groups
