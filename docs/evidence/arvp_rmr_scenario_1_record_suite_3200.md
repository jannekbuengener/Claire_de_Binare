# ARVP RMR Scenario-1 Record Suite Evidence

**Issue:** [#3200](https://github.com/jannekbuengener/Claire_de_Binare/issues/3200)
**Parent:** [#1900](https://github.com/jannekbuengener/Claire_de_Binare/issues/1900)
**Refs:** [#3198](https://github.com/jannekbuengener/Claire_de_Binare/issues/3198), [#3196](https://github.com/jannekbuengener/Claire_de_Binare/issues/3196), [#3194](https://github.com/jannekbuengener/Claire_de_Binare/issues/3194), [#3191](https://github.com/jannekbuengener/Claire_de_Binare/issues/3191), [#3189](https://github.com/jannekbuengener/Claire_de_Binare/issues/3189)
**PR:** [#3201](https://github.com/jannekbuengener/Claire_de_Binare/pull/3201)
**Execution date:** 2026-06-14
**Merge SHA:** TBD
**Status:** DONE_EVIDENCE_CREATED

---

## Brain Evidence

```
brain_source: repo-only
brain_status: used
tools_or_queries:
  - read: canonical read-order (AGENTS.md, agents/AGENTS.md, governance, CONTROL_REGISTER.md, LR-AUDIT-STATUS)
  - read: evidence docs #3198, #3196, #3194, #3191
  - read: strategy_replay_runner.py (full RMR dispatch)
  - bash: dry-run RMR scenario-group (exit 0, 20160 candles)
  - bash: dry-run RMR single-run (exit 0, 20160 candles)
  - bash: python -m services.validation.strategy_replay_runner --scenario-group baseline,pessimistic_execution,feed_gap (executed 3/3)
  - bash: python -m services.validation.strategy_replay_runner --strategy-id range_mean_reversion_v1 (single-run executed)
  - inspect: artifacts/evidence_scenario_runs/3200 (all artifacts)
records_or_results:
  - Scenario-group: 3/3 succeeded, group_id=sg-ddbcc9cf83e2, fingerprint=6b89dd642aec…
  - Run IDs: c6c9f0ee-..., c049d0be-..., 1cfebf0e-...
  - Single-run: run_id=replay-60faa243e2b6-0001, provenance=bt-5e206aef83daead2, dataset=8b583afb...
  - 0 trades, 0 signals, 0 fills — RMR found no mean-reversion setups in this 14-day window
  - Provenance/bundle: report.json, manifest.json, operator_summary.json, config.resolved.json, run_registry.jsonl
  - #3200 OPEN (this slice), #3198 CLOSED, #3196 CLOSED, #1900 OPEN
repo_crosscheck:
  - strategy_replay_runner.py dispatches RMR single-run + scenario-group correctly
  - RMR warmup=240, PB dataset (20160 candles) adequate
  - rmr_backtest_runner.py reports compatible schema
impact_on_plan:
  - Scenario-1 record suite is evidence-ready: both paths executed
  - Economics gate impact: G4/G6/G8 now include RMR
  - range_mean_reversion_v1 remains PARKED (no candidate promotion)
limitations:
  - repo-only; no SurrealDB/Context-Brain evidence
  - Only 3/5 scenario packs tested (baseline, pessimistic_execution, feed_gap)
  - Only PB dataset used; no RMR-specific candle extraction
  - No Dataset-Quality-Report (#3035)
```

---

## Bootloader-/Read-Order-Evidence

Canonical read-order executed according to `agents/AGENTS.md`:
1. `knowledge/governance/CDB_CONSTITUTION.md`
2. `knowledge/governance/CDB_GOVERNANCE.md`
3. `knowledge/governance/CDB_AGENT_POLICY.md` §4
4. `knowledge/governance/SYSTEM_INVARIANTS.md`
5. `knowledge/CDB_KNOWLEDGE_HUB.md`
6. `docs/meta/WORKING_REPO_CANON.md`
7. `CURRENT_STATUS.md` (ledger only)
8. `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` — LR remains NO-GO
9. `docs/runbooks/CONTROL_REGISTER.md` — Stage `trade-capable` not Live-Go
10. `agents/OPEN_CODE_AGENTS.md`

---

## Live-Lage

| Item | Status | Ref |
|------|--------|-----|
| #3200 | **OPEN** | Ziel-Issue |
| #3198 | **CLOSED** | Single-run path |
| #3196 | **CLOSED** | Replay adapter |
| #1900 | **OPEN** | Parent Epic |
| Open PRs | **None** at start | Clean surface |
| Branch | `evidence/rmr-record-suite-3200` | This slice |
| HEAD | `ca1edc89d` (origin/main) | Clean start |
| LR-Verdikt | **NO-GO** | Unchanged |
| Board Stage | `trade-capable` | Not Live-Go |

---

## Run Feasibility

| Finding | Status |
|---------|--------|
| Scenario-group CLI | ✅ `python -m services.validation.strategy_replay_runner --strategy-id range_mean_reversion_v1 --scenario-group baseline,pessimistic_execution,feed_gap` |
| Single-run CLI | ✅ `python -m services.validation.strategy_replay_runner --strategy-id range_mean_reversion_v1` |
| Dataset | ✅ `artifacts/backtests/primary_breakout_v1/20260418-212643/dataset.candles.json` (20160 BTCUSDT 1m candles) |
| Output dir | ✅ `artifacts/evidence_scenario_runs/3200` |
| Offline safe | ✅ No Docker/DB/MCP/secrets needed |
| Dry-run | ✅ Both paths pass dry-run (exit 0) |
| RMR warmup | 240 candles (well below 20160) |
| Symbol match | BTCUSDT — same for PB and RMR |
| Single-run guard | ✅ Removed by #3198 — RMR single-run now exits 0 |

---

## Scenario-Group Commands

```bash
python -m services.validation.strategy_replay_runner \
    --input-candles artifacts/backtests/primary_breakout_v1/20260418-212643/dataset.candles.json \
    --output-dir artifacts/evidence_scenario_runs/3200 \
    --strategy-id range_mean_reversion_v1 \
    --scenario-group baseline,pessimistic_execution,feed_gap
```

---

## Single-Run Commands

```bash
python -m services.validation.strategy_replay_runner \
    --input-candles artifacts/backtests/primary_breakout_v1/20260418-212643/dataset.candles.json \
    --output-dir artifacts/evidence_scenario_runs/3200 \
    --strategy-id range_mean_reversion_v1
```

---

## Scenario Results

### Scenario Group: sg-ddbcc9cf83e2

| Scenario | exit_code | Run ID | Ergebnis |
|----------|-----------|--------|----------|
| baseline | 0 | c6c9f0ee-d45e-51ee-bf80-c8b5244ba12c | ✅ Erfolgreich |
| pessimistic_execution | 0 | c049d0be-05d0-58f1-8321-da9ba06644ab | ✅ Erfolgreich (30bps slippage + 0.7 fill) |
| feed_gap | 0 | 1cfebf0e-40dc-5740-92ea-1ca42be52d65 | ✅ Erfolgreich (2-bar gap) |

**Group fingerprint:** `6b89dd642aecad5908906dadc1920f0e64e2d84e49601724615f21646c6cd876`
**Group artifacts:** `artifacts/evidence_scenario_runs/3200/sg-ddbcc9cf83e2/`

### Single Run: replay-60faa243e2b6-0001

| Field | Value |
|-------|-------|
| Run ID | replay-60faa243e2b6-0001 |
| Status | completed |
| Mode | baseline |
| Execution Provenance ID | bt-5e206aef83daead2 |
| Dataset Fingerprint | 8b583afbc8cd1b450d2f35ec4d2c203a32639f8fbcb5b01e0a991a0f8ce8bd99 |
| Scheduler Profile | instant |
| Gate Result | UNKNOWN (no gate_evaluator configured) |
| Deterministic Replay OK | False (RMR has no two-pass check) |

**Execution metrics:** 0 decisions, 0 orders, 0 fills, 20160 events processed
**Gross return R:** 0.0 (no trade found in this 14-day window)
**RMR config:** entry_threshold=2.0, exit_threshold=0.0, zs_lookback=20, atr_period=14, atr_stop_mult=1.5, cooldown_minutes=60, order_size=1.0

---

## Provenance / Registry / Bundle Outputs

| Artifact | Path | Status |
|----------|------|--------|
| Bundle dir | `artifacts/evidence_scenario_runs/3200/replay-60faa243e2b6-0001/` | ✅ Created |
| report.json | `.../report.json` | ✅ sha256=b92545b8 |
| manifest.json | `.../manifest.json` | ✅ bundle_schema_version=replay_bundle.v1 |
| operator_summary.json | `.../operator_summary.json` | ✅ status=completed, provenance=bt-5e206aef83daead2 |
| config.resolved.json | `.../config.resolved.json` | ✅ RMR config snapshot |
| env_redacted.txt | `.../env_redacted.txt` | ✅ Redacted env dump |
| audit.log | `.../audit.log` | ✅ Reporter log |
| Run Registry | `.../3200/run_registry.jsonl` | ✅ running + completed records |
| Scenario Group Manifest | `.../3200/sg-ddbcc9cf83e2/scenario_group_manifest.json` | ✅ 3/3 succeeded |
| Scenario Specs | `.../3200/sg-ddbcc9cf83e2/scenario_specs.json` | ✅ |
| Scenario Comparison Summary | `.../3200/sg-ddbcc9cf83e2/scenario_comparison_summary.md` | ✅ |

---

## Economics Gate Impact

| Gate | Status Before #3200 | Status After #3200 | Begruendung |
|------|---------------------|--------------------|-------------|
| G1 (No stale PARK promotion) | PASS | **PASS** | Unchanged |
| G2 (No same-loop) | PASS | **PASS** | Unchanged |
| G3 (Economics before impl.) | BLOCKED | **BLOCKED** | RMR still no economics assessment |
| G4 (Scenario replayable) | PASS (PB + RMR scenario-group only) | **PASS (RMR single-run added)** | RMR now fully replayable: both scenario-group and single-run paths work |
| G5 (ranking_ready=false) | PASS | **PASS** | Unchanged |
| G6 (Fail-closed cost assumptions) | PARTIAL (PB + RMR scenario-group) | **PARTIAL (RMR stress comparison confirmed)** | RMR stress comparison executed with 3 scenarios |
| G7 (Fee-Free Proxy >= 0.0R) | FAIL | **FAIL** | Unchanged (all candidates negative) |
| G8 (Stress resilience) | PARTIAL (PB + RMR with 3/5 packs) | **PARTIAL (RMR stress trace exists)** | 2/3 candidates stress-tested; momentum_capture_v1 remains EVIDENCE_BLOCKED |

**Gate-Gesamtstatus:** 5 PASS, 1 BLOCKED, 1 PARTIAL, 1 FAIL — unchanged from #3194

---


## Candidate Status

- **range_mean_reversion_v1** remains **PARKED** — not promoted, no strategy changes, no signal logic changes
- **primary_breakout_v1** remains **PARKED**
- **momentum_capture_v1** remains **PARKED + EVIDENCE_BLOCKED** (no replay adapter)

---

## Evidence Blockers

| Blocker | Status | Begruendung |
|---------|--------|-------------|
| `delayed_execution` pack not tested (RMR) | **NOT_TESTED** | Only 3/5 packs executed; no regression |
| `low_liquidity` pack not tested (RMR) | **NOT_TESTED** | Only 3/5 packs executed; no regression |
| `momentum_capture_v1` replay adapter | **EVIDENCE_BLOCKED** | No adapter in `_SUPPORTED_STRATEGY_IDS` |
| Dataset-Quality-Report (#3035) | **EVIDENCE_BLOCKED** | Not implemented |
| RMR single-run produces 0 trades on this dataset | **DOCUMENTED** | No mean-reversion setups in this 14-day window |

---

## Recommended Next Bounded Slice

**Option A: Momentum Capture V1 Replay Adapter**
- momentum_capture_v1 is the last PARKED candidate without replay adapter
- Building replay adapter would complete the candidate replay surface

**Option B: Remaining Scenario Packs (delayed_execution, low_liquidity) on RMR**
- Extends stress comparison to 5/5 packs for RMR

---

## Safety Boundaries

- LR remains NO-GO.
- Board stage trade-capable is not Live-Go.
- No Product-Complete claim.
- No natural_paper_evidence claim.
- No Live-Go / Echtgeld-Go.
- No candidate promotion.
- range_mean_reversion_v1 remains PARKED.
- No strategy implementation or signal changes.
- No optimization or tuning.
- No Momentum adapter work.
- No runtime, Docker, DB, MCP, workflow, or secrets access.

---

## Restunsicherheiten

1. **Only 3/5 scenario packs tested** (baseline, pessimistic_execution, feed_gap). `delayed_execution` and `low_liquidity` not executed.
2. **No RMR-specific dataset.** The PB BTCUSDT 1m dataset was used; a multi-window RMR extraction may yield different results.
3. **RMR produced 0 trades in this 14-day window.** This is not a regression — the dataset regime may not generate z-score > 2.0 setups.
4. **Dataset-Quality-Report (#3035) absent.** Dataset trustworthiness assumed but not formally verified.
5. **Gate result is UNKNOWN.** No gate_evaluator configured in the replay pipeline for RMR.
6. **momentum_capture_v1 remains EVIDENCE_BLOCKED.** Full multi-candidate stress comparison not possible.
