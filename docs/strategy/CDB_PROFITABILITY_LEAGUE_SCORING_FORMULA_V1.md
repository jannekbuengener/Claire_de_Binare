# CDB Profitability League Scoring Formula v1

**Status:** Executable docs/contract spec for #3682
**Mode:** Docs / formula / worked examples only
**Parent:** #3032 · follows #3040 (League Table) · #3039 (Execution Economics)
**Triggered by:** #3383 coverage report (numeric formula gap)
**Live-Readiness:** NO-GO
**Runtime Impact:** none

## Purpose

This document defines the **executable Strategy League Scoring Formula v1** for
`profitability_league_table_report.v1`.

Before this formula, repo-backed league seeds used `total_score=0.0` and
`dimension_scores[].score=0.0` as **fail-closed sentinels** because no
calculation logic existed (#3383). This spec replaces unexplained zeros with
traceable rules while preserving fail-closed behavior when evidence is incomplete.

Scoring is **decision support only**. It does not authorize paper, micro-live,
live capital, runtime changes, or candidate promotion.

## Contract Artifacts

| Artifact | Path | Role |
|---|---|---|
| This formula | `docs/strategy/CDB_PROFITABILITY_LEAGUE_SCORING_FORMULA_V1.md` | Normative scoring rules |
| League table design | `docs/strategy/CDB_PROFITABILITY_LEAGUE_TABLE_V1.md` | Ranking model and semantics |
| Model schema | `docs/contracts/profitability_league_table_model.v1.schema.json` | Dimension enum + weights |
| Report schema | `docs/contracts/profitability_league_table_report.v1.schema.json` | Output shape |
| Worked example | `docs/contracts/examples/profitability_league_table_scoring_worked_example_v1.json` | Sentinel case (paper not run) |
| Coverage report | `docs/evidence/CDB_CANDIDATE_EVIDENCE_STRATEGY_LEAGUE_COVERAGE_REPORT.md` | Gap analysis input (#3383) |

## Inputs

Primary input is a `profitability_evidence_packet.v1` per candidate, optionally
joined with:

- `profitability_execution_economics_assessment.v1` (when present)
- `profitability_dataset_quality_report.v1` (when present)

No runtime scorer is required for this slice. An offline, fail-closed
implementation of these rules exists at
`services/validation/profitability_league_scorer.py` (#3684); it is decision
support only and does not authorize promotion, paper capital, or live capital.

## Schema Dimension Mapping

Formula v1 defines six scoring dimensions. Report `dimension_scores[].dimension`
MUST use these enum values (extended in model/report schemas):

| Formula dimension | Report enum | Legacy alias |
|---|---|---|
| `NET_ECONOMICS` | `NET_ECONOMICS` | `NET_RETURN` (deprecated alias, same weight slot) |
| `ROBUSTNESS` | `ROBUSTNESS` | — |
| `EVIDENCE_COMPLETENESS` | `EVIDENCE_COMPLETENESS` | — |
| `SAFETY_STATUS` | `SAFETY_STATUS` | — |
| `PAPER_REFERENCE_CONFIDENCE` | `PAPER_REFERENCE_CONFIDENCE` | — |
| `EXECUTION_REALISM` | `EXECUTION_REALISM` | — |

Legacy dimensions `DRAWDOWN_DISCIPLINE` and `STRESS_RESILIENCE` remain valid in
the schema enum for backward compatibility but are **not used** by Formula v1.
Their signals are absorbed into `NET_ECONOMICS` (drawdown) and `ROBUSTNESS`
(stress/scenario outcomes).

## Default Weights

Weights MUST sum to `100.0` and match the league model fixture
`pltm-profitability-scoring-v1`:

| Dimension | Weight % | `requires_net_economics` |
|---|---:|---|
| `NET_ECONOMICS` | 25.0 | true |
| `ROBUSTNESS` | 20.0 | true |
| `EVIDENCE_COMPLETENESS` | 15.0 | false |
| `SAFETY_STATUS` | 15.0 | false |
| `PAPER_REFERENCE_CONFIDENCE` | 15.0 | false |
| `EXECUTION_REALISM` | 10.0 | true |

Gross-only ranking is forbidden. Dimensions marked `requires_net_economics=true`
MUST score `0.0` when net economics are not assessable (see fail-closed rules).

## Score Range And Normalization

- Every dimension score is on **`[0.0, 100.0]`** (inclusive).
- Use `clamp(x, 0.0, 100.0)` for all normalized outputs.
- `total_score` is the weighted sum:

```text
total_score = Σ (dimension_score[d] × weight_pct[d] / 100.0)
```

- Round `dimension_score` and `total_score` to **one decimal place** at emission.
- `total_score` is also on `[0.0, 100.0]`.

## Global Fail-Closed Rules

### When `ranking_ready` MUST remain `false`

A candidate MUST have `ranking_ready=false` when **any** of these hold:

1. `net_return` is `null`.
2. `fees` is `null` or net economics are otherwise unassessable.
3. `replay_vs_paper_status` is `not_run` or `missing_reference`.
4. `simulator_drift` is `not_assessed` or `unusable`.
5. `regime_scorecard.status` is not `ok`.
6. `recommendation` is `UNSAFE`, `REJECT`, or `NO_RECOMMENDATION`.
7. `trade_count < 10` (insufficient sample for comparative ranking).
8. Fewer than three `scenario_results` entries with `status != NOT_RUN`.
9. Dataset quality verdict is `BLOCKED` when a quality report is linked.
10. Any dimension with `requires_net_economics=true` scores `0.0` due to missing
    required inputs (not merely low performance).

### When `total_score` MAY be computed vs sentinel

| Condition | `total_score` / `dimension_scores` behavior |
|---|---|
| `ranking_ready=false` due to hard gates (rows 1–9 above) | **Sentinel mode:** all scores `0.0`; limitations MUST explain why |
| `ranking_ready=false` only because aggregate economics are negative (`PARK`) but gates 1–9 pass | **Computed mode allowed:** real scores emitted; `ranking_ready` still `false` if recommendation is `PARK` and economics gate fails (see recommendation policy) |
| `ranking_ready=true` | **Computed mode required:** real scores; no sentinels |

**Sentinel mode** exists to prevent misleading partial scores when mandatory
evidence classes are absent (#3383). A score of `0.0` in sentinel mode is **not**
a performance measurement.

### When `total_score` MUST NOT be used for ordering

- `table_status` MUST be `PARTIAL` or `BLOCKED` when any candidate has
  `ranking_ready=false`.
- Rank positions among `ranking_ready=false` candidates are **visibility order
  only** (e.g. lexicographic `candidate_id`), not score-derived.
- Only candidates with `ranking_ready=true` may be ordered by `total_score`.

## Recommendation Policy (Non-Promotion)

| `recommendation` | Meaning for scoring | Promotion? |
|---|---|---|
| `PARK` | Candidate visible; may have computed dimension scores; **not** rank-ready for promotion comparison unless economics gate passes | **No** — research hold, not next gate |
| `REJECT` | Sentinel scores; `ranking_ready=false` | **No** |
| `PROMOTE_TO_NEXT_RESEARCH_GATE` | May be `ranking_ready=true` if all gates pass | **Advisory label only** — not executable promotion |
| `UNSAFE` | Sentinel; `ranking_ready=false` | **No** |
| `NO_RECOMMENDATION` | Sentinel; `ranking_ready=false` | **No** |

`PARK` means "hold for more evidence or economics improvement." It does **not**
authorize runtime deployment, paper capital, or live capital.

---

## Dimension Specifications

### 1. `NET_ECONOMICS`

**Purpose:** Measure fee-adjusted net performance relative to a neutral baseline.

**Input fields (PEP):**

- `net_return` (required)
- `gross_return` (required)
- `max_drawdown` (packet-level or max of `scenario_results[].max_drawdown`)
- `profit_factor` (optional)

**Score range:** `0.0` – `100.0`

**Normalization:**

```text
if net_return is null → score = 0.0  (fail-closed)

neutral = 50.0
if net_return <= 0:
    score = clamp(neutral + net_return × 250.0, 0.0, 49.9)
else:
    score = clamp(neutral + net_return × 200.0, 50.0, 100.0)

if max_drawdown is not null and max_drawdown > 0.20:
    score = clamp(score - 15.0, 0.0, 100.0)
elif max_drawdown is not null and max_drawdown > 0.10:
    score = clamp(score - 8.0, 0.0, 100.0)
```

**Fail-closed:**

- `net_return` null → `0.0`; contributes to `ranking_ready=false`.
- `gross_return` null → `0.0`.

**Example interpretation:**

- `net_return = -0.122` → base ≈ `19.5`; candidate is economically negative.
- `net_return = +0.05` → base ≈ `60.0`; positive but not promotion-proof alone.

---

### 2. `ROBUSTNESS`

**Purpose:** Measure stability across scenario windows and stress outcomes.

**Input fields:**

- `scenario_results[]` (`status`, `net_return`, `max_drawdown`, `notes`)
- `loss_streak`
- `trade_count`

**Score range:** `0.0` – `100.0`

**Normalization:**

```text
score = 100.0
for each scenario in scenario_results:
    if scenario.status == FAIL: score -= 8.0
    if scenario.status == BLOCKED: score -= 12.0
    if scenario.status == WARNING: score -= 4.0
    if "gate_result=FAIL" in scenario.notes: score -= 3.0
    if scenario.net_return is not null and scenario.net_return < -0.05: score -= 2.0

if loss_streak >= 6: score -= 10.0
elif loss_streak >= 4: score -= 5.0

if trade_count < 10: score -= 15.0

score = clamp(score, 0.0, 100.0)
```

**Fail-closed:**

- No `scenario_results` entries → `0.0`.
- All scenarios `NOT_RUN` → `0.0`.

**Example interpretation:**

- Multi-window candidate with all `gate_result=FAIL` in notes → mid-range score
  despite `status=PASS` on scenarios (controlled-lab weak gates).

---

### 3. `EVIDENCE_COMPLETENESS`

**Purpose:** Penalize missing or partial evidence needed for fair comparison.

**Input fields:**

- All PEP required fields (presence / non-null)
- `source_run_refs` (count)
- `regime_scorecard.status`
- `missing_evidence[]` (when present)
- Optional: `source_artifacts[]`

**Score range:** `0.0` – `100.0`

**Normalization:**

```text
score = 100.0
if profit_factor is null: score -= 8.0
if avg_win is null: score -= 6.0
if avg_loss is null: score -= 6.0
if max_drawdown is null: score -= 6.0
if regime_scorecard.status != ok: score -= 20.0
if len(source_run_refs) < 5: score -= 10.0
if missing_evidence present: score -= 5.0 × min(len(missing_evidence), 4)
score = clamp(score, 0.0, 100.0)
```

**Fail-closed:**

- `regime_scorecard.status == unavailable` → cap at `30.0` maximum.

**Example interpretation:**

- Primary breakout seed with null `profit_factor` / `avg_win` / `avg_loss` →
  score reduced by 20 points from completeness penalties alone.

---

### 4. `SAFETY_STATUS`

**Purpose:** Prevent unsafe or blocked candidates from ranking upward on economics
alone.

**Input fields:**

- `recommendation`
- `risk_blocks`
- `kill_switch_events`
- `safety_boundaries` (presence)
- `limitations` (safety-related text)

**Score range:** `0.0` – `100.0`

**Normalization:**

```text
base by recommendation:
  UNSAFE → 0.0
  REJECT → 10.0
  NO_RECOMMENDATION → 15.0
  PARK → 45.0
  PROMOTE_TO_NEXT_RESEARCH_GATE → 70.0

if risk_blocks > 0: base = min(base, 25.0)
if kill_switch_events > 0: base = min(base, 10.0)
if safety_boundaries missing or empty: base = min(base, 30.0)

score = clamp(base, 0.0, 100.0)
```

**Fail-closed:**

- `recommendation == UNSAFE` → `0.0`; `ranking_ready=false`.

**Example interpretation:**

- `PARK` → `45.0`: visible and reviewable, explicitly **not** a promotion signal.

---

### 5. `PAPER_REFERENCE_CONFIDENCE`

**Purpose:** Score replay-vs-paper alignment and simulator calibration confidence.

**Input fields:**

- `replay_vs_paper_status`
- `simulator_drift`

**Score range:** `0.0` – `100.0`

**Normalization:**

```text
base by replay_vs_paper_status:
  aligned → 90.0
  pessimistic_drift → 75.0
  optimistic_drift → 40.0
  ambiguous_drift → 25.0
  missing_reference → 0.0
  not_run → 0.0

drift adjustment:
  none → +5.0
  pessimistic → +0.0
  optimistic → -10.0
  ambiguous → -15.0
  unusable → score = 0.0
  not_assessed → cap final at min(computed, 20.0)

score = clamp(adjusted, 0.0, 100.0)
```

**Fail-closed:**

- `not_run` or `missing_reference` → `0.0`; forces `ranking_ready=false`
  (sentinel mode).
- `simulator_drift == unusable` → `0.0`.

**Example interpretation:**

- Current tri-candidate seeds (`replay_vs_paper_status=not_run`) → `0.0`; table
  stays `PARTIAL` with sentinel `total_score`.

---

### 6. `EXECUTION_REALISM`

**Purpose:** Score whether net economics used explicit, bounded friction assumptions.

**Input fields:**

- `fees`, `spread_cost`, `slippage_cost`
- `gross_return`, `net_return`
- Optional: execution economics assessment `ranking_ready`

**Score range:** `0.0` – `100.0`

**Normalization:**

```text
score = 0.0
if fees is not null and fees >= 0:
    score = 40.0
if spread_cost is not null and spread_cost > 0:
    score += 25.0
elif spread_cost is not null and spread_cost == 0:
    score += 5.0   # explicit zero attribution
if slippage_cost is not null and slippage_cost > 0:
    score += 25.0
elif slippage_cost is not null and slippage_cost == 0:
    score += 5.0

if gross_return is not null and net_return is not null:
    if abs(gross_return - net_return) < 1e-9 and fees == 0:
        score = min(score, 15.0)   # suspicious identity gross==net

score = clamp(score, 0.0, 100.0)
```

**Fail-closed:**

- `fees` null → `0.0`.
- Both `spread_cost` and `slippage_cost` null → cap at `40.0` maximum.

**Example interpretation:**

- Primary breakout (`fees=3489`, `spread=0`, `slippage=0`) → `50.0`: fees
  modeled, spread/slippage explicitly zero but not fully realistic.

---

## Worked Example: `primary_breakout_v1` (Sentinel Mode)

**Input:** `docs/evidence/profitability_evidence_packet_primary_breakout_v1_mexc_multi_window_3032.json`

| Gate check | Result |
|---|---|
| `net_return` present | pass |
| `replay_vs_paper_status` | **`not_run` → FAIL** |
| `simulator_drift` | **`not_assessed` → FAIL** |
| `trade_count >= 10` | pass (39) |
| `scenario_results >= 3` | pass (20) |

**Outcome:**

- `ranking_ready = false` (paper reference hard gate).
- **Sentinel mode:** `total_score = 0.0`; all `dimension_scores[].score = 0.0`.
- `recommendation = PARK` (unchanged; not promotion).
- `limitations_summary` MUST cite formula ref and gate failures.

See `docs/contracts/examples/profitability_league_table_scoring_worked_example_v1.json`.

## Tie-Breakers (When `ranking_ready=true`)

When two candidates share the same `total_score` (one decimal):

1. Higher `PAPER_REFERENCE_CONFIDENCE` score.
2. Higher `ROBUSTNESS` score.
3. Lower `max_drawdown` (packet or scenario max).
4. Higher `EVIDENCE_COMPLETENESS` score.
5. Fewer `limitations` entries.

## Safety Boundaries

- LR remains **NO-GO**.
- No Live-Go. No Echtgeld-Go.
- No runtime mutation. No DB/secrets mutation.
- No candidate promotion. No capital allocation.
- Scoring output is advisory research evidence only.
- `PROMOTE_TO_NEXT_RESEARCH_GATE` is a label, not an executable action.

## Non-Goals

- No runtime scorer service in this slice.
- No change to ARVP, Risk, Execution, or Allocation services.
- No uplift of live-readiness status.
- No reactivation of #205 / #211.

## Validation

1. Formula dimensions and weights sum to 100 %.
2. Fail-closed and sentinel rules are consistent with #3383 coverage report.
3. Worked example JSON validates against report schema.
4. Model fixture `pltm-profitability-scoring-v1` validates against model schema.
5. `rg` review: no Live-Go / Echtgeld authorization language.

This does not prove any candidate is profitable, paper-ready, or live-ready.
