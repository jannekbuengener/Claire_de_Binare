# ARVP Batch Compare — #2971 Closure Decision

**Decision Date:** 2026-06-08
**Decision:** **CLOSE #2971 as DONE_PARTIAL_DELIVERED** with explicit follow-ups
**Status before decision:** HOLD_PARTIAL
**Status after decision:** CLOSED (DONE_PARTIAL_DELIVERED)

---

## Brain Evidence Block

| Field | Value |
|-------|-------|
| `brain_source` | `repo-only` |
| `brain_status` | `not-used` |
| `tools_or_queries` | `gh issue view` (x8), `gh pr view` (x5), `rg`, `python -m json.tool`, file reads |
| `records_or_results` | 14 live GitHub queries; 4 evidence docs; 1 machine-readable batch summary; 1 roadmap |
| `repo_crosscheck` | All data verified against repo files and GitHub live state |
| `impact_on_plan` | No DB/MCP/brain claims used; all evidence is GitHub+repo backed |
| `limitations` | No SurrealDB, no Context Brain, no DB-backed memory used |

## Bootloader / Read-Order Evidence

- `AGENTS.md` root pointer resolved ✅
- `agents/AGENTS.md` read (canonical registry) ✅
- Read order: `CDB_CONSTITUTION.md`, `CDB_GOVERNANCE.md`, `CDB_AGENT_POLICY.md` ✅
- `docs/runbooks/CONTROL_REGISTER.md`: Board stage `trade-capable`, LR remains NO-GO ✅
- `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`: LR verdict NO-GO ✅
- `CURRENT_STATUS.md`: Ledger-only, not live truth ✅
- Git truth: HEAD `d38b0c3b7d` == `origin/main`, clean worktree ✅

## Live-Lage (GitHub Live Truth as of 2026-06-08)

| Issue | State | Key Fact |
|-------|-------|----------|
| #2971 | **OPEN** | HOLD_PARTIAL — 2-window batch compare delivered via PR #3053 (4c638357) |
| #2961 | **CLOSED** | Calibration batch completed (2-window bank, PR #3052) |
| #2973 | **CLOSED** | Drift classification delivered (PR #3054) |
| #2974 | **OPEN/BLOCKED** | Product-complete blocked on signal semantics gap |
| #2980 | **CLOSED** | HOLD — fill model fix blocked by venue-level gap |
| #3079 | **CLOSED** | Price policy evaluated (PR #3081, merge SHA d38b0c3) |
| #3028 | **MERGED** | Paper reference window (Binance venue_mismatch) |
| #3031 | **CLOSED** (#3051) | Binance candle backfill completed |
| #3081 | **MERGED** (HEAD) | Price policy evaluation landed; gap confirmed as venue-level |
| Open PRs | **0** | No open pull requests |

## #2971 Acceptance Matrix

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | Batch compare runs for all window-bank entries | ✅ PASS | 2/2 windows compared; per-window shadow_comparison.json exists |
| 2 | Per-window `shadow_comparison` output exists | ✅ PASS | Pilot: d71a4abdd5..., #3028: 8f74124bc3... |
| 3 | Per-window deltas and fingerprints documented | ✅ PASS | Documented in `arvp_calibration_batch_2961_after_3031.md` and `arvp_batch_compare_2971_after_2961.md` |
| 4 | Batch aggregation created | ✅ PASS | `artifacts/batch_compare/2971/window_bank_2/batch_compare_summary.json` + evidence doc |
| 5 | Non-comparable windows classified with explicit reason | ✅ PASS | 0 non-comparable windows; all bank entries included |
| 6 | No Live-Go implication introduced | ✅ PASS | LR remains NO-GO; documented in all evidence artifacts |
| 7 | Reproducible: same windows → same output | ✅ PASS | Deterministic artifacts; fingerprints match across runs |

**All 7 acceptance criteria met for the available 2-window bank.**

## Decision

**CLOSE #2971 as DONE_PARTIAL_DELIVERED.**

### Rationale

1. **2+ comparison-grade windows exist** — the issue's `Depends On` clause ("Window bank populated with 2+ comparison-grade windows") is satisfied. Current bank: pilot (MEXC same-venue) + #3028 (Binance venue_mismatch).

2. **All 7 acceptance criteria PASS** for the 2-window bank per the committed evidence in PR #3053.

3. **3+ window target is aspirational, not a hard closure blocker** — the ARVP roadmap ("At least 2, target: 3+") frames this as a quality target. The issue body does not list 3+ as an acceptance criterion. #2974 (product-complete review) already tracks the 3+ target explicitly.

4. **Caveats fully documented** — venue_mismatch, regime_discrepancy, proxy-only calibration, and confounded drift classification are all explicitly recorded in `arvp_batch_compare_2971_after_2961.md`.

5. **#3079/#3081 confirmed** — no price policy closes the LIVE_VS_REPLAY_SIGNAL_SEMANTICS_GAP. The gap is venue-level market structure, not intra-candle price selection.

### Caveats (not hidden, not resolved)

- **Same-venue MEXC evidence:** only the pilot window (1/2) provides MEXC-native evidence. The #3028 window uses Binance data (venue_mismatch=true).
- **Regime discrepancy:** #3028 uses regime_id=0 (TREND default) vs original regime_id=2 (HIGH_VOL_CHAOTIC).
- **Proxy-only calibration:** no explicit reject data available for either window.
- **3+ comparison-grade windows:** target not met; tracked by #2974 product-complete gate.

## Follow-up / Blocker Mapping

| Gap | Tracks In | Priority | Action |
|-----|-----------|----------|--------|
| 3+ comparison-grade windows | #2974 (product-complete), #1900 (north-star) | Medium | Already tracked; no new issue needed |
| Same-venue MEXC candle evidence | **#3083** (created alongside this decision) | Medium | Backfill MEXC 1m candles for #3028 window or future windows |
| LIVE_VS_REPLAY_SIGNAL_SEMANTICS_GAP | #3079 (CLOSED), #2974 (BLOCKED) | High | Confirmed as venue-level; no solution via price_policy; #2974 remains blocked |
| Explicit reject data | #1900 (stretch goal) | Low | Not required for 2-window batch; aspirational for full calibration |

## Safety Boundaries

- LR remains **NO-GO**
- No Live-Go / Echtgeld-Go
- No runtime execution beyond already-completed replay/compare/calibration
- No DB mutation
- No strategy code changes
- Binance candles are not MEXC evidence
- Batch evidence is offline comparison, not runtime authorization
- No trading decisions derived from this batch
- Board stage `trade-capable` is orthogonal to LR

## References

- `docs/evidence/arvp_batch_compare_2971_after_2961.md` — batch compare evidence
- `artifacts/batch_compare/2971/window_bank_2/batch_compare_summary.json` — machine-readable batch summary
- `docs/evidence/arvp_price_policy_evaluation_3079.md` — price policy evaluation (gap not closable)
- `docs/evidence/arvp_drift_classification_2973_after_2971.md` — multi-window drift classification
- `docs/roadmaps/ARVP_TO_LIVE_GO_ROADMAP_2026-06.md` — ARVP roadmap (Phase A)
- PR #3053 — original batch compare delivery
- PR #3081 — price policy evaluation
