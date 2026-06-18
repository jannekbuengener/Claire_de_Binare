# ARVP Momentum Capture Scenario-Group Evidence (#3208)

**Issue:** [#3208](https://github.com/jannekbuengener/Claire_de_Binare/issues/3208)
**Parent:** [#1900](https://github.com/jannekbuengener/Claire_de_Binare/issues/1900)
**Refs:** [#3202](https://github.com/jannekbuengener/Claire_de_Binare/issues/3202), [#3200](https://github.com/jannekbuengener/Claire_de_Binare/issues/3200), [#3198](https://github.com/jannekbuengener/Claire_de_Binare/issues/3198), [#3196](https://github.com/jannekbuengener/Claire_de_Binare/issues/3196), PR [#3203](https://github.com/jannekbuengener/Claire_de_Binare/pull/3203)
**Execution date:** 2026-06-15
**Status:** DONE_EVIDENCE_CREATED

---

## Brain Evidence

```text
brain_source: repo-only
brain_status: not-used
tools_or_queries:
  - read: canonical read-order (AGENTS.md, agents/AGENTS.md, governance, WORKING_REPO_CANON, CURRENT_STATUS ledger, LR-AUDIT, CONTROL_REGISTER, OPEN_CODE_AGENTS)
  - bash: git fetch origin --prune; git status -sb; git rev-parse HEAD; git rev-parse origin/main
  - bash/gh: gh pr list --state open; gh issue view 3208, 3202, 1900, 1445
  - read: docs/evidence/arvp_momentum_capture_replay_adapter_evidence_3202.md
  - read: docs/evidence/arvp_rmr_scenario_1_record_suite_3200.md
  - read: docs/evidence/arvp_rmr_single_run_provenance_bundle_path_3198.md
  - read: services/validation/momentum_backtest_runner.py
  - read: services/validation/strategy_replay_runner.py
  - read: core/replay/scenario_packs.py; core/replay/scenario_harness.py
  - read: tests/unit/validation/test_strategy_replay_runner.py
  - bash: momentum scenario-group dry-run
  - bash: momentum scenario-group execution for baseline,pessimistic_execution,feed_gap
  - bash: repo-backed metric/provenance extraction from the same runtime code paths
records_or_results:
  - Git: main == origin/main == 17960463dcfee9ff1ff977df1c1a086a5c94ef1a at start
  - GitHub: #3208 OPEN, #3202 CLOSED, #1900 OPEN, #1445 OPEN
  - Scenario-group: 3/3 succeeded, group_id=sg-ddbcc9cf83e2, fingerprint=6b89dd642aecad5908906dadc1920f0e64e2d84e49601724615f21646c6cd876
  - Scenario run IDs: baseline=c6c9f0ee-d45e-51ee-bf80-c8b5244ba12c, pessimistic_execution=c049d0be-05d0-58f1-8321-da9ba06644ab, feed_gap=1cfebf0e-40dc-5740-92ea-1ca42be52d65
  - Dataset path: artifacts/backtests/primary_breakout_v1/20260418-212643/dataset.candles.json
  - Dataset fingerprint: 8b583afbc8cd1b450d2f35ec4d2c203a32639f8fbcb5b01e0a991a0f8ce8bd99
repo_crosscheck:
  - strategy_replay_runner.py already dispatches momentum single-run and scenario-group paths
  - scenario_packs.py is shared and strategy-agnostic for baseline/pessimistic_execution/feed_gap
  - scenario_harness.py writes deterministic manifest/specs/summary, but no per-scenario replay bundle
impact_on_plan:
  - The remaining gap after #3202 was an evidence-run gap, not a missing built-in pack definition gap
  - No code change was required to execute momentum scenario-group safely on the existing architecture
limitations:
  - repo-only; no SurrealDB/MCP/DB-backed evidence
  - Scenario-group path currently writes manifest/specs/summary only, not per-scenario replay bundles or run_registry entries
  - All three executed scenarios produced zero signals and zero trades on this dataset, so stress-variant deltas are structurally absent in this run
```

---

## Bootloader-/Read-Order-Evidence

Canonical read-order executed according to `agents/AGENTS.md`:
1. `knowledge/governance/CDB_CONSTITUTION.md`
2. `knowledge/governance/CDB_GOVERNANCE.md`
3. `knowledge/governance/CDB_AGENT_POLICY.md`
4. `knowledge/governance/SYSTEM_INVARIANTS.md`
5. `knowledge/CDB_KNOWLEDGE_HUB.md`
6. `docs/meta/WORKING_REPO_CANON.md`
7. `CURRENT_STATUS.md` (ledger only)
8. `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
9. `docs/runbooks/CONTROL_REGISTER.md`
10. `agents/OPEN_CODE_AGENTS.md`

GitHub live was checked before any status assumption for `#3208`, `#3202`, `#1900`, `#1445`, and open PR state.

---

## Live-Lage

| Item | Status | Ref |
|------|--------|-----|
| Branch at start | `main` | local Git truth |
| HEAD / origin/main | `17960463dcfee9ff1ff977df1c1a086a5c94ef1a` | equal |
| Dirty foreign surfaces | `.opencode/plans/`, `docs/decisions/` | untouched |
| `#3208` | **OPEN** at execution start | target issue |
| `#3202` | **CLOSED** | adapter + single-run already landed |
| `#1900` | **OPEN** | parent epic |
| Open PRs | Dependabot only: `#3204`-`#3207` | non-blocking queue noise |
| LR verdict | **NO-GO** | unchanged |
| Board stage | `trade-capable` | not Live-Go |

---

## Scenario-Pack Feasibility

### Current architecture

- `core/replay/scenario_packs.py` defines shared built-in deterministic packs:
  - `baseline`
  - `pessimistic_execution`
  - `delayed_execution`
  - `low_liquidity`
  - `feed_gap`
- `services/validation/strategy_replay_runner.py` accepts `--scenario-group` for all supported strategies.
- `momentum_capture_v1` is already in:
  - `_SUPPORTED_STRATEGY_IDS`
  - `_SUPPORTED_SYMBOLS`
  - `_SUPPORTED_ADAPTER_IDS`
- `strategy_replay_runner.py::_make_momentum_run_single_fn()` resolves scenario overrides, applies replay-data overrides, and delegates to `run_momentum_capture_backtest()`.

### Why the residual gap after #3202 still existed

The repo no longer shows a missing built-in pack-definition gap for momentum.
The actual residual was narrower:

- single-run momentum replay was already operational after #3202
- shared scenario packs already existed and were strategy-agnostic
- what was still missing was a repo-backed momentum scenario-group execution and evidence artifact

### Strategy-agnostic check

The executed packs stay within shared, deterministic override surfaces:

| Scenario | Surface | Override type |
|----------|---------|---------------|
| `baseline` | none | reference run |
| `pessimistic_execution` | `ExecutionSimulator` config | slippage/fill/posture |
| `feed_gap` | replay-data perturbation | `feed_gap_bars=2` |

No strategy-specific signal logic was added or invented.

### Exact command

Dry-run:

```bash
python -m services.validation.strategy_replay_runner \
    --input-candles artifacts/backtests/primary_breakout_v1/20260418-212643/dataset.candles.json \
    --output-dir artifacts/evidence_scenario_runs/3208 \
    --strategy-id momentum_capture_v1 \
    --symbol BTCUSDT \
    --adapter-id momentum_capture_runner_v1 \
    --scenario-group baseline,pessimistic_execution,feed_gap \
    --dry-run
```

Execution:

```bash
python -m services.validation.strategy_replay_runner \
    --input-candles artifacts/backtests/primary_breakout_v1/20260418-212643/dataset.candles.json \
    --output-dir artifacts/evidence_scenario_runs/3208 \
    --strategy-id momentum_capture_v1 \
    --symbol BTCUSDT \
    --adapter-id momentum_capture_runner_v1 \
    --scenario-group baseline,pessimistic_execution,feed_gap
```

---

## Changed Surfaces or Evidence Blocker

### Changed surfaces

| Surface | Change |
|---------|--------|
| `artifacts/evidence_scenario_runs/3208/sg-ddbcc9cf83e2/scenario_group_manifest.json` | new generated evidence |
| `artifacts/evidence_scenario_runs/3208/sg-ddbcc9cf83e2/scenario_specs.json` | new generated evidence |
| `artifacts/evidence_scenario_runs/3208/sg-ddbcc9cf83e2/scenario_comparison_summary.md` | new generated evidence |
| `docs/evidence/arvp_momentum_capture_scenario_group_evidence_3208.md` | this repo-backed evidence summary |

### No blocker outcome

No execution blocker was found for `baseline`, `pessimistic_execution`, or `feed_gap` on `momentum_capture_v1`.

The remaining architecture limit is non-blocking for `#3208`:

- the current scenario-group path writes manifest/specs/summary only
- it does **not** emit per-scenario replay bundles, run_registry entries, or operator summaries

This is documented below as a known boundary, not as a blocker to this issue's acceptance.

---

## Scenario-Group Commands

### Executed dry-run

```text
DRY-RUN: scenario group valid, dataset loaded. source='file', candles_total=20160.
```

### Executed group run

```bash
python -m services.validation.strategy_replay_runner \
    --input-candles artifacts/backtests/primary_breakout_v1/20260418-212643/dataset.candles.json \
    --output-dir artifacts/evidence_scenario_runs/3208 \
    --strategy-id momentum_capture_v1 \
    --symbol BTCUSDT \
    --adapter-id momentum_capture_runner_v1 \
    --scenario-group baseline,pessimistic_execution,feed_gap
```

---

## Scenario Results or Evidence Blockers

### Scenario-group result

| Field | Value |
|-------|-------|
| Group ID | `sg-ddbcc9cf83e2` |
| Group fingerprint | `6b89dd642aecad5908906dadc1920f0e64e2d84e49601724615f21646c6cd876` |
| Started | `2026-06-15T10:36:32.834876+00:00` |
| Finished | `2026-06-15T10:36:33.022814+00:00` |
| Succeeded | `3/3` |

### Per-scenario outcomes

| Scenario | Exit | Run ID | Derived execution provenance | Signals | Closed trades | Fee-adjusted return R |
|----------|------|--------|------------------------------|---------|---------------|-----------------------|
| `baseline` | `0` | `c6c9f0ee-d45e-51ee-bf80-c8b5244ba12c` | `bt-ecfe13aa0e37badf` | `0` | `0` | `0.0` |
| `pessimistic_execution` | `0` | `c049d0be-05d0-58f1-8321-da9ba06644ab` | `bt-ecfe13aa0e37badf` | `0` | `0` | `0.0` |
| `feed_gap` | `0` | `1cfebf0e-40dc-5740-92ea-1ca42be52d65` | `bt-ecfe13aa0e37badf` | `0` | `0` | `0.0` |

### Interpretation

- All three scenarios are safely executable on the existing shared scenario-pack architecture.
- This run produced **no signals and no trades** in any of the three scenarios.
- Therefore, the stress variants demonstrate execution-path availability, but not economically differentiated outcomes on this dataset.
- No blocker remains for the narrow `#3208` goal of proving momentum scenario-group executability.

---

## Provenance / Registry / Bundle Outputs

### Repo-backed outputs that do exist

| Artifact | Path | Status |
|----------|------|--------|
| Group manifest | `artifacts/evidence_scenario_runs/3208/sg-ddbcc9cf83e2/scenario_group_manifest.json` | ✅ |
| Scenario specs | `artifacts/evidence_scenario_runs/3208/sg-ddbcc9cf83e2/scenario_specs.json` | ✅ |
| Scenario summary | `artifacts/evidence_scenario_runs/3208/sg-ddbcc9cf83e2/scenario_comparison_summary.md` | ✅ |

### Known architecture limit

The current scenario-group path does **not** write the single-run bundle surfaces known from `#3202` / `#3198`, e.g.:

- `report.json`
- `manifest.json`
- `config.resolved.json`
- `env_redacted.txt`
- `operator_summary.json`
- `run_registry.jsonl`

For this slice, that is documented as a non-blocking architecture boundary because `#3208` asked for safe momentum scenario-group execution and exact evidence, not full scenario-group bundle parity.

---

## Economics Gate Impact

| Area | Impact |
|------|--------|
| Signal logic | none |
| Fee model | none |
| Execution surface | none beyond existing shared simulator overrides |
| Replay data semantics | none beyond existing deterministic `feed_gap_bars` injection |
| Promotion gates | none |

### Conclusion

- `#3208` closes a bounded **evidence-run** gap only.
- No new economics-positive claim is justified.
- No candidate promotion is justified.
- The run reconfirms that `momentum_capture_v1` remains a negative or unevidenced family for promotion decisions on this axis.

---

## Candidate Status

- `momentum_capture_v1 remains PARKED.`
- No candidate promotion.
- No strategy implementation or signal changes.
- No optimization.
- No runtime services, Docker, DB, or MCP work.

---

## Recommended Next Bounded Slice

No mandatory follow-up is required to close `#3208`.

Optional future slice only if specifically needed:

- scenario-group bundle parity for shared replay runs
- per-scenario replay bundle outputs and registry/provenance surfaces similar to the single-run path

That is an architecture-convenience slice, not a blocker for the current momentum scenario-group evidence closure.

---

## Safety Boundaries

LR remains NO-GO.

Board stage trade-capable is not Live-Go.

No Product-Complete claim.

No natural_paper_evidence claim.

No Live-Go / Echtgeld-Go.

No candidate promotion.

momentum_capture_v1 remains PARKED.

---

## Restunsicherheiten

1. The current scenario-group path proves safe execution, but not per-scenario bundle parity with the single-run path.
2. All three scenarios produced zero signals and zero trades on this dataset, so there is no differentiated stress-outcome table beyond successful execution.
3. The derived execution provenance value stayed identical across all three scenarios in this run. That is non-blocking here, but it reinforces that scenario-group provenance granularity is weaker than the single-run path.
4. This slice does not change the broader economics verdict for `momentum_capture_v1`; it only closes the scenario-group replay evidence gap.
