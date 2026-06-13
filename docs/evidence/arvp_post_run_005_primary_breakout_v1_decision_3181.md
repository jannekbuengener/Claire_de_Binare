# ARVP Decision — post-run_005 primary_breakout_v1

**Issue**: [#3181](https://github.com/jannekbuengener/Claire_de_Binare/issues/3181)
**Parent**: [#1900](https://github.com/jannekbuengener/Claire_de_Binare/issues/1900)
**Status**: DONE_MERGED_POST_RUN_005_DECISION
**Evidence class**: `controlled_lab_evidence`
**LR verdict**: NO-GO

---

## Decision

`ALLOW_ONE_BOUNDED_EXIT_REGIME_DECAY_DIAGNOSIS_WITH_FALLBACK_PARK`

- **primary_breakout_v1 is not promotable.**
- **primary_breakout_v1 is not Product-Complete.**
- **primary_breakout_v1 has negative controlled-lab trade economics in run_005.**
- **One bounded diagnosis may inspect exit/regime-decay mechanics.**
- **No parameter optimization is allowed.**
- **If the diagnosis cannot stay bounded, PARK.**

---

## Evidence Chain

| Run | Source | Key Finding |
|-----|--------|-------------|
| run_003 | [#3174](https://github.com/jannekbuengener/Claire_de_Binare/issues/3174) | Multi-regime coverage: TREND=2676, RANGE=3366, HIGH_VOL_CHAOTIC=1533 observations (7,575 candles total). Signal and trade attribution unavailable in this run. |
| run_004 | [#3175](https://github.com/jannekbuengener/Claire_de_Binare/issues/3175) | BUY signal attribution: 5 BUY signals, **all in TREND**, zero in RANGE or HIGH_VOL_CHAOTIC. Entry filter is selective and regime-aligned. |
| run_005 | [#3179](https://github.com/jannekbuengener/Claire_de_Binare/issues/3179) | Trade lifecycle + per-regime PnL attribution: 5 trades, all entries in TREND, **4 exits in RANGE, 1 exit in TREND, all losses**, total approx **-0.0109R**. |

All evidence is `controlled_lab_evidence` only.

### Pipeline (run_005)

```
MEXC calibrated candles (7,575 rows, 1m BTCUSDT, regime-calibrated)
  → strategy_backtest_runner.py (patched #3178) → gate_trace + trades
  → build_signal_aware_candle_trace.py → BUY signal attribution
  → trade_lifecycle.json (per-trade entry/exit regime + PnL)
  → arvp_regime_scorecard_runner.py → per-regime scorecard with PnL sums
```

---

## Economic Finding

| Metric | Value |
|--------|-------|
| Total trades | 5 |
| Winning trades | 0 |
| Losing trades | 5 |
| Total PnL (R) | -0.0109R |
| Entries in TREND | 5/5 |
| Exits in RANGE | 4/5 |
| Exits in TREND | 1/5 |
| RANGE exits PnL | -0.0105R |
| TREND exits PnL | -0.0004R |

All 5 trades entered TREND (regime required for entry). 4 of 5 trades closed in RANGE — the regime had shifted by the time the channel exit triggered. The sole trade that remained in TREND had the smallest loss (-0.0004R).

---

## What Is Proven

- The entry filter correctly restricts BUY signals to TREND regime (zero false positives in RANGE/HVC across run_004).
- The trade outcome in the tested dataset is uniformly negative (5/5 losses).
- The dominant failure mode is regime-decay / exit-lag: trades entered TREND but exited after the market transitioned to RANGE.
- The pipeline from candles through backtest, signal attribution, and scorecard generation is deterministic and self-consistent.

---

## What Is Not Proven

- **Statistical conclusiveness.** 5 trades is too small a sample to assess whether the exit-lag pattern is systematic or dataset-specific.
- **SELL signal behavior.** Gate trace does not emit exit decisions — the exit attribution relies solely on trade close timestamps matched to regime segments.
- **Sensitivity to dataset.** The finding applies to a single MEXC BTCUSDT 1m dataset. Different market windows may produce different outcomes.
- **Root cause.** Whether the exit mechanics are structurally flawed or merely unlucky with this particular regime sequence has not been established.
- **Strategy general effectiveness.** Controlled-lab evidence cannot satisfy natural_paper_evidence, §5.2.4, or any Product-Complete claim.

---

## Options Considered

### Option A: PARK primary_breakout_v1

- **Rationale:** Entry filter works, but trade outcomes are uniformly negative. Controlled-lab economics do not support continued development. Park until new evidence (different dataset, different market regime, or calibration data from paper phase) justifies revisit.
- **Verdict:** Fallback option.

### Option B: One bounded exit/regime-decay diagnosis (SELECTED)

- **Rationale:** The failure mode is specific (regime-decay / exit-lag) and may be diagnosable. One explicit diagnostic slice — no optimization, no parameter tuning, no strategy change — could determine whether the exit mechanics are structurally flawed vs. dataset-artifact.
- **Constraints:** Diagnosis only. Identify per-trade entry→exit regime timeline, exit trigger distance from regime boundary, hold duration, and adverse excursion (if derivable). No parameter changes. No scoring. No promotion.
- **Verdict:** SELECTED.

### Option C: Continue evidence generation without diagnosis (REJECTED)

- **Rationale:** Without diagnosis, more evidence runs on the same strategy would produce the same negative result. Evidence churn without insight.
- **Verdict:** REJECTED.

### Option D: Move to LR/#1905/Product-Complete (REJECTED)

- **Rationale:** Negative controlled-lab economics cannot support readiness. Would violate §5.2.4, Product-Complete gate, and LR NO-GO boundary.
- **Verdict:** REJECTED.

---

## Selected Option

**Option B: One bounded exit/regime-decay diagnosis** — with fallback PARK.

1. Exactly one bounded follow-up issue may be created to inspect exit/regime-decay mechanics.
2. The follow-up scope is strictly limited to diagnosis: inspect entry timing, exit timing, regime transition timing, hold duration, and adverse excursion if already derivable from run_005 artifacts.
3. No parameter optimization, threshold tuning, or strategy logic change is permitted.
4. No new artifacts beyond what is described in the diagnosis issue scope.
5. No promotion, readiness, Product-Complete, or LR claims.
6. If the diagnosis cannot stay within these bounds, fall back to PARK primary_breakout_v1.
7. **Rejected:** further blind evidence generation (Option C), LR/#1905/Product-Complete (Option D), and any form of parameter chasing.

---

## Allowed Follow-up Scope

| Allowed | Forbidden |
|---------|-----------|
| Inspect entry/exit timing per trade | Parameter optimization |
| Inspect regime transition timing | Threshold tuning |
| Inspect hold duration | Strategy logic change |
| Inspect adverse excursion (if derivable) | New live/paper readiness claims |
| Recommend PARK if exit is structurally flawed | Natural paper evidence claims |
| | §5.2.4 clearance claims |
| | Product-Complete claims |
| | LR-Go or any Echtgeld authorization |
| | Code changes beyond diagnosis scripts |

---

## Hard Stop Conditions

- Diagnostic effort drifts into parameter optimization or tuning.
- Diagnostic effort drifts into strategy logic change or scoring.
- Diagnostic effort would require new artifacts beyond what is derivable from existing run_005 data.
- Diagnostic effort makes Product-Complete, natural_paper_evidence, §5.2.4, LR, or Paper/Live claims.
- Diagnostic effort attempts to reopen/unpark #1905 or reopen #3087.

---

## Safety / LR Boundaries

| Boundary | State |
|----------|-------|
| LR status | **NO-GO** |
| Product-Complete claim | **False** |
| natural_paper_evidence claim | **False** |
| controlled_lab satisfies §5.2.4 | **False** |
| Live-Go | **False** |
| Paper-Go | **False** |
| Real-money Go | **False** |
| #1905 unpark/reopen | **No** |
| #3087 reopen | **No** |
| Candidate promotion | **No** |
| Parameter optimization | **No** |
| Runtime mutations | **No** |
| Docker/infra changes | **No** |
| Productive DB writes | **No** |

Board stage is `trade-capable` (ratified #1492). This is orthogonal to the LR system and does not authorize live capital, strategy validation, or any readiness claim.

---

## References

- [#3181](https://github.com/jannekbuengener/Claire_de_Binare/issues/3181) — this decision issue
- [#1900](https://github.com/jannekbuengener/Claire_de_Binare/issues/1900) — ARVP parent epic
- [#3174](https://github.com/jannekbuengener/Claire_de_Binare/issues/3174) — run_003 multi-regime observation
- [#3175](https://github.com/jannekbuengener/Claire_de_Binare/issues/3175) — run_004 BUY signal attribution
- [#3179](https://github.com/jannekbuengener/Claire_de_Binare/issues/3179) — run_005 trade/PnL attribution
- [PR #3176](https://github.com/jannekbuengener/Claire_de_Binare/pull/3176) — run_004 evidence pack merge
- [PR #3178](https://github.com/jannekbuengener/Claire_de_Binare/pull/3178) — runner regime-ID patch merge
- [PR #3180](https://github.com/jannekbuengener/Claire_de_Binare/pull/3180) — run_005 evidence pack merge
- `artifacts/controlled_lab_evidence/run_003/arvp_regime_scorecard.json`
- `artifacts/controlled_lab_evidence/run_004/arvp_regime_scorecard.json`
- `artifacts/controlled_lab_evidence/run_005/arvp_regime_scorecard.json`
- `artifacts/controlled_lab_evidence/run_005/trade_lifecycle.json`
- `artifacts/controlled_lab_evidence/run_005/evidence_context.md`
- `knowledge/governance/ARVP_PRODUCT_INTENT.md`
- `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
- `docs/runbooks/CONTROL_REGISTER.md`
- `knowledge/governance/CDB_CONSTITUTION.md`
