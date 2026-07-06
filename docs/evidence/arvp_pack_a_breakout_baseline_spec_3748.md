# ARVP Pack-A — Breakout Baseline Test Package Spec (#3748)

Status Class: Test specification (no execution, no promotion)
Issue: [#3748](https://github.com/jannekbuengener/Claire_de_Binare/issues/3748)
Parent: [#1900](https://github.com/jannekbuengener/Claire_de_Binare/issues/1900)
Prerequisites:
- [#3746](https://github.com/jannekbuengener/Claire_de_Binare/issues/3746) CLOSED — PR [#3749](https://github.com/jannekbuengener/Claire_de_Binare/pull/3749) @ `0a3b94c`
- [#3747](https://github.com/jannekbuengener/Claire_de_Binare/issues/3747) CLOSED — PR [#3766](https://github.com/jannekbuengener/Claire_de_Binare/pull/3766) @ `2607c5f`
Related: [#3742](https://github.com/jannekbuengener/Claire_de_Binare/issues/3742) (OPEN), [#3038](https://github.com/jannekbuengener/Claire_de_Binare/issues/3038) (CLOSED), [#3039](https://github.com/jannekbuengener/Claire_de_Binare/issues/3039) (CLOSED), [#3037](https://github.com/jannekbuengener/Claire_de_Binare/issues/3037) (CLOSED), [#3086](https://github.com/jannekbuengener/Claire_de_Binare/issues/3086) (CLOSED — execute split; friction evidence gap persists per #3747 B1), [#2985](https://github.com/jannekbuengener/Claire_de_Binare/issues/2985), [#205](https://github.com/jannekbuengener/Claire_de_Binare/issues/205), [#211](https://github.com/jannekbuengener/Claire_de_Binare/issues/211)
Live-Readiness: **NO-GO**
Echtgeld: **not authorized**
Board stage: `trade-capable` (orthogonal to LR; **not** Live-Go)

**This document is a test specification only. It does not authorize an ARVP run, backtest execution, batch runner invocation (#3037), or candidate promotion.**

---

## 1. Source / Provenance

| Field | Value |
|-------|-------|
| Primary inputs | `docs/evidence/arvp_strategy_longlist_deep_research_3746.md`, `docs/evidence/arvp_p0_strategy_data_regime_economics_map_3747.md` |
| Strategy canon (PB1) | `knowledge/contracts/PRIMARY_BREAKOUT_V1.md` |
| Scenario canon | `docs/strategy/CDB_PROFITABILITY_SCENARIO_PACK_LIBRARY_V1.md` (#3038) |
| Economics canon | `docs/strategy/CDB_PROFITABILITY_EXECUTION_ECONOMICS_V1.md` (#3039) |
| Dataset quality canon | `docs/strategy/CDB_PROFITABILITY_DATASET_QUALITY_GATE_V1.md` (#3035) |
| Batch run design (reference only) | `docs/strategy/CDB_PROFITABILITY_ARVP_BATCH_RUNNER_V1.md` (#3037) |
| Same-venue policy | `docs/evidence/mexc_same_venue_data_quality_policy_3091.md` |
| Friction gap evidence | `docs/evidence/arvp_mexc_same_venue_acquisition_3086.md` |
| Technical scenario packs | `core/replay/scenario_packs.py` (`baseline`, `pessimistic_execution`, `delayed_execution`, `low_liquidity`, `feed_gap`) |
| Spec date | 2026-07-06 |
| Renditeversprechen | **None** |

**Mapping rule:** This spec **references** #3038/#3039/#3035 canon. It does **not** duplicate their schemas, verdict enums, or JSON fixtures.

---

## 2. Brain Evidence

```text
brain_source: repo-only
brain_status: not-used
tools_or_queries:
  - cdb_context_briefing (task_id=cdb-briefing-3748-pack-a-breakout-spec)
  - git fetch origin --prune; git status -sb; git rev-parse HEAD; git rev-parse origin/main
  - git switch -c docs/3748-arvp-pack-a-breakout-spec origin/main
  - gh issue view 3748, 3747, 3746, 1900, 3742, 3038, 3039, 3037, 3086, 2985
  - gh pr list --state open --limit 20
  - read: arvp_strategy_longlist_deep_research_3746.md, arvp_p0_strategy_data_regime_economics_map_3747.md
  - read: PRIMARY_BREAKOUT_V1.md, CDB_PROFITABILITY_*_V1.md (3035/3038/3039/3037)
  - read: mexc_same_venue_data_quality_policy_3091.md, arvp_mexc_same_venue_acquisition_3086.md
  - rg dedupe scan — no prior arvp_pack_a* evidence file
records_or_results:
  - context_brain_attempted=true; context_brain_used=false; context_available=false
  - repo_fallback_reason=insufficient_evidence; records_found=none
  - briefing_id=46d112840d981920; operator_trust_level=LOW; enrichment records=none
  - HEAD == origin/main == 2607c5fa964d1830150c5cfea2bce8a38a19d530
  - #3748 OPEN; #3746/#3747 CLOSED; #3742 OPEN; #3086 CLOSED (GitHub live)
repo_crosscheck:
  - docs/evidence/arvp_exit_regime_decay_diagnosis_3183.md (primary_breakout_v1 PARK)
  - artifacts/backtests/primary_breakout_v1/20260418-212643/ (example pinned dataset path)
  - core/replay/scenario_packs.py (five deterministic packs)
impact_on_plan:
  - Pack-A spec derived from #3746 Pack-A table + #3747 P0 matrix; wave-1 minimum = Top-3.
  - ranking_ready=false default enforced until B1 friction evidence satisfied (#3747 §7–8).
  - PB1 included as PARKED reference anchor only; Donchian + Bo+Trend are new comparison candidates.
  - #3742 regime_segments remain parallel dependency — not claimed solved.
limitations:
  - No SurrealDB/context-brain records used.
  - Donchian / filter-variant parameter defaults are spec-frozen placeholders — not optimized.
  - Spec does not prove economic edge, promotion, or live readiness.
  - GitHub live shows #3086 CLOSED; historical spread/liquidity/fill series gap (B1) remains per #3747.
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

**Kurzentscheidung:**

1. **Pack-A (Breakout-Basis)** benchmarkt die Breakout-Familie auf **einem gemeinsamen** BTCUSDT/MEXC/1m same-venue Dataset mit **long-only** Default.
2. **Welle-1-Minimum (operational):** Top-3 — `primary_breakout_v1` (PARKED Referenzanker), **Donchian Breakout**, **Breakout + Trend Filter**.
3. **Pack-A Vollumfang:** zusätzlich Breakout + Volatility Filter, Volatility Breakout — **Welle-1-Run-Slice darf auf Top-3 begrenzt bleiben**.
4. **Vergleichsmodus:** Shape-/Signal-/Szenario-Vergleich mit `ranking_ready=false` — **keine** ökonomische Rangliste ohne #3039-vollständige Kostenattribution und B1-Friktionsbeleg.
5. **`primary_breakout_v1`:** Nur Referenz/Benchmark-Parität — **kein** Rescue, **keine** Promotion (#3183 PARK).
6. **Szenarien:** Pflicht-Set aus `core/replay/scenario_packs.py`, semantisch aligned zu #3038 — baseline, pessimistic execution, delayed execution, low liquidity, feed gap.
7. **Regime-segmentierte Paper-Scorecards:** blockiert bis #3742 `regime_segments` liefert — offline Regime-Ableitung für Shape-Tests erlaubt mit Limitation-Banner.
8. **LR NO-GO / kein Live-Go / kein Echtgeld-Go** — diese Spec autorisiert keine Kapital- oder LR-Freigabe.

**Explizit:** Spec ≠ ausgeführte Validierung. Ein späterer Execute-Slice (#3037 lineage) braucht eigenes GO.

---

## 4. Pack-A Purpose and Boundaries

### 4.1 Purpose

Pack-A ist das erste ARVP-Testpaket der Validierungswelle A (Breakout-Basis) aus #3746 §10. Ziel:

- Breakout-Trigger-Varianten **vergleichbar** machen (Signal-Shape, Trade-Frequenz, Szenario-Fragilität).
- CDB-Anker `primary_breakout_v1` als **Referenz** gegen neue Kandidaten stellen.
- Deterministische Replay-Parität und Szenario-Stress **spezifizieren**, nicht ausführen.

### 4.2 In scope

| Item | Scope |
|------|-------|
| Wave-1 Top-3 Kandidaten | Spec + Vergleichsregeln |
| Pack-A Erweiterung (Bo+Vol, Vol Breakout) | Spec-Tabelle; optional nach Top-3 |
| Ein gemeinsames Dataset | Fingerprint-pinned |
| Szenario-Pack-Referenzen | #3038 + `scenario_packs.py` |
| Economics-Deklaration | #3039 mit `ranking_ready=false` |
| PASS/FAIL/HOLD-Schema | Für spätere Execute-Auswertung |

### 4.3 Out of scope / forbidden

| Boundary | Decision |
|----------|----------|
| Strategie-Implementierung / Signal-Code | **Forbidden** |
| Backtest / ARVP batch run (#3037) | **Forbidden** in diesem Slice |
| Parameteroptimierung | **Forbidden** |
| Candidate promotion | **Forbidden** |
| `primary_breakout_v1` rescue | **Forbidden** — PARK bleibt |
| Gearbox / Selector (#205) | **Forbidden** |
| Multi-Asset (#211) | **Forbidden** |
| #3038/#3039 Canon duplizieren | **Forbidden** — nur referenzieren |
| #3742 als gelöst behandeln | **Forbidden** — parallel OPEN |
| Renditeversprechen | **Forbidden** |

---

## 5. Wave-1 Minimum — Top-3 Definition

| Rank | strategy_id | human_name | Wave-1 role | Promotion |
|------|-------------|------------|-------------|-----------|
| 1 | `primary_breakout_v1` | Primary Breakout v1 | **Reference anchor** — parity benchmark only | **PARKED** — no rescue (#3183) |
| 2 | `donchian_breakout_v1` | Donchian Breakout | **New comparison candidate** | Not authorized |
| 3 | `breakout_trend_filter_v1` | Breakout + Trend Filter | **New comparison candidate** | Not authorized |

**Wave-1 binding constraints:**

| Dimension | Value |
|-----------|-------|
| Symbol | `BTCUSDT` |
| Venue | MEXC same-venue |
| Timeframe | `1m` OHLCV (primary) |
| Direction | **long-only** (default) |
| Dataset | **One** pinned dataset — same fingerprint for all Top-3 |
| Scenario packs | Same five-pack set for all Top-3 (§8) |
| Economics model | Same #3039 model fixture version for all Top-3 |
| `ranking_ready` | **`false`** unless #3039 assessment + B1 friction evidence satisfied |
| Comparative output | Relative shape/stress deltas — **not** league ranking |

**Pack-A extension (not wave-1 minimum):** `breakout_volatility_filter_v1`, `volatility_breakout_v1` — spec'd in §7 and §6 but may be deferred to wave-1b without invalidating Top-3 comparison.

---

## 6. Full Pack-A Candidate Table

| Order | strategy_id | human_name | strategy_family | Wave | ARVP role | PB1 relation | ranking_ready default |
|------:|-------------|------------|-----------------|------|-----------|--------------|----------------------|
| 1 | `primary_breakout_v1` | Primary Breakout v1 | Breakout | **W1 min** | Reference anchor | Self (PARKED) | `false` |
| 2 | `donchian_breakout_v1` | Donchian Breakout | Breakout | **W1 min** | New benchmark | Compare to PB1 | `false` |
| 3 | `breakout_trend_filter_v1` | Breakout + Trend Filter | Hybrid | **W1 min** | New benchmark | Filtered PB1 cousin | `false` |
| 4 | `breakout_volatility_filter_v1` | Breakout + Volatility Filter | Hybrid | Extension | Vol-gated breakout | Filter variant | `false` |
| 5 | `volatility_breakout_v1` | Volatility Breakout | Breakout/Volatility | Extension | Expansion trigger | Distinct trigger shape | `false` |

Data/economics prerequisites per candidate: see `docs/evidence/arvp_p0_strategy_data_regime_economics_map_3747.md` §4 — **link, do not duplicate**.

---

## 7. Per-Strategy Specification Tables

Frozen parameters below are **spec placeholders** for testability. They are **not** optimized and must not be tuned within Pack-A wave 1.

### 7.1 `primary_breakout_v1` (Reference Anchor — PARKED)

| Dimension | Specification |
|-----------|---------------|
| **strategy_id** | `primary_breakout_v1` |
| **human_name** | Primary Breakout v1 |
| **purpose** | CDB canonical breakout reference; parity benchmark for Pack-A shape/scenario comparison — **not** promotion target |
| **entry concept** | Long entry when `regime_id == TREND` and `close > highest_high(entry_lookback) * (1 + breakout_buffer)` and cooldown clear — per `knowledge/contracts/PRIMARY_BREAKOUT_V1.md` |
| **exit concept placeholder** | Long exit when `close < lowest_low(exit_lookback)`; exits allowed when entries blocked |
| **filter requirements** | External `TREND` regime gate (fail-closed if regime/market state missing or stale) |
| **required inputs** | 1m OHLCV; regime labels (`regime_id`); market-state freshness; risk/allocation/kill-switch blocks |
| **lookahead boundary** | Signals evaluated on **closed** 1m bars only; regime context must be contemporaneous or lagged — no future bar access |
| **known limitations** | **PARKED** (#3183); tri-loop FULL_STOP; friction-sensitive; `ranking_ready=false`; reference-only in Pack-A |

**Canonical frozen defaults (repo-backed):** `entry_lookback_minutes=240`, `exit_lookback_minutes=120`, `breakout_buffer=0.0005`, `min_minutes_between_entries=60`, `trade_side_mode=long_only`.

### 7.2 `donchian_breakout_v1` (New Comparison Candidate)

| Dimension | Specification |
|-----------|---------------|
| **strategy_id** | `donchian_breakout_v1` |
| **human_name** | Donchian Breakout |
| **purpose** | Minimal-parameter external breakout benchmark with few degrees of freedom |
| **entry concept** | Long when `close` breaks above `highest_high(entry_channel_bars)` of prior **closed** 1m bars (exclusive of current bar) |
| **exit concept placeholder** | Long exit when `close` falls below `lowest_low(exit_channel_bars)` of prior closed bars **or** opposite channel breach per frozen exit rule |
| **filter requirements** | **None** for wave 1 (raw Donchian) — optional `TREND` overlay deferred to Pack-D |
| **required inputs** | 1m OHLCV only |
| **lookahead boundary** | Channel highs/lows computed from bars `[t-entry_channel_bars, t-1]` only; entry evaluated at bar `t` close |
| **known limitations** | Whipsaw in chop; no regime gate; economics partial without B1 friction series |

**Frozen spec parameters (placeholder):** `entry_channel_bars=20`, `exit_channel_bars=10`, `trade_side_mode=long_only`, `min_minutes_between_entries=30`.

### 7.3 `breakout_trend_filter_v1` (New Comparison Candidate)

| Dimension | Specification |
|-----------|---------------|
| **strategy_id** | `breakout_trend_filter_v1` |
| **human_name** | Breakout + Trend Filter |
| **purpose** | Breakout entries only when higher-timeframe trend gate is bullish — tests filter value vs raw Donchian |
| **entry concept** | Same breakout trigger as `donchian_breakout_v1` **AND** 5m-derived trend gate `close_5m > EMA(trend_ema_period)` on **completed** 5m bar |
| **exit concept placeholder** | Exit on Donchian lower channel **or** trend gate failure (`close_5m <= EMA`) — whichever fires first per bar |
| **filter requirements** | **Mandatory** 5m trend gate (derived, not fetched separately) |
| **required inputs** | 1m OHLCV; **5m derived** OHLCV + EMA |
| **lookahead boundary** | 5m bars aggregated from 1m with **closed-bar-only** rule (§10); trend gate uses last **completed** 5m bar relative to 1m decision time |
| **known limitations** | Filter turnover may reduce trades without proving net edge; MTF sync risk; B7 lookahead policy applies |

**Frozen spec parameters (placeholder):** inherits Donchian `20/10`; `trend_ema_period=20` on 5m; `trade_side_mode=long_only`.

### 7.4 `breakout_volatility_filter_v1` (Pack-A Extension)

| Dimension | Specification |
|-----------|---------------|
| **strategy_id** | `breakout_volatility_filter_v1` |
| **human_name** | Breakout + Volatility Filter |
| **purpose** | Breakout only in structured vol regime — blocks entries in chaotic high-ATR bars |
| **entry concept** | Donchian breakout entry **AND** `ATR(atr_period) / close` within `[vol_floor, vol_ceiling]` on closed 1m bar |
| **exit concept placeholder** | Donchian lower channel exit; vol filter does not block exits |
| **filter requirements** | ATR band gate on 1m |
| **required inputs** | 1m OHLCV (ATR from 1m) |
| **lookahead boundary** | ATR from closed bars only |
| **known limitations** | Overfiltering risk; vol shocks need pessimistic_execution scenario (#3038) |

**Frozen placeholders:** Donchian `20/10`; `atr_period=14`; `vol_floor=0.0003`; `vol_ceiling=0.0030`.

### 7.5 `volatility_breakout_v1` (Pack-A Extension)

| Dimension | Specification |
|-----------|---------------|
| **strategy_id** | `volatility_breakout_v1` |
| **human_name** | Volatility Breakout |
| **purpose** | Entry on price breakout **with concurrent** volatility expansion — distinct from vol-filtered Donchian |
| **entry concept** | Long when `close > highest_high(breakout_lookback)` **AND** `ATR(atr_period) > ATR(atr_period).shift(expansion_lag) * expansion_multiplier` |
| **exit concept placeholder** | Exit when `close < lowest_low(exit_lookback)` or ATR expansion condition no longer holds (frozen rule) |
| **filter requirements** | Expansion trigger is part of entry, not overlay |
| **required inputs** | 1m OHLCV |
| **lookahead boundary** | ATR shift uses completed bars only |
| **known limitations** | Jump-chasing in shocks; high slippage sensitivity — aggressive `pessimistic_execution` / `low_liquidity` scenarios mandatory |

**Frozen placeholders:** `breakout_lookback=20`, `exit_lookback=10`, `atr_period=14`, `expansion_lag=5`, `expansion_multiplier=1.15`.

---

## 8. Dataset and Quality Gate

### 8.1 Required dataset (all Pack-A candidates)

| Field | Requirement |
|-------|-------------|
| symbol | `BTCUSDT` |
| venue | **MEXC same-venue** per `mexc_same_venue_data_quality_policy_3091.md` |
| timeframe | `1m` |
| direction | long-only |
| minimum grade | `STRICT_CAMPAIGN_GRADE` or documented `TOLERANT` with limitations banner |
| quality gate | [#3035](https://github.com/jannekbuengener/Claire_de_Binare/issues/3035) — emit `profitability_dataset_quality_report.v1` |
| verdict for wave 1 | `PASS` required; `WARNING` only with explicit documented limitations; `FAIL`/`BLOCKED` → `HOLD_DATA` |

### 8.2 Pinned dataset rule (wave-1 comparability)

All Top-3 candidates **must** bind to the **same** dataset fingerprint in any future execute slice:

| Field | Rule |
|-------|------|
| `dataset_fingerprint` | Single SHA256 / report fingerprint shared across manifest |
| `requested_window` | Identical start/end UTC for all candidates |
| `source_provenance` | MEXC same-venue; no `venue_mismatch=true` windows for wave-1 primary compare |
| example anchor (non-binding) | `artifacts/backtests/primary_breakout_v1/20260418-212643/dataset.candles.json` — execute slice must re-pin with #3035 report |

**Cross-reference:** Full P0 data matrix — `arvp_p0_strategy_data_regime_economics_map_3747.md` §5.

### 8.3 5m derived handling

| Rule | Detail |
|------|--------|
| Source | Derived **only** from the same pinned 1m feed |
| Aggregation | Floor timestamp to 5m bucket; OHLCV = standard rollup (open=first, high=max, low=min, close=last, volume=sum) |
| Completeness | 5m bar considered **complete** only after minute `bucket_end` closes |
| Decision time | 1m signal at bar `t` may use 5m bars with `5m_close_time <= t` only |
| Lookahead | **Forbidden:** using incomplete 5m bucket or future 1m bars inside open 5m bucket |
| Applies to | `breakout_trend_filter_v1` (mandatory); PB1 optional context only |

### 8.4 Same-venue requirement

- Candle data must be MEXC same-venue for wave-1 primary comparison.
- Windows with `venue_mismatch=true` (e.g. #3028 Binance) are **excluded** from wave-1 primary fingerprint unless explicitly scoped as secondary sensitivity with banner.
- Historical spread/liquidity/fill/reject series: **not** repo-backed for all windows — see #3086 evidence + #3747 B1. Issue #3086 is **CLOSED** on GitHub (decision split); **friction evidence gap remains** for honest net economics.

### 8.5 #3035 quality gate dependency

Before any execute slice trusts a dataset:

1. Run dataset quality report per `CDB_PROFITABILITY_DATASET_QUALITY_GATE_V1.md`.
2. Record fingerprint, coverage, missing/duplicate/ordering counts.
3. Fail-closed: no silent normalization of duplicates or out-of-order bars.

---

## 9. Scenario Pack Section (#3038)

**Canon:** `docs/strategy/CDB_PROFITABILITY_SCENARIO_PACK_LIBRARY_V1.md` — stress domains and advisory verdict semantics.

**Technical implementation reference:** `core/replay/scenario_packs.py` — deterministic built-in packs.

### 9.1 Mandatory scenario set (Pack-A wave 1)

| scenario_id | Domain ( #3038 ) | Pack-A use |
|-------------|------------------|------------|
| `baseline` | Undegraded reference | Shape baseline; deterministic rerun parity anchor |
| `pessimistic_execution` | slippage shock, spread expansion, rejections | Friction stress — mandatory for breakout entries |
| `delayed_execution` | latency | Entry timing sensitivity (esp. Bo+Trend MTF) |
| `low_liquidity` | liquidity stress, partial fills | Fill-rate / partial-fill sensitivity |
| `feed_gap` | feed gaps | Missing-bar / stale-feed robustness |

All five scenarios run against **each** wave-1 candidate on the **same** pinned dataset in any future execute slice.

### 9.2 Scenario verdict interpretation (advisory)

Per #3038: `PASS` does not authorize live/paper scaling. Pack-A uses scenario outcomes for **relative fragility comparison** only.

| Scenario outcome | Pack-A interpretation |
|------------------|----------------------|
| `PASS` | Candidate survives stress domain for scoped research purpose |
| `WARNING` | Review / possible PARK in execute slice |
| `FAIL` | Stress-fragile — candidate FAIL or HOLD in aggregate schema (§11) |
| `BLOCKED` | Cannot assess — aggregate → `HOLD_DATA` or `HOLD_FRICTION` |

### 9.3 #3037 boundary

`CDB_PROFITABILITY_ARVP_BATCH_RUNNER_V1.md` defines how a future batch **consumes** scenario references. **This spec does not invoke the batch runner.**

---

## 10. Execution Economics Section (#3039, #3086)

**Canon:** `docs/strategy/CDB_PROFITABILITY_EXECUTION_ECONOMICS_V1.md`

### 10.1 Declared economics model (wave 1)

| Field | Rule |
|-------|------|
| Model artifact | `profitability_execution_economics_model.v1` fixture — version pinned in execute manifest |
| Fees | MEXC schedule — bounded declared assumptions |
| Spread | Declared model; measured same-venue series **preferred** — absent → `WARNING` / `HOLD_FRICTION` |
| Slippage | Informed by scenario packs (#3038); missing assumptions → `FAIL` per #3039 |
| Assessment | Per-candidate `profitability_execution_economics_assessment.v1` |
| **`ranking_ready`** | **`false` by default** for all Pack-A candidates in wave 1 |

### 10.2 Execution truth statement

```text
ranking_ready = false
```

unless **both**:

1. #3039 assessment complete with no fail-closed assumption gaps **and**
2. B1 same-venue friction evidence satisfied per #3747 §8 (spread/liquidity/fill/reject — not replaceable by OHLCV alone)

**Signal-/Shape-Test** is possible without (2). **Economic truth / ranking** is **blocked**.

### 10.3 #3086 / friction gap crosswalk

| Topic | Status |
|-------|--------|
| GitHub #3086 | **CLOSED** (acquisition decision split) |
| B1 friction evidence | **Open gap** per #3747 — historical spread/liq/fill/reject not repo-backed for all windows |
| Pack-A implication | Economics assessments may use declared fixtures; aggregate verdict includes `NOT_RANKING_READY` and/or `HOLD_FRICTION` |
| Duplication | **No** new friction follow-up issue — gap covered by #3086 evidence + #3747 B1 |

Cost/friction scenarios declared via #3039 + stressed via #3038 packs — not proof of live friction.

---

## 11. Metrics Section

Metrics below must be emitted comparably for each candidate in a future execute slice. Sources: replay artifacts, `profitability_evidence_packet.v1`, scenario stress summaries (#3038), economics assessments (#3039).

| Metric | Definition | Wave-1 requirement | ranking impact |
|--------|------------|--------------------|----------------|
| **deterministic rerun parity** | Same dataset fingerprint + config → identical signal count and entry timestamps across reruns | **Mandatory** — mismatch → `FAIL` | Blocks trust |
| **paper drift** | Replay-vs-paper compare delta where same-venue paper window exists | Report if available; `not_run` → documented limitation | `ranking_ready=false` if hard gate missing |
| **net after costs** | Gross − fees − spread − slippage per #3039 | **Mandatory field**; may use declared model | Advisory only while `ranking_ready=false` |
| **regime PnL** | PnL split by regime segment | **Optional** offline; **blocked** for natural-paper segments until #3742 | `HOLD_REGIME_SEGMENTS` if required but missing |
| **fill-rate drift** | Replay fill rate vs paper/reference | Report where paper exists; else `not_assessed` | `HOLD_FRICTION` if claimed without evidence |
| **trade count** | Round-trip or entry count on pinned window | **Mandatory** | Comparative (frequency) |
| **drawdown / adverse excursion** | Max drawdown, MAE per trade or portfolio | **Mandatory** | Stress context |
| **failure count** | Guard blocks, rejected signals, scenario FAIL count | **Mandatory** | Fragility indicator |

**Comparative rule:** Metrics support **side-by-side tables** across Top-3 on identical dataset/scenarios — not ordinal promotion.

---

## 12. PASS / FAIL Schema

Aggregate verdict enum for Pack-A wave-1 execute evaluation (per candidate, then optional pack-level rollup).

### 12.1 Verdict definitions

| Verdict | Meaning | Typical triggers |
|---------|---------|------------------|
| **PASS** | Shape/scenario spec satisfied for scoped research; economics limitations explicitly declared | Deterministic parity OK; scenarios not FAIL; dataset #3035 PASS; limitations banner present if `ranking_ready=false` |
| **FAIL** | Candidate stress-fragile or spec violation | Scenario FAIL on mandatory pack; deterministic parity break; lookahead violation detected |
| **HOLD_DATA** | Dataset or quality prerequisite missing | #3035 FAIL/BLOCKED; venue_mismatch on primary window; missing pinned fingerprint |
| **HOLD_FRICTION** | Honest net economics cannot be asserted | B1 gap; spread model placeholder; fill-rate not assessed where required |
| **HOLD_REGIME_SEGMENTS** | Regime-segmented scorecard requested but unavailable | #3742 `regime_segments` empty on natural-paper windows |
| **NOT_RANKING_READY** | Explicit sub-status — must accompany any candidate with `ranking_ready=false` | Default for **all** wave-1 candidates until B1 + #3039 complete |

### 12.2 Fail-closed rules

1. **No PASS** that implies promotion, live readiness, or positive net edge proof.
2. Any candidate with `ranking_ready=false` **must** carry `NOT_RANKING_READY` in output bundle.
3. `HOLD_FRICTION` and `NOT_RANKING_READY` may coexist with shape-level **PASS** (signal test OK, economics blocked).
4. Pack-level rollup: if any Top-3 candidate is `FAIL`, pack status is at best `PARTIAL` — never `PROMOTION_READY`.
5. Z-Score MR and other non-Pack-A candidates are **out of scope** — do not mix into Pack-A verdict.

### 12.3 Example decision matrix (wave 1)

| Condition | Aggregate verdict |
|-----------|-------------------|
| #3035 PASS + parity OK + scenarios PASS + `ranking_ready=false` | **PASS** + **NOT_RANKING_READY** |
| #3035 PASS + parity OK + `pessimistic_execution` FAIL | **FAIL** |
| #3035 FAIL | **HOLD_DATA** |
| Shape OK + spread series missing + net claimed | **HOLD_FRICTION** (no honest net) |
| Regime PnL required on paper + no #3742 segments | **HOLD_REGIME_SEGMENTS** |

---

## 13. Lookahead and Determinism Boundaries

| Boundary | Rule |
|----------|------|
| Bar timing | Signals on **closed** 1m candles only |
| 5m derivation | Completed buckets only (§8.3) |
| Regime labels | Contemporaneous or lagged — no future regime |
| Scenario packs | Deterministic overrides per `scenario_packs.py` — no random stress |
| Config freeze | Parameter sets fixed per §7 — no in-run optimization |
| Rerun parity | Mandatory metric (§11) — hash of signal timeline must match across reruns |
| PB1 regime dependency | If regime feed missing → fail-closed no-entry (existing PB1 behavior) |

---

## 14. Long-Only Default

| Field | Value |
|-------|-------|
| `trade_side_mode` | `long_only` for all Pack-A candidates |
| Short signals | **Forbidden** in wave 1 |
| Exit semantics | Close long / flat — no short entry |
| Alignment | Consistent with #3746 default test universe and CDB public loop |

---

## 15. Dependency — #3742 (regime_segments)

| Topic | Status |
|-------|--------|
| Issue #3742 | **OPEN** — window bank / `regime_segments` extraction |
| Pack-A dependency | **Natural-paper regime-segmented scorecards** and Phase-A §5.2.4 segmented compare **blocked** without #3742 |
| Allowed without #3742 | Offline shape tests; candle-derived regime proxies with limitation banner |
| Spec claim | **Does not** assert `regime_segments` populated |

Per `arvp_window_bank_inventory_3212.md`: current bank has `regime_segments` **unavailable**.

---

## 16. Future Execute Slice Hook (#3037 — Reference Only)

A future execute slice (separate GO) should produce:

| Output | Contract reference |
|--------|-------------------|
| Batch manifest | `profitability_arvp_batch_manifest.v1` |
| Batch summary | `profitability_arvp_batch_summary.v1` |
| Per-candidate evidence | `profitability_evidence_packet.v1` |
| Scenario stress | `profitability_scenario_stress_summary.v1` (#3038) |
| Economics | `profitability_execution_economics_assessment.v1` (#3039) |

Manifest must pin: dataset fingerprint (#3035), Top-3 `strategy_id` list, scenario pack IDs, economics model version, `ranking_ready=false` default.

**Check existing #3037 lineage before creating a new execute issue.**

---

## 17. Safety and Non-Goals

- **LR NO-GO** — `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
- **Kein Live-Go, kein Echtgeld-Go**
- **Board `trade-capable` ≠ Live-Go**
- **Spec ≠ executed validation**
- Keine Strategie-Implementierung / kein Signal-Code
- Kein Backtest / kein ARVP-Run in diesem Slice
- Keine Candidate-Promotion
- Kein Gearbox (#205) / Multi-Asset (#211)
- Kein Duplikat von #3035 / #3038 / #3039 Canon
- Keine Lösung von #3742
- Keine Renditeversprechen

---

## 18. Restunsicherheiten

1. Donchian / filter frozen parameters (§7) are reasonable placeholders — not validated against MEXC microstructure.
2. 5m aggregation contract is spec-declared; canonical code adapter for `breakout_trend_filter_v1` does not exist yet — execute slice needs adapter GO.
3. GitHub shows #3086 CLOSED while B1 friction evidence remains open in #3747 — wave 1 stays `ranking_ready=false`.
4. Example dataset under `artifacts/backtests/primary_breakout_v1/` may not be MEXC same-venue — execute slice must re-pin with #3035 + same-venue policy.
5. Pack-A extension candidates (Bo+Vol, Vol Breakout) ordering after Top-3 is intentional deferral, not deprioritization of research value.

---

*Evidence created 2026-07-06 for #3748. Primary inputs: #3746 longlist + #3747 P0 matrix + profitability canon crosswalk. **Not executed.***
