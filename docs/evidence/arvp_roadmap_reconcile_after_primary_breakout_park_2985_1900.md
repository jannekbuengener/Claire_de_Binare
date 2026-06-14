# ARVP Roadmap Reconcile after primary_breakout_v1 PARK

**Issue scope**: [#2985](https://github.com/jannekbuengener/Claire_de_Binare/issues/2985), [#1900](https://github.com/jannekbuengener/Claire_de_Binare/issues/1900)
**Reconcile date**: 2026-06-14
**Status**: CONTROL_RECONCILE_PREPARED

---

## Brain Evidence

| Field | Value |
|-------|-------|
| `brain_source` | `repo-only` |
| `brain_status` | `not-used` |
| `tools_or_queries` | `read` of bootloader and evidence docs; `git fetch origin --prune`; `git status -sb`; `git rev-parse HEAD`; `git rev-parse origin/main`; `gh pr list --state open`; `gh issue view` for `#1445`, `#1492`, `#1900`, `#1905`, `#2970`, `#2974`, `#2985`, `#3087`, `#3094`, `#3166`, `#3172`, `#3175`, `#3177`, `#3179`, `#3181`, `#3183`; `gh api graphql` and `gh api repos/.../issues/comments/...` for current control comments |
| `records_or_results` | `HEAD == origin/main == f393d270da25b9ff0533f8755a6eb84d6f90dd62`; open PR list empty; `#2985 OPEN`; `#1900 OPEN`; `#1905 CLOSED/PARKED`; `#2970 CLOSED`; `#2974 CLOSED`; `#3087 CLOSED`; `#3094 CLOSED`; `#3172/#3175/#3177/#3179/#3181/#3183 CLOSED`; `#3174/#3184 MERGED` |
| `repo_crosscheck` | `docs/evidence/arvp_post_run_005_primary_breakout_v1_decision_3181.md`; `docs/evidence/arvp_exit_regime_decay_diagnosis_3183.md`; `docs/evidence/arvp_product_complete_review_2974.md`; `docs/evidence/arvp_deterministic_window_production_3094.md`; `docs/evidence/arvp_option_e_waiver_split_decision_3087_3095.md`; `docs/evidence/profitability_range_mean_reversion_v1_hold_park_decision_3162.md`; `docs/evidence/profitability_momentum_capture_v1_hold_park_decision_3166.md`; `docs/evidence/profitability_break_even_boundary_cost_slippage_sensitivity_3170.md`; `docs/roadmaps/ARVP_TO_LIVE_GO_ROADMAP_2026-06.md` |
| `impact_on_plan` | No DB-backed or MCP-backed claims are used. GitHub live plus repo live are sufficient to reconcile #2985 and #1900. The next legitimate slice is candidate selection, not `primary_breakout_v1` tuning. |
| `limitations` | No SurrealDB/context-brain records were used. The worktree contains unrelated untracked files outside this scope and they are intentionally untouched. |

---

## Live-Lage

- Git truth: `HEAD` and `origin/main` are identical at `f393d270da25b9ff0533f8755a6eb84d6f90dd62`.
- Open PRs: none.
- `#2985` is still **OPEN**, but its body is materially stale relative to landed Phase-A and controlled-lab follow-up work.
- `#1900` remains **OPEN** as the ARVP north-star anchor.
- `#2974` is **CLOSED** with `DONE_REVIEW_COMPLETED_PRODUCT_COMPLETE_BLOCKED`.
- `#3087` is **CLOSED** after the Option-E split decision; the natural-paper blocker was not cleared.
- `#3094` is **CLOSED**; evidence classes and the campaign escalation path are documented.
- `#2970` is **CLOSED**; `#1905` remains **CLOSED/PARKED** and must not be unparked from this reconcile.
- Board stage remains `trade-capable`; LR remains **NO-GO**.

---

## Evidence Chain #3172-#3184

| Step | Live status | Key result |
|------|-------------|------------|
| `#3172` / PR `#3173` | CLOSED / MERGED | First repo-backed `controlled_lab_evidence` path produced. Explicitly not `natural_paper_evidence`. |
| PR `#3174` | MERGED | `run_003` established multi-regime controlled-lab coverage: TREND, RANGE, HIGH_VOL_CHAOTIC. |
| `#3175` / PR `#3176` | CLOSED / MERGED | `run_004` added BUY-signal attribution per regime: 5 BUY signals, all in TREND, zero false-positive BUY signals outside TREND. |
| `#3177` / PR `#3178` | CLOSED / MERGED | Runner patch persisted `entry_regime_id` and `exit_regime_id`, enabling trade-lifecycle attribution for the next run. |
| `#3179` / PR `#3180` | CLOSED / MERGED | `run_005` closed the loop: entry-regime to exit-regime to trade outcome and per-regime PnL. Result: 5 trades, all losses, 4 of 5 exits in RANGE. |
| `#3181` / PR `#3182` | CLOSED / MERGED | Decision: exactly one bounded exit/regime-decay diagnosis is allowed. No promotion, no Product-Complete claim, no parameter optimization, fallback PARK. |
| `#3183` / PR `#3184` | CLOSED / MERGED | Diagnosis found structural regime-instability plus regime-unaware exit behavior. Recommendation: **PARK `primary_breakout_v1`**. |

Required findings now repo-backed and live-backed:

- `run_003`: multi-regime controlled-lab evidence exists.
- `run_004`: BUY-signal attribution per regime exists.
- `run_005`: entry-regime to exit-regime to trade outcome/PnL attribution exists.
- `#3181` allowed exactly one bounded diagnosis.
- `#3183` recommended PARK for `primary_breakout_v1`.
- `primary_breakout_v1` is not promotable and remains parked.
- `controlled_lab_evidence` is not `natural_paper_evidence`.
- LR remains **NO-GO**.

---

## Decision: primary_breakout_v1 PARKED

- `primary_breakout_v1` is **PARKED**.
- It is **not promotable** from the controlled-lab chain.
- It is **not Product-Complete**.
- It does **not** satisfy `natural_paper_evidence` or Roadmap `§5.2.4`.
- No additional bounded diagnosis is authorized beyond `#3183`.
- No `#1905` unpark follows from this chain.
- No parameter tuning or strategy-logic change is allowed under the `#3181` boundary.

This is a PARK decision, not a success claim and not a failure of the control process. The control process did its job: it produced bounded evidence, one bounded diagnosis, and then stopped instead of drifting into optimization.

---

## Impact on #2985 roadmap

- Phase A is **not** promoted to Product-Complete by the `#3172-#3184` lane.
- The natural-paper blocker lineage remains unresolved. `controlled_lab_evidence` cannot clear the Product-Complete gate.
- `#2974` remains the last valid Product-Complete gate review, and its verdict is still **BLOCKED**.
- `#3087` closed via split, not via gate satisfaction.
- `#2970` closed with `#1905` staying closed/parked and `#2980` not becoming a valid continuation path for this parked `primary_breakout_v1` lane.
- `#2985` must therefore show two truths at once:
  - bounded controlled-lab progress was made
  - LR-facing downstream work remains blocked as a Live path

Roadmap consequence:

- No Live-Go claim.
- No Echtgeld-Go claim.
- No Product-Complete claim.
- No `#1905` unpark.
- No `primary_breakout_v1` continuation via tuning.

---

## Impact on #1900 north-star

- `#1900` remains the ARVP north-star anchor.
- The `primary_breakout_v1` controlled-lab lane contributed useful bounded evidence about regime attribution and failure mode.
- That evidence strengthens the honesty of the north-star: ARVP can identify when a candidate should be parked instead of narratively prolonged.
- The north-star is still about replay and paper-phase leverage, not about rescuing a parked candidate.
- The next honest `#1900` move is to select or specify the next candidate slice from existing repo-backed candidate evidence.

---

## Downstream LR-050 boundary

- LR remains **NO-GO**.
- Board stage `trade-capable` remains orthogonal to LR.
- No canary step is unlocked by the `primary_breakout_v1` controlled-lab chain.
- No `ready-for-human-live-approval` implication exists.
- No runtime, Docker, workflow, DB, MCP, secrets, or account-readiness claim is changed by this reconcile.

The `#3172-#3184` chain is evidence about one candidate under `controlled_lab_evidence`. It is not a Live path and not a human-approval path.

---

## Next executable slice recommendation

**Recommended next path:** select and specify the next strategy candidate instead of tuning parked `primary_breakout_v1`.

Why this is the smallest legitimate next move:

- `primary_breakout_v1` is parked under an explicit no-tuning boundary.
- Existing profitability/candidate evidence already covers three controlled-lab PARK candidates:
  - `primary_breakout_v1` — `docs/evidence/profitability_league_table_seed_primary_breakout_v1_3032.json`
  - `range_mean_reversion_v1` — `docs/evidence/profitability_range_mean_reversion_v1_hold_park_decision_3162.md`
  - `momentum_capture_v1` — `docs/evidence/profitability_momentum_capture_v1_hold_park_decision_3166.md`
- The break-even boundary review (`#3170`) concludes that the current BTCUSDT/MEXC/1m long-only loop stays parked even at the fee-free proxy.

Recommended issue shape:

- Objective: choose or specify the next candidate from existing profitability/candidate evidence.
- Scope: read-only triage, shortlist, reject/park reasons, one recommended next executable slice.
- Out of scope: implementation, optimization, runtime, Live-Go, Echtgeld-Go, and any `primary_breakout_v1` rescue attempt.

---

## Non-goals

- No Product-Complete claim.
- No `natural_paper_evidence` claim.
- No Live-Go or Echtgeld-Go.
- No `#1905` unpark.
- No `primary_breakout_v1` parameter tuning.
- No `primary_breakout_v1` strategy-logic change.
- No new controlled-lab rerun for `primary_breakout_v1`.
- No Phase B-E LR-050 advancement.
- No runtime, Docker, workflow, DB, or MCP mutation.

---

## Restunsicherheiten

1. The next candidate-selection slice may still conclude that all currently evidenced candidates remain PARK-level only.
2. The controlled-lab chain proves failure mode and boundaries, not natural-paper behavior.
3. A future candidate-selection recommendation may still require a new bounded follow-up issue to gather missing candidate evidence.
4. If fresh natural-paper evidence lands later, the parked status could be revisited only through a new governance decision, not by inference from this document.

---

## References

- `docs/evidence/arvp_post_run_005_primary_breakout_v1_decision_3181.md`
- `docs/evidence/arvp_exit_regime_decay_diagnosis_3183.md`
- `docs/evidence/arvp_product_complete_review_2974.md`
- `docs/evidence/arvp_deterministic_window_production_3094.md`
- `docs/evidence/arvp_option_e_waiver_split_decision_3087_3095.md`
- `docs/evidence/profitability_range_mean_reversion_v1_hold_park_decision_3162.md`
- `docs/evidence/profitability_momentum_capture_v1_hold_park_decision_3166.md`
- `docs/evidence/profitability_break_even_boundary_cost_slippage_sensitivity_3170.md`
- `docs/roadmaps/ARVP_TO_LIVE_GO_ROADMAP_2026-06.md`
- `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
- `docs/runbooks/CONTROL_REGISTER.md`
