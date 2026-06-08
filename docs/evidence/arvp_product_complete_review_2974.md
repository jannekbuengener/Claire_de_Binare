# ARVP Phase A Product-Complete Gate Review — #2974

**Decision Date:** 2026-06-08
**Decision:** **DONE_REVIEW_COMPLETED_PRODUCT_COMPLETE_BLOCKED**
**Product-Complete Status:** **BLOCKED** (PARTIAL)
**Verdict per Roadmap §5:** 4 of 5 gate conditions met; 1 hard blocker

---

## Brain Evidence

| Field | Value |
|-------|-------|
| `brain_source` | `repo-only` |
| `brain_status` | `not-used` |
| `tools_or_queries` | `gh issue view` (x9), `gh pr view` (x6), `gh pr list`, `gh issue list --search` (x3), `git log`, `rg` |
| `records_or_results` | 15 live GitHub queries; 14 evidence docs; 1 operator runbook; 1 roadmap; machine-readable batch/drift/scorecard summaries |
| `repo_crosscheck` | All data verified against repo files and GitHub live state |
| `impact_on_plan` | No DB/MCP/brain claims used; all evidence is GitHub+repo backed |
| `limitations` | No SurrealDB, no Context Brain, no DB-backed memory used |

---

## Bootloader / Read-Order Evidence

- `AGENTS.md` root pointer resolved ✅
- `agents/AGENTS.md` read (canonical registry, read order, brain evidence gate) ✅
- `knowledge/governance/CDB_CONSTITUTION.md`, `CDB_GOVERNANCE.md`, `CDB_AGENT_POLICY.md` ✅
- `docs/runbooks/CONTROL_REGISTER.md`: Board stage `trade-capable` (ratified 2026-04-08, #1492), LR NO-GO ✅
- `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`: LR verdict NO-GO ✅
- `CURRENT_STATUS.md`: Ledger-only, not live truth ✅
- `docs/roadmaps/ARVP_TO_LIVE_GO_ROADMAP_2026-06.md`: Phase A roadmap, §5 product-complete criteria ✅
- Git truth: HEAD `0759cbc` == `origin/main`, clean worktree ✅

---

## Live-Lage (GitHub Live Truth as of 2026-06-08)

| Issue/PR | State | Key Fact |
|----------|-------|----------|
| #2974 | **OPEN** | This review — product-complete gate decision |
| #1900 | **OPEN** | ARVP north-star anchor |
| #2961 | **CLOSED** | Calibration batch completed (2-window bank, PR #3052) |
| #2971 | **CLOSED** | Batch compare DONE_PARTIAL_DELIVERED (PR #3084, ecd08628) |
| #2972 | **CLOSED** | Operator runbook created (PR #3010, e438d265) |
| #2973 | **CLOSED** | Drift classification delivered (PR #3054, 896dd2bb) |
| #2975 | **CLOSED** | Regime scorecards evaluated (PR #3055, 56195758) — both `unavailable` |
| #2980 | **CLOSED** | Fill-model fix HOLD/BLOCKED by signal semantics gap |
| #3079 | **CLOSED** | Price policy evaluated (PR #3081, d38b0c3b) — gap confirmed as venue-level |
| #3083 | **CLOSED** | MEXC backfill HOLD_DATA_UNAVAILABLE (PR #3085, 0759cbc) |
| PR #3080 | **MERGED** | #2980 recheck evidence (7d359b83) |
| PR #3085 | **MERGED** | MEXC code infrastructure + HOLD_DATA_UNAVAILABLE (0759cbc) |
| Open PRs | **0** | No open pull requests |

---

## Key Correction: Operator Runbook A6 EXISTS

**Prior #2974 comments (2026-06-07 through 2026-06-08) stated "Operator runbook (A6) ❌ not started". That status is stale.**

The ARVP Operator Runbook was delivered via PR #3010, merged **2026-06-05** (commit `e438d265`), closing #2972. The file `docs/runbooks/ARVP_OPERATOR_RUNBOOK.md` (281 lines) is on `main` and covers:

- End-to-end operating order (window selection → extraction → replay → compare → calibrate → interpret)
- Stage-by-stage command templates
- Failure/HOLD classification table (7 classes)
- Stop rules (8 conditions)
- Artifact checklist (10 artifacts)
- Safety boundaries (9 boundaries)
- Cross-references to roadmap, contracts, and runner modules

`docs/index.md` line 13 and `docs/runbooks/README.md` line 34 already reference the runbook as "ARVP-End-to-End-Operator-Flow".

**Verdict: A6 = PASS. Previous status markers in #2974 are stale and superseded by this review.**

---

## Roadmap §5.1 — Minimum Product-Complete Criteria Matrix

| # | Criterion | Met? | Evidence |
|---|-----------|------|----------|
| 1 | Paper Reference Window Bank — at least 2 (target: 3+) comparison-grade windows | ✅ PASS | 2 windows: pilot (paper_1909_1776991354682, MEXC same-venue) + #3028 (0c39ac88-..., Binance venue_mismatch). Committed in `artifacts/calibration/2961/`. Roadmap frames 3+ as target/quality, not hard minimum. |
| 2 | Replay-vs-Paper Batch Compare — per-window deltas, fingerprints, batch aggregation | ✅ PASS | Batch compare across 2-window bank delivered via PR #3053. Per-window shadow_comparison.json, fingerprints, and batch_compare_summary.json committed. All 7 AC met (#2971 closure evidence). |
| 3 | Calibration + Drift Classification — systematic classification per window | ✅ PASS | Both windows classified `simulator_pessimistic` (PR #3054). 4 ranked findings by operational impact. Aggregate certainty: limited. Candidate execution-realism gap (Rank 1: fill model) identified from data. |
| 4 | Regime Interpretation — scorecards with activity/coverage metrics; honest if unavailable | ⚠️ PARTIAL | Both scorecards `unavailable` (no `regime_segments`). Honest, documented, no forced inference. Roadmap §5.1 says "no regime inference without data" — this is satisfied. Roadmap §5.2.4 requires at least one window with non-empty `regime_segments` — see gate matrix below. |
| 5 | Execution Realism Gap — at least one ranked data-driven gap | ✅ PASS | Rank 1 gap identified: fill model / order execution realism in replay (from both windows, fill_count_delta = -1/-1). Documented in #2973 drift classification report. |

---

## Roadmap §5.2 — Product-Complete Gate Matrix

| # | Gate Condition | Met? | Evidence / Blocker |
|---|----------------|------|---------------------|
| 1 | Window bank of at least 2 comparison-grade `paper_reference_window.v1` entries | ✅ | 2 windows committed; window width data-driven (prefer 5+ minutes per roadmap). Both windows are ~1-2 minutes — not disqualifying per roadmap text but limits regime utility. |
| 2 | Reproducible batch calibration across all bank windows — per-window deltas and drift classification | ✅ | Both windows calibrated. Batch compare (#2971) and drift classification (#2973) evidence committed. Both deterministic and reproducible. |
| 3 | At least one ranked execution-realism gap identified from calibration data | ✅ | Rank 1: fill model gap (fill_count_delta = -1/-1 across both windows). Data-driven, not theoretical. |
| 4 | Regime scorecards populated for at least one window with non-empty `regime_segments` | ❌ **BLOCKED** | Both windows (pilot ~2min, #3028 ~2min) have no `regime_segments`. Scorecards are `unavailable` for both. Per roadmap §6 A4: "Longer windows (1h+) will naturally produce regime segments." |
| 5 | Operator runbook documents ARVP end-to-end execution and interpretation | ✅ | `docs/runbooks/ARVP_OPERATOR_RUNBOOK.md` (281 lines, PR #3010, merged 2026-06-05). Covers all 7 stages. |

**Gate Result: 4 of 5 conditions met. Condition 4 (non-empty regime_segments) is the single hard blocker per roadmap text.**

---

## Product-Complete Decision

### Verdict: **BLOCKED** (PARTIAL)

ARVP Phase A is **NOT product-complete**. One hard gate criterion (§5.2.4) is unmet.

### Single Hard Blocker

| Blocker | Gate | Rationale | Resolution Path |
|---------|------|-----------|-----------------|
| No window with non-empty `regime_segments` | §5.2.4 | Both bank windows are ~1-2 minutes. Regime segmentation requires longer windows (1h+) with enough market structure to produce regime boundaries. Honest `unavailable` is correct, but the gate requires at least one populated scorecard. | Produce a longer comparison-grade paper reference window (target: 1h+) through fresh paper runtime execution or discovery of existing repo-backed evidence. |

### Additional Documented Limitations (not blocking product-complete)

| Limitation | Classification | Status | Tracks In |
|------------|---------------|--------|-----------|
| LIVE_VS_REPLAY_SIGNAL_SEMANTICS_GAP (tick vs candle close) | Documented architectural limitation | Venue-level market structure gap. No code fix available per #3079/#3081 price policy evaluation. Limits replay fidelity certainty. | #3079 (CLOSED, HOLD), #2980 (CLOSED, BLOCKED) |
| Same-venue MEXC data for #3028 window unavailable | HOLD_DATA_UNAVAILABLE | MEXC public klines only retain ~2.5 days (#3083/#3085). Code infrastructure exists; data acquisition requires alternative source (fractal, persistent DB capture, or premium API). | #3083 (CLOSED, HOLD_DATA_UNAVAILABLE) |
| 3+ comparison-grade window target | Aspirational quality target | Roadmap says "at least 2 (target: 3+)". 2-window minimum met. 3+ is a quality/stretch target, not a hard gate condition. | #1900 (north-star), #2971 (CLOSED) |
| Aggregate drift certainty: limited | Evidentiary limitation | 2 windows, one confounded by venue/regime mismatch. Cannot claim high-confidence multi-window simulator truth. | #2973 (CLOSED, documented) |

---

## Review Completion Decision for #2974

### Verdict: **DONE_REVIEW_COMPLETED_PRODUCT_COMPLETE_BLOCKED**

All #2974 acceptance criteria are satisfied:

| # | Acceptance Criterion | Status | Evidence |
|---|---------------------|--------|----------|
| 1 | Roadmap §5.1 DoD checked line by line with evidence references | ✅ | This document § Roadmap §5.1 Matrix |
| 2 | Roadmap §5.2 gate conditions evaluated | ✅ | This document § Roadmap §5.2 Gate Matrix |
| 3 | #2961 state reviewed | ✅ | CLOSED; calibration batch completed (PR #3052) |
| 4 | #1900 progress comment posted | ✅ | Will post after PR merge |
| 5 | Gaps documented with exact blockers | ✅ | This document § Blocker list |
| 6 | If complete: Phase B start identified | N/A | Product is NOT complete |
| 7 | If not complete: exact blocker list with issue refs | ✅ | 1 hard blocker + 3 documented limitations |
| 8 | No Live-Go authorization | ✅ | LR NO-GO reaffirmed |

**#2974 may be closed as DONE_REVIEW_COMPLETED_PRODUCT_COMPLETE_BLOCKED.** The review task is complete. The product is not complete, but the review itself is finished, and the blocker list is explicit and evidence-backed.

---

## Blocker / Follow-up Mapping

| Gap | Existing Issue | Follow-up Needed? | Action |
|-----|---------------|-------------------|--------|
| Operator Runbook A6 | #2972 CLOSED / PR #3010 | No | Runbook EXISTS. Dedupe check passed. |
| Non-empty regime_segments (§5.2.4) | #2975 CLOSED (scorecards `unavailable`) | ✅ Created | #3087 — [ARVP][WINDOW] Produce longer comparison-grade paper reference window(s) to satisfy regime_segments gate |
| Same-venue MEXC data beyond public klines | #3083 CLOSED (HOLD_DATA_UNAVAILABLE) | ✅ Created | #3086 — [ARVP][DATA] Acquire MEXC same-venue candle data beyond public klines retention |
| 3+ window target | #1900 (north-star), #2971 (CLOSED) | No | Combined with longer-window follow-up |
| LIVE_VS_REPLAY_SIGNAL_SEMANTICS_GAP | #3079 (CLOSED), #2980 (CLOSED) | No | Already tracked; venue-level limitation |
| LR-050 blockers (Phase B–E) | #2977 (OPEN), #2976 (OPEN) | No | Sequenced after product-complete per roadmap §8 |

---

## Safety Boundaries (all affirmed)

| Boundary | Status |
|----------|--------|
| LR remains **NO-GO** | Confirmed |
| Product-complete is NOT Live-Go | Confirmed |
| Board stage `trade-capable` is NOT Live-Go | Confirmed |
| No Echtgeld-Go | Confirmed |
| No runtime/stack start | Confirmed (docs-only) |
| No Docker/compose changes | Confirmed |
| No live exchange runtime | Confirmed |
| No productive DB writes | Confirmed |
| No data fetch/backfill | Confirmed |
| No MCP mutations | Confirmed |
| No secrets in outputs | Confirmed |
| No strategy code changes | Confirmed |

---

## References

- `docs/roadmaps/ARVP_TO_LIVE_GO_ROADMAP_2026-06.md` — Phase A roadmap, §5 product-complete criteria
- `docs/runbooks/ARVP_OPERATOR_RUNBOOK.md` — ARVP operator runbook (PR #3010, merged 2026-06-05)
- `docs/evidence/arvp_batch_compare_decision_2971.md` — #2971 closure decision (DONE_PARTIAL_DELIVERED)
- `docs/evidence/arvp_batch_compare_2971_after_2961.md` — 2-window batch compare evidence
- `docs/evidence/arvp_drift_classification_2973_after_2971.md` — multi-window drift classification
- `docs/evidence/arvp_regime_scorecards_2975_after_2973.md` — regime scorecard evaluation (both `unavailable`)
- `docs/evidence/arvp_price_policy_evaluation_3079.md` — price policy evaluation (gap confirmed venue-level)
- `docs/evidence/arvp_recheck_2980_after_3058.md` — #2980 recheck (signal semantics gap isolated)
- `docs/evidence/arvp_mexc_backfill_3083.md` — MEXC backfill attempt (HOLD_DATA_UNAVAILABLE)
- `docs/evidence/arvp_calibration_batch_2961_after_3031.md` — calibration batch summary
- `docs/runbooks/CONTROL_REGISTER.md` — Board stage `trade-capable`, LR NO-GO
- `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` — canonical LR status
- PR #3010 — ARVP operator runbook (e438d265)
- PR #3053 — batch compare delivery
- PR #3054 — drift classification (896dd2bb)
- PR #3055 — regime scorecards (56195758)
- PR #3080 — #2980 recheck evidence (7d359b83)
- PR #3081 — price policy evaluation (d38b0c3b)
- PR #3084 — #2971 closure (ecd08628)
- PR #3085 — MEXC backfill HOLD_DATA_UNAVAILABLE (0759cbc)

---

## Restunsicherheiten

1. **Longer windows may not guarantee regime_segments.** If market conditions are flat during a 1h+ window, the regime engine may still produce insufficient segments. The resolution path is probabilistic, not guaranteed.
2. **Same-venue MEXC data may remain unavailable indefinitely** if no alternative acquisition source (fractal/MEXC adapter, persistent DB capture, premium API) is viable.
3. **The 3+ window target** is a quality aspiration per roadmap text, but the leap from 2 to 3 comparison-grade windows is operationally significant (requires fresh paper runtime or new data discovery).
4. **LIVE_VS_REPLAY_SIGNAL_SEMANTICS_GAP** is classified as a venue-level limitation. If the gap is later found to be code-level rather than venue-level, blocker classification may need revision.
5. **All evidence is repo+GitHub backed.** No DB/MCP/brain claims were used.

---

## Follow-up Issues Created

| Issue | Title | Scope |
|-------|-------|-------|
| #3087 | [ARVP][WINDOW] Produce longer comparison-grade paper reference window(s) to satisfy regime_segments gate | Hard blocker (§5.2.4): produce ≥1 window with non-empty `regime_segments` |
| #3086 | [ARVP][DATA] Acquire MEXC same-venue candle data beyond public klines retention | Documented limitation: remove venue_mismatch confound via alternative MEXC data acquisition |

## Status

`DONE_REVIEW_COMPLETED_PRODUCT_COMPLETE_BLOCKED`

- Review for #2974 is **complete**.
- ARVP Phase A Product-Complete is **BLOCKED** by §5.2.4 (non-empty regime_segments).
- #2974 may be closed after PR merge.
- Follow-up issues #3087 (hard blocker) and #3086 (limitation) created.
