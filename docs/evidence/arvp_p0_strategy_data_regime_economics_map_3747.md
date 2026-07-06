# ARVP P0 Strategy — Data, Regime & Execution-Economics Map (#3747)

Status Class: Discovery evidence (data/economics prerequisites, no promotion)
Issue: [#3747](https://github.com/jannekbuengener/Claire_de_Binare/issues/3747)
Parent: [#1900](https://github.com/jannekbuengener/Claire_de_Binare/issues/1900)
Prerequisite: [#3746](https://github.com/jannekbuengener/Claire_de_Binare/issues/3746) CLOSED — PR [#3749](https://github.com/jannekbuengener/Claire_de_Binare/pull/3749) @ `0a3b94c`
Related: [#3742](https://github.com/jannekbuengener/Claire_de_Binare/issues/3742), [#3748](https://github.com/jannekbuengener/Claire_de_Binare/issues/3748), [#3035](https://github.com/jannekbuengener/Claire_de_Binare/issues/3035) (CLOSED), [#3039](https://github.com/jannekbuengener/Claire_de_Binare/issues/3039) (CLOSED), [#2985](https://github.com/jannekbuengener/Claire_de_Binare/issues/2985), [#3086](https://github.com/jannekbuengener/Claire_de_Binare/issues/3086) (OPEN)
Live-Readiness: **NO-GO**
Echtgeld: **not authorized**
Board stage: `trade-capable` (orthogonal to LR; **not** Live-Go)

---

## 1. Source / Provenance

| Field | Value |
|-------|-------|
| Primary source | `docs/evidence/arvp_strategy_longlist_deep_research_3746.md` (#3746 longlist) |
| Candidate contract | `docs/strategy/CDB_PROFITABILITY_CANDIDATE_CONTRACT_V1.md` (#3034 CLOSED) |
| Dataset quality canon | `docs/strategy/CDB_PROFITABILITY_DATASET_QUALITY_GATE_V1.md` (#3035 CLOSED) |
| Execution economics canon | `docs/strategy/CDB_PROFITABILITY_EXECUTION_ECONOMICS_V1.md` (#3039 CLOSED) |
| Same-venue policy | `docs/evidence/mexc_same_venue_data_quality_policy_3091.md` |
| Same-venue acquisition gap | `docs/evidence/arvp_mexc_same_venue_acquisition_3086.md` (#3086 OPEN) |
| Window bank / regime_segments | [#3742](https://github.com/jannekbuengener/Claire_de_Binare/issues/3742) — **not solved by this slice** |
| Pack-A spec (downstream) | [#3748](https://github.com/jannekbuengener/Claire_de_Binare/issues/3748) — **not written here** |
| P0 candidate count | **10** (Ranks 1–10 from #3746) |
| Default test universe | BTCUSDT / MEXC / long-only / 1m (research default from #3746) |

**Mapping rule:** This document **references** #3035 and #3039 canon surfaces. It does **not** duplicate their schemas, verdict enums, or fail-closed rules.

---

## 2. Brain Evidence

```text
brain_source: repo-only
brain_status: not-used
tools_or_queries:
  - cdb_context_briefing (task_id=cdb-briefing-3747-p0-data-economics-map) — attempted; task_id required
  - git fetch origin --prune; git switch -c docs/3747-arvp-p0-data-economics-map origin/main
  - gh issue view 3747, 3746, 1900, 3742, 3748, 3035, 3039, 2985
  - gh pr view 3749
  - read: docs/evidence/arvp_strategy_longlist_deep_research_3746.md
  - read: CDB_PROFITABILITY_DATASET_QUALITY_GATE_V1.md, CDB_PROFITABILITY_EXECUTION_ECONOMICS_V1.md
  - read: mexc_same_venue_data_quality_policy_3091.md, arvp_mexc_same_venue_acquisition_3086.md
  - rg dedupe scan across docs/knowledge for existing P0 data/economics matrix
records_or_results:
  - context_brain_attempted=true; context_brain_used=false; context_available=false
  - repo_fallback_reason=insufficient_evidence; records_found=none
  - origin/main @ 0a3b94ced53ed81c4cde86118fed1410f078256d (includes #3749)
  - #3747 OPEN; no existing docs/evidence/*3747* prior to this slice
repo_crosscheck:
  - docs/evidence/arvp_strategy_longlist_deep_research_3746.md (P0 ranks 1–10)
  - docs/evidence/arvp_exit_regime_decay_diagnosis_3183.md (primary_breakout_v1 PARK)
  - docs/evidence/arvp_window_bank_inventory_3212.md (regime_segments unavailable)
  - docs/strategy/CDB_PROFITABILITY_SCENARIO_PACK_LIBRARY_V1.md (#3038 stress domains)
impact_on_plan:
  - P0 matrix built from #3746 longlist + repo canon crosswalk; no invented DB claims.
  - Same-venue friction classified as central hard blocker for honest net economics.
  - #3742 boundary preserved: natural-paper / regime_segments not claimed solved.
  - #3748 Pack-A spec remains downstream; this slice supplies DATA dependency only.
limitations:
  - No SurrealDB/context-brain records used.
  - No runtime DB inspection in this slice; candle-grade claims cite committed evidence docs only.
  - Spread/liquidity/fill/reject time series not repo-backed for historical windows beyond pilot paper compare.
  - Matrix does not authorize ARVP runs, implementation, or candidate promotion.
context_brain_attempted: true
context_brain_used: false
context_available: false
repo_fallback_used: true
repo_fallback_reason: insufficient_evidence
context_tool_status: available
context_trust_level: none
records_found: none
```

---

## 3. Management Summary

**Kernentscheidung:**

1. **Welle 1 (Spec/Shape-Backtest):** Alle 10 P0-Kandidaten können auf **MEXC same-venue 1m OHLCV** (plus abgeleitete 5m-Aggregate wo nötig) **deterministische Signal-/Entry-Shape-Tests** und Szenario-Stress **formulieren** — vorausgesetzt ein Dataset passiert den [#3035](https://github.com/jannekbuengener/Claire_de_Binare/issues/3035) Quality Gate (`PASS` oder dokumentiertes `WARNING`).
2. **Welle 1 (ehrliche Netto-Ökonomie):** **Nicht beweisbar** ohne same-venue Spread-, Liquiditäts-, Fill-Rate- und Rejection-Evidenz plus [#3039](https://github.com/jannekbuengener/Claire_de_Binare/issues/3039) Execution-Economics-Assessment mit `ranking_ready=false` bis Lücken geschlossen.
3. **Top-Datenlücke:** Historische **same-venue** Friktionsreihen (Spread, Liquidität, Fill-Rate, Rejections) — nicht durch reines 1m-OHLCV ersetzbar. #3086 bleibt OPEN; #3028-Fenster nutzt `venue_mismatch=true` (Binance).
4. **Regime-Coverage:** P0-Trend/Breakout-Kern braucht **Trend/Expansion**-Segmente; Z-Score MR braucht **Range-only**-Gates. Ohne #3742 `regime_segments` auf natural-paper-Fenstern bleibt **regime-segmentierte ARVP-Interpretation blockiert** (Phase-A §5.2.4).
5. **`primary_breakout_v1`:** Repo-**PARKED** (#3183) — bleibt **Referenzanker** für vergleichbares ARVP-Design, **kein** Rescue-/Promotionskandidat.
6. **LR NO-GO / kein Live-Go / kein Echtgeld-Go** — diese Matrix autorisiert keine Kapital- oder LR-Freigabe.

**Explizite Abgrenzung zu Nachbar-Slices:**

| Slice | Rolle | Status in diesem Doc |
|-------|-------|----------------------|
| #3746 Longlist | P0-Kandidatenliste, Klassen, Top-3/Next-5 | **Input** (nicht dupliziert) |
| #3747 (dieses Doc) | Daten-, Regime-, Economics-Bedarf je P0 | **Delivered here** |
| #3748 Pack-A | Breakout-Baseline-Testpaket-Spec | **Downstream** — verweist auf diese Matrix |
| #3742 | natural-paper window bank + `regime_segments` | **Parallel** — weiter nötig |
| #3035 | Dataset Quality Gate v1 | **Canon-Referenz** — nicht neu geschrieben |
| #3039 | Execution Economics v1 | **Canon-Referenz** — nicht neu geschrieben |

---

## 4. P0 Candidate Matrix (Per-Candidate Analysis)

Lesart: **ARVP testability** = ob ein ehrlicher ARVP-Spec/Run-Pfad existiert, nicht ob Promotion gerechtfertigt ist.

| # | Candidate | strategy_family | ARVP testability (wave 1) | minimum dataset | nice-to-have dataset | required TF | derived TF needs | regime coverage needs | execution economics needs | same-venue dep. | spread/liq/fill/reject dep. | 1m OHLCV enough wave 1? | blocks honest economics | testable now without lying | waits for #3742 / later data | promotion boundary |
|---|-----------|-----------------|---------------------------|-----------------|----------------------|-------------|------------------|----------------------|---------------------------|-----------------|------------------------------|-------------------------|-------------------------|----------------------------|------------------------------|-------------------|
| 1 | `primary_breakout_v1` | Breakout | **Shape yes** / **Economics no** (PARKED) | MEXC 1m OHLCV; #3035 PASS | 5m derived; paper windows | 1m | optional 5m trend context | Trend, Expansion | fees, slippage, rejects; #3039 assessment | **Yes** | **High** — breakout entries friction-sensitive | **Partial** — signal shape only | Missing same-venue friction series; PARKED tri-loop | Deterministic replay shape + scenario packs (#3038) with declared assumptions | `regime_segments` for segmented scorecards; fresh paper if #3742 requires | **PARKED** — reference anchor only; no rescue (#3183) |
| 2 | Donchian Breakout | Breakout | **Shape yes** / **Economics partial** | MEXC 1m OHLCV; #3035 PASS | 5m for HTF sanity checks | 1m | none required | Trend | baseline + pessimistic execution (#3038/#3039) | **Yes** | **Medium** — fewer trades than MR | **Partial** | Net PnL without measured spread/slippage is assumption-only | Spec + offline replay with economics model fixtures | Regime scorecards need #3742 segments | New candidate; compare to PB1 benchmark only |
| 3 | Breakout + Trend Filter | Hybrid | **Shape yes** / **Economics partial** | 1m OHLCV + 5m derived | Regime labels if available | 1m | **5m derived** (trend gate) | Trend (gated) | as breakout base + filter turnover cost | **Yes** | **Medium** | **Partial** | Filter may reduce trades but not prove net edge | Shape/backtest with derived 5m; cost scenarios declared | Regime labels on paper windows (#3742) | Filter definition frozen in spec; no PB1 promotion |
| 4 | Breakout + Volatility Filter | Hybrid | **Shape yes** / **Economics partial** | 1m OHLCV (ATR/bandwidth from 1m) | Vol shock scenario inputs | 1m | none required | Trend, structured vol | high-vol slippage scenarios (#3038) | **Yes** | **Medium–High** in vol shocks | **Partial** | Vol-filter does not substitute cost evidence | Scenario stress with pessimistic_execution / low_liquidity packs | Regime segments for vol regimes (#3742) | Overfiltering risk — spec-only here |
| 5 | 1m Entry + 5m Trend Filter | Multi-TF | **Shape yes** / **Economics partial** | 1m OHLCV + **5m derived** | 15m optional later | 1m | **5m derived** mandatory | Trend | entry-level slippage; MTF sync risk | **Yes** | **Medium** | **Partial** | MTF aggregation lookahead must be ruled out in spec | Derived 5m from same 1m feed; deterministic aggregation tests | Paper windows with regime_segments (#3742) | No HTF lookahead in wave 1 |
| 6 | EMA Trend Filter | Trend-Following | **Shape yes** / **Economics partial** | 1m OHLCV | 5m EMA context optional | 1m | none required | Trend | standard fee/slippage model (#3039) | **Yes** | **Low–Medium** | **Partial** | Whipsaw costs need friction evidence | Overlay spec + replay; EMA length fixed | Regime trend segments (#3742) | Overlay only — not standalone alpha claim |
| 7 | HH/HL Continuation | Trend-Following | **Shape yes** / **Economics partial** | 1m OHLCV | Structure swing labels | 1m | none required | Trend (structure) | delay/retest slippage | **Yes** | **Medium** | **Partial** | Structure edge ≠ net edge without costs | Structure detection tests on 1m | Regime trend segments (#3742) | Structure rules frozen; no promotion |
| 8 | Volatility Breakout | Breakout/Volatility | **Shape yes** / **Economics partial** | 1m OHLCV | vol expansion metrics | 1m | none required | Trend, Expansion | aggressive slippage in shocks (#3038) | **Yes** | **High** in expansion bars | **Partial** | Jump-chasing inflates gross without friction | Vol-breakout triggers + stress packs | Expansion vs chaos segments (#3742) | Distinct from #4 filter variant |
| 9 | Z-Score Reversion (Range-only) | Mean Reversion | **Shape conditional** / **Economics no** without spread | 1m OHLCV + **range regime gate** | **Spread series strongly needed** | 1m | none required | **Range only** (hard gate) | spread + slippage **mandatory** (#3039 FAIL without) | **Yes** | **Very High** | **No** for honest economics | MR net dominated by spread; candle-only lies | Range-gate logic testable; economics must stay `ranking_ready=false` | Range regime_segments (#3742); spread data (#3086+) | **Second-wave economics** until friction evidence |
| 10 | High-Volatility Avoidance (overlay) | Volatility/Filter | **Overlay yes** / **Economics N/A** (filter) | 1m OHLCV (ATR/bandwidth) | calibrated vol thresholds | 1m | none required | Low/Normal vol (blocks high vol) | compares trade-frequency cost savings | **Yes** | **Low** direct; **Medium** indirect | **Yes** for overlay logic | Cannot prove alpha — only activity compression | Idle/block decisions testable vs baseline packs | Vol regime segments (#3742) | Overlay — pairs with breakout/trend packs (#3748 D) |

---

## 5. Dataset Requirement Matrix

Rows = data classes. Columns = P0 candidates.  
**M** = mandatory for wave-1 honest test, **R** = recommended, **O** = optional, **—** = not needed wave 1.

| Data class | PB1 | Donchian | Bo+Trend | Bo+Vol | 1m+5m | EMA | HH/HL | Vol Bo | Z-Score MR | HVC Avoid |
|------------|:---:|:--------:|:--------:|:------:|:-----:|:---:|:-----:|:------:|:----------:|:---------:|
| **1m OHLCV (MEXC same-venue)** | M | M | M | M | M | M | M | M | M | M |
| **5m derived (from 1m)** | R | — | M | — | M | R | — | — | — | — |
| **15m derived** | O | — | O | — | O | O | — | — | — | — |
| **Tick / trades** | O | — | — | — | O | — | — | O | R | — |
| **Orderbook / depth** | O | — | — | — | — | — | — | O | R | — |
| **Funding** | — | — | — | — | — | — | — | — | — | — |
| **Spread (historical, same-venue)** | R | R | R | R | R | R | R | R | **M** | O |
| **Liquidity proxy (volume, depth)** | R | R | R | R | R | R | R | R | **M** | R |
| **Fee schedule (MEXC)** | M | M | M | M | M | M | M | M | M | — |
| **Paper reference windows** | R | R | R | R | R | R | R | R | R | R |
| **#3035 Dataset Quality Report** | M | M | M | M | M | M | M | M | M | M |

**Funding:** Spot BTCUSDT P0 scope — funding not required wave 1.

**Tick/Orderbook:** Not required for wave-1 **shape** tests on breakout/trend core; increasingly important for MR and microstructure-sensitive interpretations (Z-Score).

---

## 6. Regime Coverage Matrix

| Regime dimension | P0 candidates needing it | Minimum for wave 1 | Blocked without #3742? | Notes |
|------------------|--------------------------|--------------------|------------------------|-------|
| **Trend** | PB1, Donchian, Bo+Trend, Bo+Vol, 1m+5m, EMA, HH/HL, Vol Bo | 1m price structure + optional `cdb_regime` labels in replay | **Partial** — offline regime from candles possible; **natural-paper `regime_segments` blocked** | #3742 supplies §5.2.4 gate segments |
| **Expansion** | PB1, Vol Bo, Bo+Vol | Vol expansion metrics from 1m | Same as above | |
| **Range (hard gate)** | Z-Score MR | Range-only gate — misclassification = false MR | **Yes** for honest range MR on paper windows | Trend-Regime Gate (#3746 P1) is separate overlay |
| **Low/Normal vol (block high)** | HVC Avoidance | ATR/bandwidth from 1m | Overlay testable offline; paper segmented compare needs #3742 | Evidence compressor / idle logic |
| **Unknown / chop** | All (risk) | Document unknown-regime rate | #3742 for paper-side segmentation | Protective idle alignment |

**#3742 boundary (explicit):** This matrix **does not** claim `regime_segments` are populated on any natural-paper window. Per `docs/evidence/arvp_window_bank_inventory_3212.md`, current bank has `regime_segments` **unavailable**. Phase-A Product-Complete §5.2.4 remains **blocked** until #3742 (or successor) delivers at least one comparison-grade window with non-empty `regime_segments`.

---

## 7. Execution-Economics Matrix

Aligned to [#3039](https://github.com/jannekbuengener/Claire_de_Binare/issues/3039) / `CDB_PROFITABILITY_EXECUTION_ECONOMICS_V1.md`.  
Does **not** restate schema fields — maps **what P0 needs** vs **what exists**.

| Economics dimension | Wave-1 requirement | P0 applicability | Repo status | Blocker class |
|---------------------|-------------------|------------------|-------------|---------------|
| **Fees (MEXC schedule)** | Model in #3039 fixtures; bounded assumptions | All tradable P0 (1–9) | Canon + sample assessments exist (PB1/RMR/Momentum) | Quality — use declared model, not live fees |
| **Spread cost** | Measured or explicit FAIL/WARNING | All; **critical** for Z-Score MR | Tri-candidate assessments often `spread_cost=0.0` placeholder | **Hard blocker** for honest net ranking |
| **Slippage** | Scenario packs (#3038): baseline, pessimistic, delayed, low_liquidity | Breakout/trend core | Schema + `core/replay/scenario_packs.py` | Quality — declared assumptions OK for shape; not proof |
| **Liquidity / partial fills** | low_liquidity scenario | Vol Bo, Bo+Vol, MR | #3038 CLOSED | Later enhancement without same-venue liq series |
| **Fill-rate drift** | Replay-vs-paper compare | All with paper windows | Pilot window moderate certainty; #3028 venue_mismatch | **Hard blocker** for multi-window aggregate claims |
| **Rejections** | pessimistic_execution / reject modeling | Breakout entries | Scenario pack domain | Quality without historical reject series |
| **Latency / delay** | delayed_execution scenario | 1m+5m, HH/HL | #3038 | Not needed for offline shape |
| **Net return / ranking_ready** | #3039 assessment `ranking_ready=false` until complete | All | Canon explicit | **Mandatory fail-closed** |

**Central gap (same-venue friction evidence):**

| Evidence type | Why it blocks honest economics | Related issues |
|---------------|-------------------------------|----------------|
| Historical same-venue **spread** series | MR and tight breakout edges are spread-dominated | #3086 OPEN, #3747 |
| **Liquidity** / depth proxies | low_liquidity scenario calibration unanchored | #3086 OPEN |
| **Fill-rate** on same-venue windows | Only pilot MEXC window is clean; #3028 is Binance | #3086, #3742 |
| **Rejections** time series | Cannot validate pessimistic_execution against reality | Later data work |

---

## 8. Blocker Classification

| ID | Blocker | Class | Affects P0 | Mitigation path |
|----|---------|-------|------------|-----------------|
| B1 | Same-venue spread/liquidity/fill/reject historical evidence | **Hard blocker** (honest net economics) | All; critical 9 | #3086 execute path; dedicated acquisition follow-up if needed |
| B2 | `regime_segments` unavailable on natural-paper windows | **Hard blocker** (Phase-A §5.2.4 / segmented ARVP) | All regime-segmented claims | #3742 readonly extraction or runtime-GO fresh paper |
| B3 | #3028 `venue_mismatch=true` (Binance candles) | **Quality blocker** | Multi-window calibration certainty | MEXC capture for future windows (#3086) |
| B4 | #3035 report not run per dataset window | **Quality blocker** | All runs | Emit dataset quality report before trust |
| B5 | #3039 `ranking_ready=false` / incomplete cost attribution | **Quality blocker** (by design) | All ranking | Complete economics assessment per candidate |
| B6 | Z-Score MR without spread data | **Hard blocker** for MR economics | 9 | Defer MR economics to wave 2; shape-only with explicit limitations |
| B7 | 5m derived aggregation lookahead | **Quality blocker** | 3, 5 | Deterministic aggregation contract in spec (#3748) |
| B8 | PB1 PARK / tri-loop FULL_STOP | **Promotion boundary** (not data) | 1 | Use as benchmark reference only |

**Wave-1 decision:**

| Question | Answer |
|----------|--------|
| Can 1m OHLCV support first-wave **spec / shape / deterministic replay**? | **Yes**, with #3035 quality gate and declared #3038/#3039 assumptions |
| Can 1m OHLCV **prove economic truth** (net edge, ranking, promotion)? | **No** — requires B1 resolved + #3039 complete assessments |
| What can be tested now **without lying**? | Signal logic, trade count sensitivity, scenario stress **with** `ranking_ready=false` and explicit limitation banners |
| What must wait? | Regime-segmented paper truth (#3742); MR net economics (B1+B6); multi-window same-venue calibration |

---

## 9. Mapping to #3035 (Dataset Quality Gate)

**Canon:** `docs/strategy/CDB_PROFITABILITY_DATASET_QUALITY_GATE_V1.md`

| #3035 concept | How P0 uses it |
|---------------|----------------|
| coverage / missing / duplicate / ordering checks | **Mandatory** before any P0 ARVP or backtest trust |
| verdict `PASS` / `WARNING` / `FAIL` / `BLOCKED` | P0 wave-1: require `PASS` or documented `WARNING` with limitations |
| dataset fingerprint | One fingerprint per P0 pack run (#3748 should pin same dataset) |
| relationship to `dataset_provider.py` | Gate reports quality; provider enforces transport invariants — **complementary** |
| #3031 data backfill | Out of scope — gate defines standard, not recovery |

**Non-duplication:** P0 matrix does **not** redefine check enums or schema JSON. Consumers emit `profitability_dataset_quality_report.v1` per window.

---

## 10. Mapping to #3039 (Execution Economics v1)

**Canon:** `docs/strategy/CDB_PROFITABILITY_EXECUTION_ECONOMICS_V1.md`

| #3039 concept | How P0 uses it |
|---------------|----------------|
| Economics model v1 | Fee/spread/slippage assumptions for each P0 candidate pack |
| Economics assessment v1 | Per-candidate gross→net with `ranking_ready` flag |
| `ranking_ready=false` | **Default** for wave 1 until B1 friction evidence exists |
| fail-closed rules | Missing slippage assumptions → `FAIL`; missing gross → `BLOCKED` |
| dependency on #3035 | No economics trust on `FAIL`/`BLOCKED` dataset quality |
| Strategy League Table (#3040) | **Out of scope** — no gross-only ranking |

**Non-duplication:** P0 matrix does **not** restate model/assessment JSON schemas or example fixtures.

---

## 11. `primary_breakout_v1` — PARKED Reference Anchor

| Field | Value |
|-------|-------|
| Repo status | **PARKED** (`docs/evidence/arvp_exit_regime_decay_diagnosis_3183.md`) |
| Tri-loop | FULL_STOP on BTCUSDT/MEXC/1m long-only (#3210/#3383) |
| Role in P0 matrix | **Reference anchor** for comparative ARVP design (Top-3 #1 in research) |
| Wave-1 use | Spec parity, scenario pack alignment, replay shape — **not** promotion/rescue |
| Data needs | Same as Donchian/breakout family — no exemption from B1/B2 |

---

## 12. Dependency Notes for Downstream Issues

### #3748 (Pack-A spec)

Pack-A operational minimum (Top-3 breakout family) should:

- Pin **one** MEXC same-venue 1m dataset with #3035 report
- Declare #3038 scenario packs + #3039 economics model references
- State `ranking_ready=false` until B1 closed
- Treat PB1 as PARKED reference, not promotion target
- **Not** duplicate this matrix — link here for DATA prerequisites

### #3742 (window bank / regime_segments)

Parallel track. P0 ARVP can proceed on **offline** regime derivation for spec work; **natural-paper regime-segmented scorecards** and Phase-A §5.2.4 remain blocked until #3742 delivers.

### #3086 (same-venue acquisition)

Execute blocker for historical windows beyond public klines retention. Unblocks B1 partially for **future** windows; does not retroactively fix #3028 venue mismatch.

---

## 13. Safety and Non-Goals

- **LR NO-GO** — `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
- **Kein Live-Go, kein Echtgeld-Go**
- **Board `trade-capable` ≠ Live-Go**
- Keine Strategie-Implementierung / kein Signal-Code
- Kein Backtest / kein ARVP-Run in diesem Slice
- Keine Candidate-Promotion
- Kein Gearbox (#205) / Multi-Asset (#211)
- Kein Duplikat von #3035 / #3039 Canon
- Kein Pack-A Testplan (#3748)
- Keine `regime_segments`-Lösung (#3742)
- Keine Renditeversprechen

---

## 14. Restunsicherheiten

1. Exakte historische Spread-/Reject-Reihen für MEXC BTCUSDT 1m sind **nicht** repo-backed für alle geplanten Fenster — Priorisierung von Akquisitionsfenstern bleibt Execute-Entscheidung (#3086+).
2. `cdb_regime` Service-Labels vs. paper-side `regime_segments` können divergieren — segmented compare braucht #3742-Alignment.
3. 5m-Ableitung aus 1m ist technisch trivial, aber **Lookahead-Policy** muss in #3748-Spec festgezurrt werden.
4. Z-Score MR Priorität in P0 (Next-5) ist research-gestützt, aber **economics-hart** erst nach Spread-Evidenz — ggf. Pack-Reihenfolge A→D→B vor C beibehalten (#3746 §10).

---

*Evidence created 2026-07-06 for #3747. Primary input: #3746 longlist + #3035/#3039 canon crosswalk.*
