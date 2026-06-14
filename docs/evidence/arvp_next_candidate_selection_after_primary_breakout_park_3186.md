# ARVP Next Candidate Selection after primary_breakout_v1 PARK

**Issue**: [#3186](https://github.com/jannekbuengener/Claire_de_Binare/issues/3186)
**Parent**: [#1900](https://github.com/jannekbuengener/Claire_de_Binare/issues/1900)
**Refs**: [#2985](https://github.com/jannekbuengener/Claire_de_Binare/issues/2985), [#3181](https://github.com/jannekbuengener/Claire_de_Binare/issues/3181), [#3183](https://github.com/jannekbuengener/Claire_de_Binare/issues/3183)
**Decision date**: 2026-06-14
**Status**: DONE_DECISION_ARTIFACT_PREPARED

---

## Brain Evidence

| Field | Value |
|-------|-------|
| `brain_source` | `repo-only` |
| `brain_status` | `not-used` |
| `tools_or_queries` | `read` of bootloader files and seed evidence; `git fetch origin --prune`; `git status -sb`; `git rev-parse HEAD`; `git rev-parse origin/main`; `gh pr list --state open`; `gh issue view` for `#3186`, `#2985`, `#1900`, `#3181`, `#3183`; `gh issue list --state open --search` for follow-up dedupe checks |
| `records_or_results` | `HEAD == origin/main == bbd24cfc5e134e341fd02c8a8ee9168db0296366`; open PR list empty; `#3186 OPEN`; `#2985 OPEN`; `#1900 OPEN`; `#3181 CLOSED`; `#3183 CLOSED`; known untracked foreign surfaces remain outside scope |
| `repo_crosscheck` | `docs/evidence/profitability_next_candidate_selection_3156.md`; `docs/evidence/profitability_third_candidate_selection_3164.md`; `docs/evidence/profitability_range_mean_reversion_v1_hold_park_decision_3162.md`; `docs/evidence/profitability_momentum_capture_v1_hold_park_decision_3166.md`; `docs/evidence/profitability_post_3166_tri_regime_park_next_axis_decision_3168.md`; `docs/evidence/profitability_break_even_boundary_cost_slippage_sensitivity_3170.md`; `docs/evidence/arvp_post_run_005_primary_breakout_v1_decision_3181.md`; `docs/evidence/arvp_exit_regime_decay_diagnosis_3183.md`; `docs/evidence/arvp_roadmap_reconcile_after_primary_breakout_park_2985_1900.md`; `docs/evidence/profitability_candidate_selection_3156_contract_draft.json`; `docs/evidence/profitability_candidate_momentum_capture_v1_3166.json`; `docs/evidence/profitability_league_table_report_seed_3166.json` |
| `impact_on_plan` | Later PARK and FULL_STOP decisions supersede earlier candidate selections. The strongest repo-backed result is not a new candidate promotion but `NO_PROMOTABLE_EXISTING_CANDIDATE`. |
| `limitations` | No DB-/Context-/MCP-backed evidence. No runtime or replay was executed in this slice. The seed ranking JSON is fail-closed only (`ranking_ready=false`) and cannot be used as a promotion surface. |

---

## Bootloader-/Read-Order-Evidence

- Root pointer `AGENTS.md` resolved.
- Canonical registry `agents/AGENTS.md` read.
- Full canonical read-order re-executed:
  - `knowledge/governance/CDB_CONSTITUTION.md`
  - `knowledge/governance/CDB_GOVERNANCE.md`
  - `knowledge/governance/CDB_AGENT_POLICY.md`
  - `knowledge/governance/SYSTEM_INVARIANTS.md`
  - `knowledge/CDB_KNOWLEDGE_HUB.md`
  - `docs/meta/WORKING_REPO_CANON.md`
  - `CURRENT_STATUS.md`
  - `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
  - `docs/runbooks/CONTROL_REGISTER.md`
  - `agents/OPEN_CODE_AGENTS.md`
- `CURRENT_STATUS.md` was treated as ledger only.
- GitHub live state was checked before evaluating historical roadmap and candidate-selection artifacts.
- No canonical file was missing.

---

## Live-Lage

- Branch at execution start: `main`
- Git truth at entry: `HEAD == origin/main == bbd24cfc5e134e341fd02c8a8ee9168db0296366`
- Open PRs at entry: none
- `#3186` is **OPEN** and still empty of outcome comments.
- `#2985` is **OPEN** and already reconciled to the `primary_breakout_v1` PARK truth.
- `#1900` is **OPEN** and already points to `#3186` as the next legitimate move.
- `#3181` is **CLOSED** with one bounded diagnosis allowed.
- `#3183` is **CLOSED** with the recommendation **PARK `primary_breakout_v1`**.
- LR remains **NO-GO**.
- Board stage `trade-capable` remains orthogonal to LR and does not authorize live capital.
- Known foreign untracked surfaces exist and remain untouched:
  - `.opencode/plans/`
  - `docs/decisions/ACCOUNT_BLOCKED_CHECK_WAIVER_EVALUATION_3129.md`

---

## Candidate Inventory

| Candidate / Axis | Evidence basis | Current state | Why | Allowed next move |
|------------------|----------------|---------------|-----|-------------------|
| `primary_breakout_v1` | `#3032`, `#3181`, `#3183`, `#2985` reconcile | **PARKED** | Negative controlled-lab economics, bounded diagnosis exhausted, regime-decay / exit-lag failure mode | Only revisit on new evidence or explicit governance lift |
| `range_mean_reversion_v1` | `#3156`, `#3157`, `#3162` | **PARKED** | `fee_adjusted_return_r=-0.8788`; 443 trades but still deeply negative; short-side blocked | Keep as structural comparison baseline only |
| `momentum_capture_v1` | `#3164`, `#3166` | **PARKED** | `fee_adjusted_return_r=-0.5350`; fee drag extreme; long-only first pass only | Keep as structural comparison baseline only |
| `volatility_breakout_v2` | `#3156` | **REJECTED** | Insufficient differentiation from `primary_breakout_v1`; clone/tuning risk | None |
| `momentum_pullback_v1` | `#3156` | **REJECTED** | Same TREND dependency as the parked breakout lane | None |
| `high_vol_filter_avoidance` | `#3156` | **REJECTED** | Existing contracts already block HVC where relevant; no research value | None |
| `liquidity_filtered_breakout_v1` | `#3164` | **NEEDS_EVIDENCE** | Mentioned as an archetype but no repo-backed evidence exists | Discovery/spec only |
| `regime_switch_v1` | `#3164` | **NEEDS_EVIDENCE** | Mentioned as an archetype but no repo-backed evidence exists | Discovery/spec only |
| BTCUSDT/MEXC/1m long-only loop | `#3168`, `#3170` | **FULL_STOP_ON_THIS_LOOP** | All three regime-domain candidates remain negative even at the fee-free proxy | No Candidate #4 in the same loop |

---

## Supersession Map

Earlier "selected candidate" states are not current operational truth. The later evidence chain supersedes them.

| Earlier state | Earlier source | Superseded by | Current reading |
|---------------|----------------|---------------|-----------------|
| `range_mean_reversion_v1` selected as next candidate | `docs/evidence/profitability_next_candidate_selection_3156.md` | `docs/evidence/profitability_range_mean_reversion_v1_hold_park_decision_3162.md` | Candidate was selected for a bounded pipeline pass, then PARKED. It is not promotable. |
| `momentum_capture_v1` selected as third candidate | `docs/evidence/profitability_third_candidate_selection_3164.md` | `docs/evidence/profitability_momentum_capture_v1_hold_park_decision_3166.md` | Candidate was selected for regime coverage, then PARKED. It is not promotable. |
| Tri-regime completion suggested a next axis rather than a hard stop | `docs/evidence/profitability_post_3166_tri_regime_park_next_axis_decision_3168.md` | `docs/evidence/profitability_break_even_boundary_cost_slippage_sensitivity_3170.md` | The later boundary test escalates the loop to `FULL_STOP_ON_THIS_LOOP`. |
| `primary_breakout_v1` remained a baseline reference after #3032 | `docs/evidence/profitability_primary_breakout_v1_park_decision_3032.md` | `docs/evidence/arvp_post_run_005_primary_breakout_v1_decision_3181.md`, `docs/evidence/arvp_exit_regime_decay_diagnosis_3183.md` | The later ARVP lane reconfirms and strengthens the PARK boundary. |
| Seed league-table ranks looked like a shortlist | `docs/evidence/profitability_league_table_report_seed_3166.json` | its own `ranking_ready=false` limits, plus `#3170`, `#3181`, `#3183` | Static seed rank positions are not an honest promotion surface. |

---

## Ranking / Non-Promotion Analysis

### Ranking dimensions used

1. net economic plausibility after fees/slippage
2. regime stability fit
3. evidence quality
4. replayability with available datasets
5. distance to paper-readiness
6. scope size / blast radius
7. governance safety

### Non-promotion reading

| Candidate | Economics | Regime fit | Evidence quality | Replayability | Governance safety | Result |
|-----------|-----------|------------|------------------|---------------|-------------------|--------|
| `primary_breakout_v1` | Best of the three negatives, but still gross-negative and net-negative | Fails on regime-decay / exit-lag | Highest evidence depth | High | Low, because PARK boundary is explicit | **Not promotable** |
| `momentum_capture_v1` | Net-negative, hard negative boundary at `R=-0.5350` | Covers HVC, but economics still negative | Medium-high | Medium | Medium, but no positive edge | **Not promotable** |
| `range_mean_reversion_v1` | Worst economics of the three at `R=-0.8788` | RANGE specialization does not rescue economics | Medium-high | Medium | Medium, but strongly negative | **Not promotable** |
| `liquidity_filtered_breakout_v1` / `regime_switch_v1` | Unknown | Unknown | Low | Unknown | High only as discovery scope | **Cannot rank / needs evidence** |

### Strongest non-promotion facts

- `docs/evidence/profitability_league_table_report_seed_3166.json` explicitly marks **all three** current candidates as:
  - `recommendation = PARK`
  - `ranking_ready = false`
  - static rank positions only, not a scoring surface
- `docs/evidence/profitability_break_even_boundary_cost_slippage_sensitivity_3170.md` proves:
  - `primary_breakout_v1`: gross `R=-0.075`
  - `range_mean_reversion_v1`: gross `R=-0.347`
  - `momentum_capture_v1`: gross `R=-0.206`
- Therefore all three candidates remain negative even at the fee-free proxy.
- `docs/evidence/arvp_exit_regime_decay_diagnosis_3183.md` separately closes the door on a `primary_breakout_v1` rescue path without forbidden tuning or logic change.

### Promotion verdict

**No existing repo-backed candidate satisfies a promotion threshold, a next-gate threshold, or an honest paper-readiness threshold.**

This slice therefore does not rank candidates for promotion. It ranks them only as negative baselines or unevidenced families.

---

## Decision

**Main decision:** `NO_PROMOTABLE_EXISTING_CANDIDATE`

Required interpretation encoded in this decision:

- old selected-candidate states from `#3156` and `#3164` are superseded by later PARK decisions
- seed ranks with `ranking_ready=false` are not a valid promotion basis
- `primary_breakout_v1` remains **PARKED**
- no Candidate #4 should be created inside the same BTCUSDT/MEXC/1m long-only loop
- the current loop should be treated as `FULL_STOP_ON_THIS_LOOP`

This is a valid end state for `#3186`. The evidence does not force a new candidate promotion. It forces a fail-closed recognition that the current pool of repo-backed candidates is exhausted.

---

## Recommended Follow-up

**Recommended next slice:** create a discovery/spec issue for the next post-tri-regime research axis.

Recommended issue title:

`[ARVP][DISCOVERY] Define next post-tri-regime candidate-discovery axis after BTCUSDT/MEXC/1m full stop`

Rationale:

- a same-loop Candidate #4 is explicitly not justified
- a PB1 rescue path is explicitly forbidden
- unevidenced candidate families exist, but only as discovery targets
- the next honest move is to define which new axis is evidence-backed enough to investigate next, not to implement a strategy

Expected follow-up scope:

- read-only inventory
- evidence-gap mapping
- candidate-family discovery/spec
- one recommended new research axis or explicit hold

Expected out of scope:

- implementation
- optimization
- runtime or Docker work
- DB/MCP mutation
- Live-Go / Echtgeld-Go

---

## Safety Boundaries

- LR remains NO-GO.
- Board stage trade-capable is not Live-Go.
- No Product-Complete claim.
- No natural_paper_evidence claim.
- No Live-Go / Echtgeld-Go.
- primary_breakout_v1 remains PARKED.
- No runtime, Docker, workflow, DB, or MCP mutation.
- No strategy implementation.
- No parameter optimization.
- No `#1905` unpark.

---

## Restunsicherheiten

1. The repo-backed evidence strongly supports non-promotion, but it does not yet prove which alternative future axis is best.
2. `liquidity_filtered_breakout_v1` and `regime_switch_v1` may become viable only after a dedicated discovery/spec slice creates real evidence anchors.
3. The current loop full-stop conclusion is bounded to the BTCUSDT/MEXC/1m long-only controlled-lab pool; it does not automatically invalidate other symbols, venues, or timeframes.
4. A future governance decision could reopen a parked candidate only with materially new evidence, not from reinterpretation of the current artifacts.

---

## References

- `docs/evidence/profitability_next_candidate_selection_3156.md`
- `docs/evidence/profitability_third_candidate_selection_3164.md`
- `docs/evidence/profitability_range_mean_reversion_v1_hold_park_decision_3162.md`
- `docs/evidence/profitability_momentum_capture_v1_hold_park_decision_3166.md`
- `docs/evidence/profitability_post_3166_tri_regime_park_next_axis_decision_3168.md`
- `docs/evidence/profitability_break_even_boundary_cost_slippage_sensitivity_3170.md`
- `docs/evidence/arvp_post_run_005_primary_breakout_v1_decision_3181.md`
- `docs/evidence/arvp_exit_regime_decay_diagnosis_3183.md`
- `docs/evidence/arvp_roadmap_reconcile_after_primary_breakout_park_2985_1900.md`
- `docs/evidence/profitability_candidate_selection_3156_contract_draft.json`
- `docs/evidence/profitability_candidate_momentum_capture_v1_3166.json`
- `docs/evidence/profitability_league_table_report_seed_3166.json`
