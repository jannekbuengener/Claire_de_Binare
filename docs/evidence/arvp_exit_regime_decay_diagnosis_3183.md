# ARVP Exit/Regime-Decay Diagnosis — post-run_005

**Issue**: [#3183](https://github.com/jannekbuengener/Claire_de_Binare/issues/3183)
**Parent**: [#1900](https://github.com/jannekbuengener/Claire_de_Binare/issues/1900)
**Decision**: [#3181](https://github.com/jannekbuengener/Claire_de_Binare/issues/3181)
**Status**: DONE_MERGED_PARK_RECOMMENDATION
**Evidence class**: `controlled_lab_evidence`
**LR verdict**: NO-GO

---

## Decision Context

Per decision [#3181](https://github.com/jannekbuengener/Claire_de_Binare/issues/3181) (`ALLOW_ONE_BOUNDED_EXIT_REGIME_DECAY_DIAGNOSIS_WITH_FALLBACK_PARK`), exactly one bounded diagnosis may inspect exit/regime-decay mechanics. No parameter optimization, no strategy logic change, no runner behavior change. If the diagnosis cannot stay bounded, PARK primary_breakout_v1.

---

## Input Evidence

All analysis uses existing run_005 artifacts only:

| Artifact | Path | Content |
|----------|------|---------|
| Trade lifecycle | `artifacts/controlled_lab_evidence/run_005/trade_lifecycle.json` | Per-trade entry/exit timestamps, prices, regime IDs, r_return |
| Combined trace | `artifacts/controlled_lab_evidence/run_005/trace.json` | 60,423-step replay trace with per-candle regime_id, signal attribution, gate trace status |
| Gate trace | `artifacts/controlled_lab_evidence/run_005/gate_trace.jsonl` | Entry-pathway gate decisions (entry_ready, breakout_threshold, regime_id, has_trend_regime) |
| Scorecard | `artifacts/controlled_lab_evidence/run_005/arvp_regime_scorecard.json` | Per-regime BUY signal counts, trade close counts, PnL sums |
| Evidence context | `artifacts/controlled_lab_evidence/run_005/evidence_context.md` | Pipeline description, caveats |

**No new artifacts were generated. No controlled_lab rerun was performed. No parameter optimization was performed. No strategy behavior was changed.**

---

## Trade Lifecycle Table

| # | Entry (ms) | Exit (ms) | Hold | Entry Regime | Exit Regime | Regime Flips | r_return | Notes |
|---|-----------|-----------|------|---|---|---|---|---|---|
| 0 | 1768597140000 | 1768612380000 | 254 min | TREND (0) | RANGE (1) | 5 | -0.00227 | First decay at +30 min; 164 min in exit regime |
| 1 | 1768662360000 | 1768666920000 | 76 min | TREND (0) | RANGE (1) | 3 | -0.00402 | **Worst loss.** First decay at +15 min (shortest); 42 min in exit regime |
| 2 | 1768760880000 | 1768777380000 | 275 min | TREND (0) | RANGE (1) | 13 | -0.00247 | Most regime flips; high choppiness (1 flip every ~21 min) |
| 3 | 1768810680000 | 1768827900000 | 287 min | TREND (0) | TREND (0) | 10 | -0.00042 | **Smallest loss.** Only trade to exit in TREND. Still negative. |
| 4 | 1768967040000 | 1768980720000 | 228 min | TREND (0) | RANGE (1) | 11 | -0.00171 | First decay at +2 min (HVC); 25 min in exit regime |

**Summary:** Hold durations 76–287 min. All entries TREND. 4/5 exits RANGE. 1/5 exits TREND. All r_returns negative. Total regime flips per trade: 3–13 (avg 8.4). Even Trade 3 (TREND exit, 10 flips during hold) was negative.

**Comparison:**
- **Worst trade** (#1, -0.00402R): shortest hold (76 min), quickest decay (15 min), exited RANGE.
- **Best trade** (#3, -0.00042R): longest hold (287 min), exited TREND, but still lost despite regime alignment at exit.
- **No trade was ever profitable open-to-close.** Mark-to-market (MAE/MFE) is unavailable in current artifacts.

---

## Regime Transition Findings

The combined trace was analyzed to locate all regime transitions affecting each trade. Key findings:

### 1. Regime Instability Is Pervasive

Across all 5 trades, **42 regime flips** occurred between entry and exit (avg 8.4 per trade, median ~30 min TREND segment duration). The strategy enters on TREND but the holding period spans multiple regime oscillations.

### 2. Entry-to-First-Decay Timing Varies Widely

| Trade | First decay (min after entry) | Flip direction |
|-------|:---:|--------|
| 0 | +30 | TREND -> RANGE |
| 1 | +15 | TREND -> RANGE |
| 2 | +42 | TREND -> RANGE |
| 3 | +6 | TREND -> HVC |
| 4 | +2 | TREND -> HVC |

The entry filter correctly blocks entry outside TREND, but the market does not stay in TREND long enough for hold-to-exit periods of 1-5 hours. The median TREND residence is approximately 30 minutes -- well below the shortest trade's hold duration (76 min).

### 3. Exit Timing Is Regime-Unaware

The channel exit fires at a mechanical price/timing signal. It has no knowledge of whether the current regime is TREND or RANGE. 4/5 trades exited while in RANGE because:
- The market regime oscillated multiple times during the hold period
- When the channel exit fired, the market happened to be in RANGE (4/5) or TREND (1/5)
- The distribution (4 RANGE : 1 TREND) approximately matches the observation ratio (RANGE=3366 / TREND=2676 = 1.26) -- i.e. exits are not systematically favoring RANGE beyond what the regime distribution predicts

### 4. All Trades Were Negative Irrespective of Exit Regime

Even Trade 3, which exited in TREND (the only such trade), posted -0.00042R. This suggests the entry-to-exit price movement was adverse regardless of exit regime. The channel exit fired at a price below entry in all 5 cases.

### 5. Entry = Signal (Market Order)

All 5 BUY signal timestamps in trace.json (`signals_emitted=1`) match exactly the `entry_ts_ms` in trade_lifecycle.json. The backtest enters at the signal candle -- no entry delay or slippage that could explain adverse pricing.

---

## Exit/Decay Hypothesis

**Primary:** The strategy enters on TREND via breakout, but the market regime oscillates between TREND, RANGE, and HIGH_VOL_CHAOTIC at a rate (average ~1 flip every 27 minutes) that is faster than the multi-hour hold-to-exit duration. The exit mechanism (channel exit) is regime-unaware -- it fires when a mechanical price condition is met, not when the trade is in a favorable regime state. As a result, 4/5 exits occur in RANGE at adverse prices.

**Secondary:** Even the single TREND-exit trade (Trade 3) ended negative, suggesting the channel exit does not reliably capture a move in the trade direction within the hold window. Entry and exit prices are both determined mechanically without regime-state anchoring.

**Tertiary (uncertain, not derivable from existing artifacts):** Entry may be systematically late (breaking out after the TREND segment is already mature) or the channel exit may trigger too late after the trend has reversed. Without mark-to-market data, the precise timing of adverse excursion cannot be assessed.

---

## What Is Proven

- **All 5 BUY signals fired in TREND** (regime_id=0 at `signals_emitted=1`). Entry filter is regime-aligned and correctly restricts entries to TREND.
- **Regime flips during hold are common** (3-13 per trade, 42 total across 5 trades, avg 8.4).
- **The exit mechanism is regime-unaware** -- it fires based on a mechanical channel condition, not the current regime state.
- **4/5 trades exited in RANGE** at adverse prices (total -0.0105R across 4 RANGE exits).
- **Even the TREND-exit trade lost** (-0.00042R), ruling out a simple "exit in TREND = profitable" hypothesis.
- **All findings are derived from existing run_005 artifacts.** No new runs, no parameter changes, no strategy modifications.

---

## What Is Not Proven

- **Whether entry timing is systematically late.** The backtest enters at the signal candle; mark-to-market data showing price trajectory during TREND segments is unavailable.
- **Whether the channel exit could be profitable with different parameters.** This would require parameter optimization -- FORBIDDEN scope.
- **Whether the failure is dataset-specific.** Only one dataset (7,575 MEXC BTCUSDT 1m candles) was tested. A different regime distribution could produce different results. Running a different dataset would require a new controlled-track run -- FORBIDDEN scope.
- **Whether a regime-aware exit (exit-on-regime-flip) would improve PnL.** This would require strategy logic change -- FORBIDDEN scope.
- **Max Adverse Excursion (MAE) / Max Favorable Excursion (MFE).** The trade_lifecycle does not capture intra-trade MTM. Cannot determine if any trade was ever in-the-money.
- **Statistical significance.** 5 trades is too small a sample for statistical inference. However, the pattern is mechanically consistent (regime flips exploit the gap between TREND-only entry and regime-unaware exit).

---

## Recommendation

### PARK primary_breakout_v1

**Rationale:** The diagnosis reveals a structural failure mode: regime instability (3-13 flips per trade, TREND median ~30 min, hold 76-287 min) exposes a regime-unaware channel exit to systematically adverse pricing. Addressing this failure mode requires one or more of:

1. **Parameter tuning** (adjust channel width, exit timing, entry threshold) -- FORBIDDEN
2. **Strategy logic change** (regime-aware exit, trailing stop, exit-on-flip) -- FORBIDDEN
3. **Different market dataset** (more stable regimes, longer TREND segments) -- would require new controlled-lab run, FORBIDDEN
4. **Strategy redesign exceeding bounded diagnosis scope** -- FORBIDDEN

None of these options are permitted within the bounded diagnosis scope defined by [#3181](https://github.com/jannekbuengener/Claire_de_Binare/issues/3181).

**No further bounded investigation is recommended.** The evidence is sufficient for the diagnosis to be conclusive: the strategy exhibits regime-decay-induced losses that cannot be addressed without parameter or logic changes.

---

## Park Boundary

primary_breakout_v1 strategy development is **PARKED** until one of the following conditions is met:

1. New evidence from a different source (paper phase, calibration data, different dataset) justifies revisit.
2. A governance decision explicitly lifts the PARK status and authorizes parameter optimization or strategy logic changes.
3. A fundamentally different exit mechanism is designed that does not inherit the regime-instability vulnerability of the current channel exit.

While parked:
- No new controlled-lab runs for primary_breakout_v1.
- No parameter optimization. No strategy logic changes.
- No promotion claims. No Product-Complete claims.
- LR remains NO-GO.

---

## Safety / LR Boundaries

| Boundary | State |
|----------|-------|
| LR status | **NO-GO** |
| This is diagnosis only | **Yes** |
| No parameter optimization was performed | **Yes** |
| No strategy behavior was changed | **Yes** |
| No promotion | **Yes** |
| No Product-Complete | **Yes** |
| No natural_paper_evidence | **Yes** |
| No Section 5.2.4 clearance | **Yes** |
| No Live-Go / Paper-Go / Echtgeld-Go | **Yes** |
| #1905 remains CLOSED/PARKED | **Yes** |
| #3087 remains CLOSED | **Yes** |
| No run_006 | **Yes** |
| No new controlled_lab evidence | **Yes** |
| No code changes | **Yes** |

---

## References

- [#3181](https://github.com/jannekbuengener/Claire_de_Binare/issues/3181) — ARVP post-run_005 decision
- [#3183](https://github.com/jannekbuengener/Claire_de_Binare/issues/3183) — this diagnosis issue
- [#1900](https://github.com/jannekbuengener/Claire_de_Binare/issues/1900) — ARVP parent epic
- [PR #3182](https://github.com/jannekbuengener/Claire_de_Binare/pull/3182) — decision doc merge (`d8fe5d49`)
- `artifacts/controlled_lab_evidence/run_005/trade_lifecycle.json`
- `artifacts/controlled_lab_evidence/run_005/trace.json`
- `artifacts/controlled_lab_evidence/run_005/gate_trace.jsonl`
- `artifacts/controlled_lab_evidence/run_005/arvp_regime_scorecard.json`
- `artifacts/controlled_lab_evidence/run_005/evidence_context.md`
- `docs/evidence/arvp_post_run_005_primary_breakout_v1_decision_3181.md`
- `knowledge/governance/ARVP_PRODUCT_INTENT.md`
- `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
