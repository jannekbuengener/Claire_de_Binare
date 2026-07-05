# CDB Candidate Evidence & Strategy League Table — Coverage Report

## 1. Executive Summary

This report inventories existing repo-backed CDB artifacts and classifies how far
they already cover two downstream contracts:

- `profitability_evidence_packet.v1` (Candidate Evidence Packet, "PEP")
- `profitability_league_table_report.v1` / `profitability_league_table_model.v1`
  (Strategy League Table)

Delivered for [#3383](https://github.com/jannekbuengener/Claire_de_Binare/issues/3383).
Docs-only coverage/gap analysis. It ranks nothing, promotes nothing, and proves no
live readiness.

**Headline findings:**

- The **contract surfaces exist and validate**: PEP schema, League Table model +
  report schemas, and valid example fixtures are all repo-backed.
- **Producers exist** for most candidate metrics under `services/validation/` and
  `core/replay/` (replay runners, scenario harness, regime scorecard, replay-vs-paper
  compare, paper-reference window export, simulator calibration).
- **Three candidate packets already exist** (`primary_breakout_v1`,
  `range_mean_reversion_v1`, `momentum_capture_v1`) with economics, trade stats,
  scenario results, and regime scorecards populated — but several fields are `null`
  or sentinel, and paper-reference fields are `not_run`.
- **Strategy League Table is structurally ready but not honestly rankable**: seed
  reports exist with `table_status=PARTIAL`, `ranking_ready=false`, and `0.0`
  fail-closed sentinel scores because **no numeric scoring formula is defined** in
  the repo.
- **The dominant gaps are** paper-reference / replay-vs-paper alignment, a numeric
  scoring formula, and full net-economics attribution (spread/slippage), not the
  absence of producers.
- ARVP evidence remains **negative closure**: all three candidates are `PARK`, none
  passes the economics gate. Harvester evidence is operational continuity only.

**Boundaries:** LR **NO-GO**. No Live-Go, no Echtgeld-Go, no runtime mutation, no
DB/secrets mutation, no candidate promotion. Slice-E is **interim only** (no `>=72h`
PASS). #3345, #3362, #2977 remain OPEN.

---

## 2. Existing Evidence Inventory

### 2.1 Contracts & schemas (repo-backed)

| Artifact | Path | Role |
|---|---|---|
| PEP schema | `docs/contracts/profitability_evidence_packet.v1.schema.json` | Candidate evidence packet contract (28 required fields) |
| League model schema | `docs/contracts/profitability_league_table_model.v1.schema.json` | Scoring dimensions, ranking rules, recommendation semantics |
| League report schema | `docs/contracts/profitability_league_table_report.v1.schema.json` | Candidate ranking output shape |
| League strategy doc | `docs/strategy/CDB_PROFITABILITY_LEAGUE_TABLE_V1.md` | Net-first, fail-closed ranking design |
| Example fixtures | `docs/contracts/examples/profitability_*_valid.json` | Valid research-only fixtures |

### 2.2 Candidate evidence packets (repo-backed seeds)

| Candidate | Packet(s) | Recommendation |
|---|---|---|
| `primary_breakout_v1` | `profitability_evidence_packet_primary_breakout_v1_mexc_{3091,3091_calibrated_v2,multi_window_3032,sample_expansion_3032}.json` | `PARK` |
| `range_mean_reversion_v1` | `profitability_evidence_packet_range_mean_reversion_v1_mexc_multi_window_3157.json` | `PARK` |
| `momentum_capture_v1` | `profitability_evidence_packet_momentum_capture_v1_mexc_multi_window_3166.json` | `PARK` |

### 2.3 League table seeds & reports (repo-backed)

| Artifact | Path |
|---|---|
| Model seed | `docs/evidence/profitability_league_table_seed_*_{3032,3162,3166}.json` |
| Report seed | `docs/evidence/profitability_league_table_report_seed_{3032,3162,3166}.json` |

All seed reports: `table_status=PARTIAL`, `ranking_ready=false`, `total_score=0.0`
(fail-closed sentinel).

### 2.4 Producers (repo-backed code)

| Producer | Path | Produces |
|---|---|---|
| PEP assembler | `services/validation/profitability_evidence_packet_assembler.py` | Packet identity, ref assembly |
| Replay runners | `services/validation/{strategy_replay_runner,strategy_backtest_runner,rmr_backtest_runner,momentum_backtest_runner}.py` | Candidate returns, trade stats, scenarios |
| Scenario harness | `core/replay/{scenario_harness,scenario_packs,walk_forward,counterfactual}.py` | `scenario_results` |
| Regime scorecard | `services/validation/arvp_regime_scorecard_runner.py`, `core/replay/arvp_regime_scorecards.py` | `regime_scorecard` |
| Replay-vs-paper | `services/validation/replay_vs_paper_compare_runner.py`, `core/replay/replay_vs_paper_compare.py` | `replay_vs_paper_status` |
| Paper reference | `services/validation/paper_reference_window_runner.py`, `core/replay/paper_reference_window_export.py` | Paper reference windows |
| Simulator calibration | `services/validation/simulator_calibration_report_runner.py`, `core/replay/simulator_calibration_report.py` | `simulator_drift` |
| Economics gate | `services/validation/gate_evaluator.py`, `core/replay/arvp_gate.py` | Economics gate result |

### 2.5 ARVP / replay / paper evidence (repo-backed docs)

- 51 `docs/evidence/arvp_*.md` evidence documents (calibration, scenario, replay
  adapter, drift, economics-gate, window-bank).
- Paper reference / replay-vs-paper calibration: `arvp_bounded_natural_paper_window_extraction_3215.md`,
  `arvp_guarded_natural_paper_window_execution_3217.md`,
  `arvp_three_window_replay_vs_paper_calibration_3219.md`.
- Regime scorecards: `arvp_regime_scorecards_2975_after_2973.md`.
- Economics: `arvp_first_economics_gated_scenario_inventory_3191.md`,
  `arvp_execution_realism_decision_2970_after_2975.md`.
- Tri-candidate rollup (negative closure): `arvp_tri_candidate_scenario_evidence_rollup_after_3208.md`.
- Replay reports referenced by packets: `artifacts/replay_reports/mexc_multi_window_*/...`.

### 2.6 Harvester evidence (operational continuity only)

| Artifact | State |
|---|---|
| `artifacts/evidence_harvester/24h_dry_run/` | PASS (baseline, operational) |
| `artifacts/evidence_harvester/72h_ops_validation/slice-{b,c,d}-*` | INCONCLUSIVE |
| `artifacts/evidence_harvester/72h_ops_validation/slice-e-*` | **INTERIM ONLY** (#3362 OPEN) |

Mapping references: `docs/evidence/evidence_harvester_to_profitability_packet_mapping.md`,
`docs/live-readiness/LR-050-EVIDENCE-HARVESTER-ARVP-MAPPING.md`,
`docs/evidence/evidence_harvester_slice_c_inconclusive_2026-06-30.md`.

---

## 3. Candidate Evidence Packet Field Coverage

Classification legend: `AVAILABLE` · `PARTIAL` · `MISSING` ·
`BLOCKED_BY_RUNTIME_EVIDENCE` · `BLOCKED_BY_ARVP_EVIDENCE` · `BLOCKED_BY_PAPER_REFERENCE`.

Basis: repo-backed seed packets (esp. `..._primary_breakout_v1_mexc_multi_window_3032.json`)
+ Harvester→PEP mapping (`#3380`) + producer inventory.

| PEP field | Coverage | Evidence / reason |
|---|---|---|
| `schema_version` | `AVAILABLE` | Constant emitted by assembler; present in all seeds |
| `evidence_packet_id` | `AVAILABLE` | Present in seeds; assembler identity policy |
| `candidate_id` | `AVAILABLE` | Present in seeds; from candidate contract / ARVP |
| `generated_at` | `AVAILABLE` | Present in seeds |
| `dataset_id` | `AVAILABLE` | Present (`mexc_multi_window_3032`); data-quality producer |
| `dataset_fingerprint` | `AVAILABLE` | `sha256:<64>` present in seeds |
| `source_run_refs` | `AVAILABLE` | Populated (candles + replay report refs); Harvester refs are adjunct |
| `gross_return` | `AVAILABLE` | Populated by ARVP/replay (e.g. `-0.0754`) |
| `net_return` | `AVAILABLE` | Populated (e.g. `-0.1222`) |
| `fees` | `AVAILABLE` | Populated (e.g. `3489.37`) |
| `spread_cost` | `PARTIAL` | Present but `0.0`; full attribution needs Execution Economics |
| `slippage_cost` | `PARTIAL` | Present but `0.0`; full attribution needs Execution Economics |
| `profit_factor` | `PARTIAL` | `null` in primary_breakout seed; producer exists, not always emitted |
| `expectancy` | `AVAILABLE` | Populated |
| `win_rate` | `AVAILABLE` | Populated |
| `avg_win` | `PARTIAL` | `null` in seed; requires trade distribution emission |
| `avg_loss` | `PARTIAL` | `null` in seed; requires trade distribution emission |
| `max_drawdown` | `PARTIAL` | Packet-level `null`; per-scenario drawdown present |
| `loss_streak` | `AVAILABLE` | Populated |
| `trade_count` | `AVAILABLE` | Populated |
| `regime_scorecard` | `AVAILABLE` | `status=ok`, controlled_lab; producer `arvp_regime_scorecard_runner.py` |
| `scenario_results` | `AVAILABLE` | Populated across windows; scenario harness |
| `replay_vs_paper_status` | `BLOCKED_BY_PAPER_REFERENCE` | Seeds show `not_run`; producer + partial calibration (#3219) exist, not wired to candidates |
| `simulator_drift` | `BLOCKED_BY_PAPER_REFERENCE` | Seeds show `not_assessed`; needs paper reference + calibration |
| `risk_blocks` | `BLOCKED_BY_PAPER_REFERENCE` | `0`; needs paper/risk event source (paper runtime) |
| `kill_switch_events` | `BLOCKED_BY_PAPER_REFERENCE` | `0`; needs paper/risk event source |
| `recommendation` | `AVAILABLE` | `PARK` in seeds; review/assembler policy |
| `limitations` | `AVAILABLE` | Populated; Harvester can append |
| `safety_boundaries` | `AVAILABLE` | LR NO-GO / no Live-Go text present |

Optional PEP objects: `source_artifacts` `PARTIAL`, `missing_evidence` `PARTIAL`,
`coverage_readiness` `PARTIAL` (schema supports; not consistently populated in seeds).

---

## 4. Strategy League Table Field Coverage

Basis: league table report/model schemas + seed reports.

| League field | Coverage | Evidence / reason |
|---|---|---|
| `schema_version` / `report_id` / `model_id` | `AVAILABLE` | Present in seeds |
| `generated_at` | `AVAILABLE` | Present |
| `table_status` | `AVAILABLE` | `PARTIAL` value emitted honestly |
| `candidate_rankings[].candidate_id` | `AVAILABLE` | Present |
| `candidate_rankings[].rank` | `AVAILABLE` | Present |
| `candidate_rankings[].net_return` | `AVAILABLE` | Present (from PEP) |
| `candidate_rankings[].recommendation` | `AVAILABLE` | Present (`PARK`) |
| `candidate_rankings[].limitations_summary` | `AVAILABLE` | Present |
| `candidate_rankings[].ranking_ready` | `AVAILABLE` | Present, honestly `false` |
| `candidate_rankings[].total_score` | `MISSING` | `0.0` fail-closed sentinel — **no numeric scoring formula defined in repo** |
| `candidate_rankings[].dimension_scores[]` | `MISSING` | All `0.0` sentinel; scoring formula absent |
| `limitations` | `AVAILABLE` | Present |

### Scoring dimension coverage (model)

| Dimension | Coverage | Reason |
|---|---|---|
| `NET_RETURN` | `PARTIAL` | Net economics exist but negative; no normalization formula |
| `DRAWDOWN_DISCIPLINE` | `PARTIAL` | Per-scenario drawdown exists; packet `max_drawdown` null |
| `ROBUSTNESS` | `PARTIAL` | Multi-window `scenario_results` exist; no aggregation score |
| `STRESS_RESILIENCE` | `PARTIAL` | Scenario/stress signals exist (#3038 surface); no score mapping |
| `EVIDENCE_COMPLETENESS` | `PARTIAL` | Measurable from packet completeness; not computed |
| `SAFETY_STATUS` | `AVAILABLE` | Safety flags present in every packet |

**Structural conclusion:** the League Table is **assemblable in PARTIAL form today**
(candidates visible, marked not-rank-ready) but **not honestly full-rankable** until a
numeric scoring formula exists and paper-reference-dependent inputs are filled.

---

## 5. Coverage Classification Summary

| Class | PEP fields | League fields |
|---|---|---|
| `AVAILABLE` | 18 | 9 |
| `PARTIAL` | 6 (spread, slippage, profit_factor, avg_win, avg_loss, max_drawdown) | 6 dimensions + optional |
| `MISSING` | 0 required (optional objects partial) | 2 (`total_score`, `dimension_scores`) |
| `BLOCKED_BY_PAPER_REFERENCE` | 4 (replay_vs_paper_status, simulator_drift, risk_blocks, kill_switch_events) | via ROBUSTNESS/STRESS inputs |
| `BLOCKED_BY_RUNTIME_EVIDENCE` | (paper-reference inputs need paper runtime run) | — |
| `BLOCKED_BY_ARVP_EVIDENCE` | none newly blocked — ARVP metrics already populated as PARK evidence | ranking blocked by negative closure |

**Interpretation:** No required PEP field is fully `MISSING`; the binding gaps are the
6 `PARTIAL` economics/trade-distribution fields and the 4 paper-reference-blocked
fields. The League Table's only hard `MISSING` is the numeric scoring formula.

---

## 6. What Harvester Evidence Can Deliver

- `source_run_refs` adjunct provenance (report/watchdog/write-audit/boot refs).
- `limitations` inputs: gap findings, provenance caveats, missing/zero paper-chain
  signals, source-mode caveats, active-run status.
- `safety_boundaries` text: LR NO-GO, no Live-Go, no Echtgeld-Go, no runtime/DB action.
- Operational continuity evidence (once #3362 reaches a final `>=72h` PASS).
- Coverage/gap and freshness/trust signals that can **downgrade** confidence.

## 7. What Harvester Evidence Cannot Deliver

- `gross_return`, `net_return`, `fees`, `spread_cost`, `slippage_cost`.
- `profit_factor`, `expectancy`, `win_rate`, `avg_win`, `avg_loss`, `max_drawdown`,
  `loss_streak`, candidate `trade_count`.
- `scenario_results`, candidate `regime_scorecard`.
- `replay_vs_paper_status`, `simulator_drift`.
- `risk_blocks`, `kill_switch_events` (safety flags ≠ event counts).
- `recommendation` (must not recommend promotion).
- Any League Table score or ranking authority.

## 8. What ARVP Must Deliver

- Candidate returns and trade statistics (`gross_return`, `profit_factor`,
  `expectancy`, `avg_win`, `avg_loss`, `max_drawdown`, `loss_streak`, `trade_count`).
- `scenario_results` from the scenario harness / batch output.
- Candidate `regime_scorecard` (calibration).
- A **promotable candidate**: today all three are `PARK` and fail the economics gate
  (G7). Without a candidate clearing economics, the League Table stays negative
  closure regardless of coverage.

## 9. What Paper Reference Windows Must Deliver

- Explicit paper reference windows to enable `replay_vs_paper_status`.
- `simulator_drift` classification via replay-vs-paper compare + simulator
  calibration.
- `risk_blocks` / `kill_switch_events` truth from a paper runtime event source.
- Partial calibration evidence exists (`#3215`/`#3217`/`#3219`) but is **not wired**
  into the candidate packets, which still record `not_run` / `not_assessed`. Wiring
  and any fresh natural-paper window require a separate **Runtime-GO** (paper runtime).

## 10. What Execution Economics Must Deliver

- Full `net_return` attribution with explicit `fees`, `spread_cost`, `slippage_cost`
  (seeds currently carry `spread_cost=0.0`, `slippage_cost=0.0`).
- `ranking_ready` economics readiness flag consumed by the League Table.
- The net-economics model that `profitability_league_table_model.v1` requires for
  `requires_net_economics=true` dimensions; gross-only ranking is forbidden.

---

## 11. Deduplicated Follow-Up Candidates

Existing open issues already cover the gaps. **No new issues required** in this slice.

| Gap | Existing issue / path | Notes |
|---|---|---|
| Coverage report (this) | **#3383** | Closes after PR merge |
| Packet assembler wiring | **#3381** | Assembles refs, applies recommendation policy |
| Harvester→PEP mapping | **#3380** (CLOSED) | Input contract for #3381/#3383 |
| LR-050 evidence mapping | **#3382** (CLOSED) | Sister mapping |
| Harvester `>=72h` proof | **#3362** (CLOSED) | Slice-E **PASS** (73.064h, 293/293); see §11 addendum |
| Harvester parent | **#3345** (CLOSED) | Always-on backbone delivered; see §11 addendum |
| LR-050 refresh | **#2977** | CLOSED after #3382; not reopened here |
| Strategy selector (downstream) | **#205** | Consumes #3383 output; not reactivated |

**Numeric scoring formula gap** — addressed by
`docs/strategy/CDB_PROFITABILITY_LEAGUE_SCORING_FORMULA_V1.md` (#3682). League
seeds may continue to show sentinel `0.0` until paper-reference evidence is wired
and `ranking_ready` gates pass.

---

## 12. Safety Boundaries

- LR remains **NO-GO**.
- No Live-Go.
- No Echtgeld-Go.
- No runtime mutation.
- No Docker / DB / Redis / secrets mutation.
- No candidate promotion, recommendation execution, or capital allocation.
- Board stage `trade-capable` is orthogonal to LR and is not Live-Go.
- Slice-E `>=72h` **PASS** delivered 2026-07-05 (#3362 CLOSED); does not imply LR-Go.
- ARVP, backtest, replay, and paper evidence are research inputs, not approval.
- This report ranks nothing and authorizes nothing.

### §11 addendum (2026-07-05, #2985 reconcile)

Historical §11 rows listed #3345/#3362 as OPEN at report publish time. GitHub-live
(2026-07-05): **#3345 CLOSED**, **#3362 CLOSED** (Slice-E PASS), **#3733 CLOSED**
(Tier-1 supervisor PASS), **#3738 CLOSED** (scheduler PASS + Tier-3 limitation).
Harvester/Ops does not clear LR-Go. **Next strategic focus: #1900** (ARVP Phase A).

---

## Document Metadata

| Field | Value |
|---|---|
| Issue | [#3383](https://github.com/jannekbuengener/Claire_de_Binare/issues/3383) |
| Upstream | #3345, #3362, #3380, #3381, #3382 |
| Downstream | #205 (Strategy Gearbox / selector) |
| LR verdict at publish | **NO-GO** (unchanged) |
| Scope | docs-only coverage/gap analysis |
