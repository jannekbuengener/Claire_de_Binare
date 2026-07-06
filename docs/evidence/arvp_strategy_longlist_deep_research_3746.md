# ARVP Strategy Longlist — Deep Research Preservation (#3746)

Status Class: Discovery evidence (strategy taxonomy, no promotion)
Issue: [#3746](https://github.com/jannekbuengener/Claire_de_Binare/issues/3746)
Parent: [#1900](https://github.com/jannekbuengener/Claire_de_Binare/issues/1900)
Related: [#3742](https://github.com/jannekbuengener/Claire_de_Binare/issues/3742), [#3747](https://github.com/jannekbuengener/Claire_de_Binare/issues/3747), [#3748](https://github.com/jannekbuengener/Claire_de_Binare/issues/3748), [#2985](https://github.com/jannekbuengener/Claire_de_Binare/issues/2985), [#3034](https://github.com/jannekbuengener/Claire_de_Binare/issues/3034) (CLOSED), [#205](https://github.com/jannekbuengener/Claire_de_Binare/issues/205), [#211](https://github.com/jannekbuengener/Claire_de_Binare/issues/211)
Live-Readiness: **NO-GO**
Echtgeld: **not authorized**
Board stage: `trade-capable` (orthogonal to LR; **not** Live-Go)

---

## 1. Source / Provenance

| Field | Value |
|-------|-------|
| Primary source | Deep Research export: `C:\Users\janne\Desktop\ARVP-Strategielonglist für Claire de Binare.md` |
| Transfer date | 2026-07-06 |
| Transfer method | Curated repo evidence (source file **not** copied into repo) |
| Issue anchor | #3746 |
| Parent anchor | #1900 (ARVP north-star) |
| Candidate count | **32** (full table preserved below) |
| Renditeversprechen | **None** — this is an ARVP test-ordering artifact, not a performance ranking |

**Repo crosscheck at transfer time:**

- `primary_breakout_v1` remains **PARKED** per `docs/evidence/arvp_exit_regime_decay_diagnosis_3183.md` — listed here as historical CDB anchor and benchmark reference, **not** as a promotion candidate.
- Tri-candidate loop (`primary_breakout_v1`, `range_mean_reversion_v1`, `momentum_capture_v1`) is **FULL_STOP** on BTCUSDT/MEXC/1m long-only per #3210/#3211/#3383.
- Window-bank / `regime_segments` work remains **separate** under #3742 — this longlist does **not** replace it.

---

## 2. Brain Evidence

```text
brain_source: repo-only
brain_status: not-used
tools_or_queries:
  - cdb_context_briefing (task_id=cdb-briefing-3746-strategy-longlist)
  - git fetch origin --prune; git status -sb; git rev-parse HEAD; git rev-parse origin/main
  - gh issue view 3746, 1900, 3742, 3747, 3748, 2985
  - read: Desktop source ARVP-Strategielonglist für Claire de Binare.md
  - rg dedupe scan across docs/knowledge for existing longlist
records_or_results:
  - context_brain_attempted=true; context_brain_used=false; context_available=false
  - repo_fallback_reason=insufficient_evidence; records_found=none
  - HEAD == origin/main == ff8633fe787c4812007f32094f6769b65fce31bc
  - #3746 OPEN; #1900 OPEN; no existing docs/evidence/*3746* or arvp_strategy_longlist*
repo_crosscheck:
  - docs/evidence/arvp_exit_regime_decay_diagnosis_3183.md (PB1 PARK)
  - docs/evidence/arvp_window_bank_expansion_regime_segments_3343.md (#3742 lineage)
  - docs/evidence/arvp_roadmap_reconcile_after_primary_breakout_park_2985_1900.md
  - docs/roadmaps/ARVP_TO_LIVE_GO_ROADMAP_2026-06.md
impact_on_plan:
  - Full 32-candidate transfer proceeds from Desktop source (available).
  - PB1 PARK boundary preserved in management summary; longlist ordering unchanged from research.
  - No DB-backed strategy claims; GitHub + repo evidence govern current PARK/FULL_STOP truth.
limitations:
  - No SurrealDB/context-brain records used.
  - Deep Research external citations stripped; repo-only governance crosscheck applied.
  - Longlist does not authorize implementation, ARVP runs, or candidate promotion.
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

**Kurzentscheidung (aus Deep Research, repo-aligned):**

1. **Erste ARVP-Welle = enge Breakout-/Trend-Familie** auf einem liquiden Symbol mit 1m-OHLCV — nicht Strategie-Zoo, nicht Multi-Symbol-Routing.
2. **Top-3 für erste Tests:** `primary_breakout_v1` (Referenzanker, aktuell PARKED), Donchian Breakout, Breakout + Trend Filter.
3. **Next-5 danach:** Breakout + Volatility Filter, 1m Entry + 5m Trend Filter, EMA Trend Filter, Higher-High/Higher-Low Continuation, Z-Score Reversion (range-only).
4. **Regime-/Risk-Filter sind Pflicht-Overlays**, nicht Beiwerk — passt zu CDB Protective Idle und ARVP Economics-Härte.
5. **Mean Reversion = zweite Welle**, streng regime-begrenzt (range-only, kostenhart).
6. **Nicht zuerst:** Multi-Symbol-Rotation, Selector/Router (#205 Gearbox), Support/Resistance-Breakouts, Liquidity-Sweep-Mikrostruktur.
7. **Explizite Reihenfolge:** Breakout/Trend-Kern **vor** Gearbox [#205](https://github.com/jannekbuengener/Claire_de_Binare/issues/205) und Multi-Asset [#211](https://github.com/jannekbuengener/Claire_de_Binare/issues/211).
8. **Wichtigste Datenlücke:** same-venue Spread, Liquidität, Fill-Rate, Rejections — Details gehören nach #3747, nicht hierher.
9. **LR NO-GO / kein Live-Go / kein Echtgeld-Go** — diese Longlist autorisiert keine Kapital- oder LR-Freigabe.

**Default-Testannahme:** long-only zuerst auf BTCUSDT/MEXC/1m, konsistent mit öffentlich sichtbarer CDB-Schleife.

**Empfohlene ARVP-Paket-Reihenfolge (Research-Synthese):** A (Breakout-Basis) → D (Regime/Filter-Overlays) → B (Trend) → F (Hybrid) → C (Mean Reversion) → E (Multi-Symbol).

---

## 4. Explicit Boundaries

| Boundary | Decision |
|----------|----------|
| #3742 window bank / `regime_segments` | **Separate slice.** Longlist ersetzt #3742 nicht; #3742 bleibt Phase-A1/A4-Vorläufer. |
| #3747 data/economics detail | Out of scope here; verweisen wenn Spread/Liq/Fill-Gaps vertieft werden. |
| #3748 Pack-A execution/spec | Out of scope here; Breakout-Basispaket-Specs dort. |
| #205 Strategy Gearbox | **Bewusst nicht erste Welle.** Erst Breakout/Trend-Kern unter ehrlichen Kosten beweisen. |
| #211 Multi-Asset | **Downstream.** Erst Single-Symbol-Benchmarks stabil. |
| #3034 Candidate Contract v1 | **CLOSED** — kein Duplikat-Contract in diesem Slice. |
| Candidate promotion | **Forbidden** — Longlist ist Discovery/Ordering, keine Freigabe. |
| `primary_breakout_v1` rescue | **Forbidden** — PARK aus #3183 bleibt; PB1 nur als Referenz/Benchmark. |

---

## 5. Top-3 and Next-5 (Explicit)

### Top-3 — erste ARVP-Testfamilie

| Rank | Strategy | Klasse | Priorität | Markierung |
|------|----------|--------|-----------|------------|
| 1 | `primary_breakout_v1` | Breakout | P0 | **TOP-3 #1** (Referenzanker; repo: PARKED) |
| 2 | Donchian Breakout | Breakout | P0 | **TOP-3 #2** |
| 3 | Breakout + Trend Filter | Hybrid | P0 | **TOP-3 #3** |

### Next-5 — unmittelbar danach

| Rank | Strategy | Klasse | Priorität | Markierung |
|------|----------|--------|-----------|------------|
| 4 | Breakout + Volatility Filter | Hybrid | P0 | **NEXT-5 #1** |
| 5 | 1m Entry + 5m Trend Filter | Multi-Timeframe | P0 | **NEXT-5 #2** |
| 6 | EMA Trend Filter | Trend-Following | P0 | **NEXT-5 #3** |
| 7 | Higher-High / Higher-Low Continuation | Trend-Following | P0 | **NEXT-5 #4** |
| 9 | Z-Score Reversion nur im Range-Regime | Mean Reversion | P0 | **NEXT-5 #5** |

---

## 6. Full 32-Candidate Table

Lesart: **Priorität** = ARVP-Testreihenfolge, keine Rendite-Rangliste. **Risiko** = Overfitting-/Implementierungs-/Interpretationsrisiko im CDB-Kontext.

| Rank | Strategie | Klasse | Kurzlogik | Datenbedarf | Regime-Fit | Risiko | Aufwand | ARVP-Fit | Priorität |
|-----:|-----------|--------|-----------|-------------|------------|--------|---------|----------|-----------|
| 1 | `primary_breakout_v1` | Breakout | Long-only Breakout über definierte Trigger; CDB-Anker | 1m OHLCV | Trend, geordnete Expansion | Mittel | Niedrig | Hoch | P0 |
| 2 | Donchian Breakout | Breakout | Einstieg bei X-Bar-Hoch/-Tief; wenig Freiheitsgrade | 1m OHLCV | Trend | Mittel | Niedrig | Hoch | P0 |
| 3 | Breakout + Trend Filter | Hybrid | Breakout nur bei sauberem übergeordneten Trend | 1m OHLCV, 5m derived | Trend | Mittel | Niedrig | Hoch | P0 |
| 4 | Breakout + Volatility Filter | Hybrid | Breakout nur bei „gesundem“ Vol-Regime | 1m OHLCV | Trend, strukturierte Vol | Mittel | Niedrig | Hoch | P0 |
| 5 | 1m Entry + 5m Trend Filter | Multi-Timeframe | Entry fein, Trend grob | 1m OHLCV, 5m derived | Trend | Mittel | Mittel | Hoch | P0 |
| 6 | EMA Trend Filter | Trend-Following | Nur Trades in EMA-Richtung; Trigger separat | 1m OHLCV | Trend | Niedrig-Mittel | Niedrig | Hoch | P0 |
| 7 | Higher-High / Higher-Low Continuation | Trend-Following | Trendfortsetzung bei sauberer Marktstruktur | 1m OHLCV | Trend | Mittel | Mittel | Hoch | P0 |
| 8 | Volatility Breakout | Breakout/Volatility | Einstieg bei Ausbruch plus Volatilitätsanstieg | 1m OHLCV | Trend, Expansion | Mittel | Niedrig | Hoch | P0 |
| 9 | Z-Score Reversion nur im Range-Regime | Mean Reversion | Rücklauf zum Mittelwert, range-only | 1m OHLCV | Range | Mittel-Hoch | Mittel | Hoch | P0 |
| 10 | High-Volatility Avoidance Strategy | Volatility/Filter | Nicht handeln bei chaotisch hoher ATR/Bandbreite | 1m OHLCV | Low/Normal Vol | Niedrig | Niedrig | Hoch | P0 |
| 11 | Moving Average Crossover | Trend-Following | Fast/Slow-Crossover als Baseline | 1m OHLCV | Trend | Mittel | Niedrig | Hoch | P1 |
| 12 | Higher Timeframe Bias + Lower Timeframe Trigger | Multi-Timeframe | HTF-Richtung, LTF-Auslösung | 1m OHLCV, 5m/15m derived | Trend | Mittel | Mittel | Hoch | P1 |
| 13 | 5m Breakout + 1m Execution Timing | Multi-Timeframe | Breakout auf 5m, Entry-Timing auf 1m | 1m OHLCV, 5m derived | Trend | Mittel | Mittel | Hoch | P1 |
| 14 | Breakout + Momentum Confirmation | Hybrid | Breakout mit zusätzlichem Momentum-Signal | 1m OHLCV, Vol optional | Trend | Mittel-Hoch | Mittel | Mittel-Hoch | P1 |
| 15 | ATR Expansion | Volatility | Trade nur bei ATR-Schub oder ATR-Schwelle | 1m OHLCV | Expansion | Mittel | Niedrig | Mittel-Hoch | P1 |
| 16 | Bollinger Band Squeeze | Volatility | Kompression erkennen, Ausbruch danach handeln | 1m OHLCV | Low Vol → Expansion | Mittel-Hoch | Mittel | Mittel-Hoch | P1 |
| 17 | Breakout after Compression | Volatility/Hybrid | Breakout nur nach enger Range/Kompression | 1m OHLCV | Low Vol → Trend | Mittel | Mittel | Mittel-Hoch | P1 |
| 18 | Bollinger Band Mean Reversion | Mean Reversion | Rücklauf von Band-Extremen zum Mittel | 1m OHLCV | Range, moderate Vol | Hoch | Niedrig-Mittel | Mittel | P1 |
| 19 | Range-Bound Reversion | Mean Reversion | Fade an Range-Rändern | 1m OHLCV | Range | Hoch | Mittel | Mittel | P1 |
| 20 | Trend-Regime only Gate | Regime-basiert | Trendstrategie nur im Trend-Regime | 1m OHLCV, Regime-Labels | Trend | Niedrig | Niedrig | Hoch | P1 |
| 21 | Range-Regime only Gate | Regime-basiert | Reversion nur im Range-Regime | 1m OHLCV, Regime-Labels | Range | Niedrig | Niedrig | Hoch | P1 |
| 22 | Volatility Throttle | Risk/Filter | Entry-Dichte bei hoher Vol reduzieren | 1m OHLCV | Alle, außer chaotisch | Niedrig | Niedrig | Hoch | P1 |
| 23 | Time-of-Day / Session Filter | Risk/Filter | Nur definierte Handelsfenster | 1m OHLCV, Session-Zeit | Intraday-Zeitfenster | Mittel | Niedrig | Mittel-Hoch | P1 |
| 24 | No-Trade-Zone bei hohem Spread / niedriger Liquidität | Risk/Filter | Kein Trade bei schlechten friktionalen Bedingungen | OHLCV + Spread/Liq-Proxies | Alle | Niedrig | Mittel | Mittel | P1 |
| 25 | ROC Momentum | Momentum | Einstieg bei Return-Speed-Schub | 1m OHLCV | Trend, Burst | Mittel-Hoch | Niedrig | Mittel | P2 |
| 26 | RSI Momentum | Momentum | Momentum statt Reversion mit RSI-Schwelle | 1m OHLCV | Trend/Burst | Hoch | Niedrig | Mittel | P2 |
| 27 | Opening Range Breakout | Breakout | Ausbruch aus definierter Eröffnungsrange | 1m OHLCV + Session-Anker | Eröffnungs-/Session-Schub | Hoch | Mittel | Mittel | P2 |
| 28 | BTC/ETH Regime Filter | Multi-Symbol/Regime | ETH/BTC-Zustand blockiert/aktiviert Hauptsymbol | Synchronized 1m OHLCV | Intermarket-Regime | Mittel-Hoch | Mittel | Mittel | P2 |
| 29 | Symbol Rotation / Relative Strength Ranking | Multi-Symbol | Rotiert in stärkste Kandidaten | Cross-symbol 1m OHLCV | Trend, Cross-Section | Hoch | Hoch | Niedrig-Mittel | P2 |
| 30 | Support/Resistance Breakout | Breakout | Breakout durch algorithmische Levels | 1m OHLCV | Trend nach Level-Tests | Hoch | Mittel-Hoch | Mittel | Parken |
| 31 | Liquidity Sweep Reversion | Mean Reversion/Microstructure | Sweep/Fakeout faden | OHLCV, ideal Trades/Spread/Book | Range, stop-run | Sehr hoch | Hoch | Niedrig | Parken |
| 32 | Regime-Switch Selector | Regime-basiert/Meta | Wählt Strategie dynamisch je Regime | Cross-strategy + cross-symbol | Alle | Sehr hoch | Hoch | Niedrig | Parken |

---

## 7. Strategy-Class Grouping

| Klasse | Kandidaten (Rank) | Erste-Welle-Relevanz |
|--------|-------------------|----------------------|
| **Breakout** | 1, 2, 8, 27, 30 | Kern — Ranks 1–2 Top-3; 8 P0; 27 P2; 30 Parken |
| **Trend** | 6, 7, 11 | Kern — 6–7 P0/Next-5; 11 P1 Baseline |
| **Momentum** | 14, 25, 26 | 14 P1 Hybrid; 25–26 P2 |
| **Mean Reversion** | 9, 18, 19, 31 | 9 P0/Next-5; 18–19 P1; 31 Parken |
| **Volatility** | 8, 10, 15, 16, 17 | 10 P0 Overlay; 15–17 P1 |
| **Regime** | 20, 21, 28, 32 | 20–21 P1 Gates; 28 P2; 32 Parken (≈ #205) |
| **Multi-Symbol** | 28, 29 | P2 — nach Single-Symbol (#211 downstream) |
| **Multi-Timeframe** | 5, 12, 13 | 5 P0/Next-5; 12–13 P1 |
| **Hybrid** | 3, 4, 14, 17 | 3–4 Top-3/P0; 14, 17 P1 |
| **Risk/Filter** | 10, 22, 23, 24 | 10 P0; 22–24 P1 |

---

## 8. Priority Grouping (P0 / P1 / P2 / Parken)

### P0 — erste ARVP-Welle (Ranks 1–10)

| Rank | Strategie | Klasse |
|-----:|-----------|--------|
| 1 | `primary_breakout_v1` | Breakout |
| 2 | Donchian Breakout | Breakout |
| 3 | Breakout + Trend Filter | Hybrid |
| 4 | Breakout + Volatility Filter | Hybrid |
| 5 | 1m Entry + 5m Trend Filter | Multi-Timeframe |
| 6 | EMA Trend Filter | Trend-Following |
| 7 | Higher-High / Higher-Low Continuation | Trend-Following |
| 8 | Volatility Breakout | Breakout/Volatility |
| 9 | Z-Score Reversion nur im Range-Regime | Mean Reversion |
| 10 | High-Volatility Avoidance Strategy | Volatility/Filter |

### P1 — zweite Welle nach Baselines (Ranks 11–24)

Ranks 11–24: MA Crossover, HTF Bias + LTF Trigger, 5m Breakout + 1m Timing, Breakout + Momentum, ATR Expansion, Bollinger Squeeze, Breakout after Compression, Bollinger MR, Range-Bound Reversion, Trend-Regime Gate, Range-Regime Gate, Volatility Throttle, TOD/Session Filter, Spread/Liq No-Trade-Zone.

### P2 — nach verbesserter Economics-Ehrlichkeit (Ranks 25–29)

ROC Momentum, RSI Momentum, Opening Range Breakout, BTC/ETH Regime Filter, Symbol Rotation / Relative Strength.

### Parken — zu interpretations-/architektur-nah (Ranks 30–32)

Support/Resistance Breakout, Liquidity Sweep Reversion, Regime-Switch Selector.

---

## 9. Per-Candidate Reasoning (ARVP Fit Summary)

Kompakte Begründung je Kandidat: **ARVP-Fit**, **Datenbedarf**, **Regime-Fit**, **Execution-Economics**, **Risiko/Overfitting**.

| Rank | Strategie | ARVP-Fit | Datenbedarf | Regime-Fit | Execution-Economics | Risiko/Overfitting |
|-----:|-----------|----------|-------------|------------|---------------------|-------------------|
| 1 | `primary_breakout_v1` | Hoch — direkter CDB-Anker, Replay/Paper-Vergleich | 1m OHLCV + paper windows | Trend/Expansion | Pflicht: fees, slippage, rejects | Mittel; repo: PARKED, kein Rescue |
| 2 | Donchian Breakout | Hoch — harter externer Benchmark | 1m OHLCV | Trend | Standard baseline/pessimistic | Niedrig — wenige Parameter |
| 3 | Breakout + Trend Filter | Hoch — PB1-Erweiterung, Regime-Gate-Test | 1m + 5m derived | Trend | Wie Breakout-Basis | Mittel — Filter-Definition stabil halten |
| 4 | Breakout + Volatility Filter | Hoch — HVC/Noise-Block-Hypothese | 1m OHLCV | Trend/strukturierte Vol | High-vol Slippage-Szenarien | Mittel — Overfiltering-Risiko |
| 5 | 1m Entry + 5m Trend Filter | Hoch — MTF ohne neue Datenklasse | 1m + 5m derived | Trend | Entry-Level Slippage | MTF-Lag/Lookahead bei Aggregation |
| 6 | EMA Trend Filter | Hoch — minimalistischer Trend-Overlay | 1m OHLCV | Trend | Standard | EMA-Length-Sensitivität |
| 7 | HH/HL Continuation | Hoch — strukturelle Trend-Erklärbarkeit | 1m OHLCV | Trend | Delay on breakout/retest | Struktur-Sonderfälle |
| 8 | Volatility Breakout | Hoch — Expansion vs Chaos trennen | 1m OHLCV | Trend/Expansion | Aggressive slippage in shocks | Jump-Chasing |
| 9 | Z-Score Range MR | Hoch — kontrollierte MR-Gegenprobe | 1m OHLCV; Spread wünschenswert | Range only | Spread/Slippage **Pflicht** | Knife-catching, regime misclassification |
| 10 | High-Vol Avoidance | Hoch — Evidence-Kompressor / Idle-Logik | 1m OHLCV | Low/Normal Vol | Vergleichbare Cost-Scenarios | Overblocking |
| 11 | MA Crossover | Hoch — Baseline, aber redundant vs EMA | 1m OHLCV | Trend | Standard | Whipsaw in Chop |
| 12 | HTF Bias + LTF Trigger | Hoch — zweite MTF-Welle | 1m, 5m/15m derived | Trend | Standard | Lookahead in HTF-Aggregation |
| 13 | 5m Breakout + 1m Timing | Hoch — nach Baseline-Breakouts | 1m + 5m derived | Trend | Entry-Timing Slippage | Sync-Fehler |
| 14 | Breakout + Momentum | Mittel-Hoch — Noise-Reduktion vs Parameter | 1m + optional Vol | Trend | Standard | Mehr Freiheitsgrade |
| 15 | ATR Expansion | Mittel-Hoch — Overlay/Entry-Test | 1m OHLCV | Expansion | Vol-shock Slippage | Ohne Trendfilter oft roh |
| 16 | Bollinger Squeeze | Mittel-Hoch — Compression→Expansion | 1m OHLCV | Low Vol→Expansion | Standard | Head-fake-Risiko |
| 17 | Breakout after Compression | Mittel-Hoch — ARVP-tauglich, später | 1m OHLCV | Low Vol→Trend | Standard | Range-Definition |
| 18 | Bollinger MR | Mittel — einfach, kosten-sensitiv | 1m OHLCV | Range | Spread kritisch | Trend-Persistence gegen Fade |
| 19 | Range-Bound Reversion | Mittel — harte Range-Definition nötig | 1m OHLCV | Range | Spread/Slippage | Stop-Regeln kritisch |
| 20 | Trend-Regime Gate | Hoch — Overlay, kein Alpha-Kern | 1m + Regime-Labels | Trend | N/A (Filter) | Label-Qualität |
| 21 | Range-Regime Gate | Hoch — Pflichtschranke für MR | 1m + Regime-Labels | Range | N/A (Filter) | Unknown-Regime-Rate |
| 22 | Volatility Throttle | Hoch — Governance-Overlay | 1m OHLCV | Alle | Frequency→Cost | Over-throttling |
| 23 | TOD/Session Filter | Mittel-Hoch — Crypto-Session synthetisch | 1m + Session-Zeit | Intraday | Weniger Trades | Erklärungspflichtig |
| 24 | Spread/Liq No-Trade | Mittel — inhaltlich stark | OHLCV + Spread/Liq | Alle | Kern des Filters | **Datenlücke real** → #3747 |
| 25 | ROC Momentum | Mittel — Indikator-Variante | 1m OHLCV | Trend/Burst | Standard | Threshold-Tuning |
| 26 | RSI Momentum | Mittel — schnell overfit | 1m OHLCV | Trend/Burst | Standard | Threshold-Tuning |
| 27 | Opening Range Breakout | Mittel — 24/7 Session-Anker nötig | 1m + Session | Session-Schub | Standard | Synthetischer ORB-Anker |
| 28 | BTC/ETH Regime Filter | Mittel — cross-symbol | Sync 1m OHLCV | Intermarket | Multi-symbol sync | Schon cross-symbol |
| 29 | Symbol Rotation | Niedrig-Mittel — Routing-Komplexität | Cross-symbol 1m | Cross-section | Turnover/Costs | Universe drift (#211) |
| 30 | S/R Breakout | Mittel — Level-Definition mining-anfällig | 1m OHLCV | Trend | Standard | **Parken** — Data snooping |
| 31 | Liquidity Sweep MR | Niedrig — Candle-only Voodoo | OHLCV + ideal Book | Range | Spread/Book kritisch | **Parken** — Mikrostruktur |
| 32 | Regime-Switch Selector | Niedrig — ≈ Gearbox (#205) | Cross-strategy data | Alle | Routing overhead | **Parken** — Architektur-Sprung |

---

## 10. ARVP Test Packages (Reference)

| Paket | Inhalt | Ziel |
|-------|--------|------|
| **A — Breakout-Basis** | PB1, Donchian, Bo+Trend, Bo+Vol, Vol Breakout | Breakout-Familie benchmarken |
| **B — Trend-Following** | EMA Filter, MA Cross, HH/HL, 1m+5m, HTF/LTF | Trend vs Breakout-Trigger |
| **C — Mean Reversion** | Z-Score Range, Bollinger MR, Range-Bound | Kontrollierte Gegenprobe |
| **D — Regime/Filter** | Trend/Range Gates, HVC Avoidance, Vol Throttle, TOD, Spread/Liq | Block-Entscheidungen belegen |
| **E — Multi-Symbol** | BTC/ETH Filter, Rotation, Relative Strength | Erst nach Single-Symbol stabil |
| **F — Hybrid** | Bo+Momentum, Bo after Compression, 5m+1m, MR in Range, Trend+Vol Throttle | Robustheit vs Parameterraum |

**Gesamtreihenfolge:** A → D → B → F → C → E.

---

## 11. Safety and Non-Goals

- **LR NO-GO** — `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
- **Kein Live-Go, kein Echtgeld-Go**
- **Board `trade-capable` ≠ Live-Go**
- Keine Strategie-Implementierung in diesem Slice
- Kein Backtest / kein ARVP-Run
- Keine Candidate-Promotion
- Kein Gearbox/Selector-Design (#205)
- Kein neuer Candidate-Contract (#3034 existiert, CLOSED)
- Keine Renditeversprechen

---

## 12. Restunsicherheiten

1. Deep Research basiert auf **öffentlich sichtbarem** CDB-Kontext zum Research-Zeitpunkt; interne Spread/Orderbook-Historien könnten P1/P2-Ranking verschieben.
2. `primary_breakout_v1` ist im Research Top-3, im Repo **PARKED** — künftige ARVP-Welle testet primär **neue** Kandidaten (z. B. Donchian, Filter-Varianten), nicht PB1-Rescue.
3. Same-venue Friktionsevidenz bleibt Lücke bis #3747 — MR- und Spread-sensitive Kandidaten sind deshalb konservativ priorisiert.
4. Window-Bank/`regime_segments`-Wahrheit hängt an #3742 — ohne §5.2.4 bleibt Phase A Product-Complete blockiert (#2974).

---

*Evidence transferred 2026-07-06 for #3746. Source: Desktop Deep Research export (curated, not copied).*
