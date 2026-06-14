# ARVP Scenario-Pack-First Research Spec

**Issue:** [#3189](https://github.com/jannekbuengener/Claire_de_Binare/issues/3189)
**Parent:** [#1900](https://github.com/jannekbuengener/Claire_de_Binare/issues/1900)
**Refs:** [#3188](https://github.com/jannekbuengener/Claire_de_Binare/issues/3188), [#3186](https://github.com/jannekbuengener/Claire_de_Binare/issues/3186), [#2985](https://github.com/jannekbuengener/Claire_de_Binare/issues/2985)
**Foundations:** [#3037](https://github.com/jannekbuengener/Claire_de_Binare/issues/3037), [#3038](https://github.com/jannekbuengener/Claire_de_Binare/issues/3038), [#3039](https://github.com/jannekbuengener/Claire_de_Binare/issues/3039)
**Decision date:** 2026-06-14
**Status:** DONE_MERGED_SCENARIO_PACK_FIRST_SPEC_READY

---

## Brain Evidence

```
brain_source: repo-only
brain_status: not-used
tools_or_queries:
  - read: full canonical read-order (governance, invariants, knowledge hub, working repo canon)
  - read: CONTROL_REGISTER.md, LR-AUDIT-STATUS-2026-03-05.md, CURRENT_STATUS.md
  - bash: git fetch origin --prune, git status -sb, git rev-parse HEAD, git rev-parse origin/main
  - bash: gh pr list --state open, gh issue view 3189,3188,3186,2985,1900,3037,3038,3039
  - read: all 8 foundation evidence/strategy docs required by spec
  - read: core/replay/scenario_packs.py
  - bash: gh issue list --state open --search "scenario pack first research slice"
  - bash: gh issue list --state open --search "scenario inventory economics gates"
  - bash: gh issue list --state open --search "ARVP scenario-pack-first"
records_or_results:
  - git: HEAD=origin/main=3d51aef4983fd7f78a01f15df93a3bb12ae44f85
  - gh: #3189 OPEN (stub body), #3188 CLOSED, #3186 CLOSED, #2985 OPEN, #1900 OPEN
  - gh: #3037 CLOSED (batch runner), #3038 CLOSED (scenario pack lib), #3039 CLOSED (execution economics)
  - gh: no open PRs
  - gh dedupe: 0 open issues match "scenario pack first", "scenario inventory", or "ARVP scenario-pack-first"
  - All 8 foundation docs present on main; core/replay/scenario_packs.py exists on main
repo_crosscheck:
  - docs/evidence/arvp_post_tri_regime_candidate_discovery_axis_3188.md
  - docs/evidence/arvp_next_candidate_selection_after_primary_breakout_park_3186.md
  - docs/evidence/arvp_roadmap_reconcile_after_primary_breakout_park_2985_1900.md
  - docs/evidence/profitability_break_even_boundary_cost_slippage_sensitivity_3170.md
  - docs/evidence/profitability_post_3166_tri_regime_park_next_axis_decision_3168.md
  - docs/evidence/profitability_next_candidate_selection_3156.md
  - docs/evidence/profitability_range_mean_reversion_v1_hold_park_decision_3162.md
  - docs/evidence/profitability_momentum_capture_v1_hold_park_decision_3166.md
  - docs/strategy/CDB_PROFITABILITY_SCENARIO_PACK_LIBRARY_V1.md
  - docs/strategy/CDB_PROFITABILITY_ARVP_BATCH_RUNNER_V1.md
  - docs/strategy/CDB_PROFITABILITY_EXECUTION_ECONOMICS_V1.md
  - core/replay/scenario_packs.py
impact_on_plan:
  - #3188 decision doc provides complete scenario-pack-first rationale reused here.
  - #3037/#3038/#3039 foundations are CLOSED; spec references their contracts without redefinition.
  - scenario_packs.py implements 5 deterministic packs; spec uses these as baseline.
  - FULL_STOP on BTCUSDT/MEXC/1m long-only confirmed; spec enforces NO_SAME_LOOP.
  - Dedupe search returned zero; follow-up issue can be created.
limitations:
  - repo-only; no SurrealDB/context-brain records used.
  - Known untracked foreign surfaces remain untouched.
  - This is a docs-only spec artifact; no candidate implementation is described or authorized.
```

---

## Bootloader-/Read-Order-Evidence

Canonical read-order executed according to `agents/AGENTS.md`:

1. `knowledge/governance/CDB_CONSTITUTION.md` — oberste Autoritaet: deterministisches, reproduzierbares System.
2. `knowledge/governance/CDB_GOVERNANCE.md` — Rollenmodell, Betriebsmodi, Change-Control.
3. `knowledge/governance/CDB_AGENT_POLICY.md` §4 — Write-Gates, Single-Writer Lock, HARD STOP.
4. `knowledge/governance/SYSTEM_INVARIANTS.md` — INV-001 bis INV-020: Fail-Closed, Determinismus, Contract Drift Protection.
5. `knowledge/CDB_KNOWLEDGE_HUB.md` — Shared Decisions & Agent Handoffs.
6. `docs/meta/WORKING_REPO_CANON.md` — Working Repo ist produktiver Canon; Status-SSOT-Rules.
7. `CURRENT_STATUS.md` — als Ledger behandelt, nicht als Live-Wahrheit.
8. `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` — LR remains NO-GO.
9. `docs/runbooks/CONTROL_REGISTER.md` — Stage `trade-capable` nicht Live-Go.
10. `agents/OPEN_CODE_AGENTS.md` — Brain Evidence Gate, Skill Routing.

**Operative Grenzen bestaetigt:**
- LR remains NO-GO. Keine Echtgeld-Freigabe.
- Board-Stage `trade-capable` orthogonal zu LR; autorisiert kein Live-Kapital.
- `DELIVERY_APPROVED.yaml` bleibt human-only.
- `CURRENT_STATUS.md` ist Ledger, nicht Live-Truth.

---

## Live-Lage

Stand: 2026-06-14 nach `git fetch origin --prune` und GH-Live-Pruefung:

| Item | Status | Ref |
|------|--------|-----|
| `#3189` | **OPEN** — dieser Spec-Slice | Ziel-Issue |
| `#3188` | **CLOSED** — Scenario-Pack-First axis selected | Vorgaenger |
| `#3186` | **CLOSED** — `NO_PROMOTABLE_EXISTING_CANDIDATE` | Vorgaenger |
| `#2985` | **OPEN** — Live-Roadmap Meta | North-Star Ref |
| `#1900` | **OPEN** — ARVP North-Star | Parent |
| `#3037` | **CLOSED** — Batch Runner v1 | Foundation |
| `#3038` | **CLOSED** — Scenario Pack Library v1 | Foundation |
| `#3039` | **CLOSED** — Execution Economics v1 | Foundation |
| Open PRs | **None** | Keine offenen Branches |
| HEAD | `3d51aef` (origin/main, fresh) | Sauberer Startpunkt |
| Working tree | Nur bekannte Untracked | Nicht im Scope |
| LR-Verdikt | **NO-GO** | Unveraendert |

---

## Problem Statement

Nach dem `FULL_STOP_ON_THIS_LOOP` auf BTCUSDT/MEXC/1m long-only (`#3170`) und dem Feststellen von `NO_PROMOTABLE_EXISTING_CANDIDATE` (`#3186`) hat die Discovery-Achse (`#3188`) **scenario-pack-first** als die staerkste legitime naechste Forschungsachse ausgewaehlt.

Was noch fehlt:

- **Keine konkrete Spec** dafuer, welche Scenario-Dimensionen ein Inventar brauchen.
- **Keine Economics Acceptance Gates** definiert, die ein Kandidat bestehen muss, bevor er implementiert wird.
- **Keine Evidence Requirements** pro Scenario-Dimension.
- **Keine Fail-Closed-Regeln** fuer unvollstaendige Kosten-/Slippage-/Fee-Annahmen.
- **Keine Stop Conditions**, die Scope-Drift in Candidate-Implementierung verhindern.

Dieses Artefakt schliesst genau diese Luecke: Es definiert die **pruefbare Research-Spec** fuer scenario-pack-first, ohne eine Strategie zu implementieren.

---

## Foundations Reused

Die folgenden geschlossenen Issue-Foundations werden referenziert, nicht neu definiert:

| Foundation | Status | Reuse in dieser Spec |
|------------|--------|---------------------|
| `#3037` — ARVP Batch Runner v1 | CLOSED | Batch-Manifest-Schema, Output-Bundle-Struktur, Failure-Semantik (BLOCKED/PARKED/FAILED) |
| `#3038` — Scenario Pack Library v1 | CLOSED | Szenario-Katalog-Schema, Stress-Domains (slippage, spread, partial fills, rejections, latency, feed gaps, volatility, liquidity) |
| `#3039` — Execution Economics v1 | CLOSED | Fee/Spread/Slippage-Modell, Net-Return-Felder, `ranking_ready=false`-Semantik |
| `core/replay/scenario_packs.py` | auf `main` | 5 deterministische Packs (baseline, pessimistic_execution, delayed_execution, low_liquidity, feed_gap) |
| `#3170` — Break-Even Boundary | CLOSED | Fee-Free-Proxy-Bewertung als Economics Gate Baseline |
| `#3168` — Post-Tri-Regime Axis Decision | CLOSED | Rahmen fuer nachste Forschungsachse nach Tri-Regime-PARK |

Die Foundations sind versioniert, auf `main` vorhanden und validiert. Diese Spec spezifiziert die **Luecke zwischen diesen Foundations und einer ausfuehrbaren Candidate-Pipeline** — naemlich die Acceptance-Gates.

---

## Scenario-Pack-First Scope

### Was diese Spec definiert

- **Scenario Inventory** — welche Dimensionen ein Inventar abdecken muss und welche Boundary-Werte pro Dimension gelten.
- **Minimum Scenario Pack Structure** — welche Felder/Pfade jedes Pack braucht, um vergleichbar zu sein.
- **Economics Acceptance Gates** — welche Wirtschaftlichkeitsschwellen ein Kandidat bestehen muss, bevor er implementiert oder rangiert wird.
- **Evidence Requirements** — welche Artefakte pro Scenario-Dimension und pro Kandidat existieren muessen.
- **Ranking Inputs** — was eingehen muss, bevor `ranking_ready=true` gelten darf.
- **Fail-Closed Semantik** — was passiert, wenn Kosten-/Slippage-/Fee-Annahmen fehlen.
- **Stop Conditions** — Bedingungen, bei denen dieser Research-Pfad sofort stoppt.
- **Next Bounded Research Slice** — der naechste ausfuehrbare Schritt.

### Was diese Spec NICHT ist

- **Keine Strategie-Implementierung.** Diese Spec definiert Gates. Sie implementiert keinen Kandidaten.
- **Kein Scenario-Runner.** Die technische Ausfuehrung bleibt in `core/replay/scenario_packs.py` und dem Batch Runner (#3037).
- **Kein neues Contract-Schema.** Bestehende Schemas aus #3037/#3038/#3039 werden referenziert.
- **Keine Ranking-Formel.** Diese Spec definiert Inputs; Ranking bleibt ein separater Schritt (#3040).
- **Kein Product-Complete-Claim.** Diese Spec macht das Produkt nicht vollstaendig.
- **Kein natural_paper_evidence Claim.**
- **Kein Live-Go / Echtgeld-Go.**

---

## Scenario Inventory

### Definitionsregel

Das Scenario Inventory muss alle Dimensionen umfassen, die einen systematischen Einfluss auf die Netto-Rendite eines Kandidaten haben koennen. Jede Dimension muss:

1. eine explizite **Boundary** (zulaessiger Wertebereich) definieren
2. eine **Baseline** (aktueller/standard Wert) benennen
3. eine **Evidence-Quelle** referenzieren
4. einen **Acceptance-Gate** (PASS/WARNING/FAILED/BLOCKED) definieren

### Inventar-Dimensionen (Minimum)

#### 1. Symbol Universe Boundary

| Feld | Wert |
|------|------|
| Boundary | BTCUSDT only (Baseline). Erweiterung nur nach dediziertem Symbol-Discovery-Slice. |
| Baseline | BTCUSDT — einzige durchgehend evidenzgestuetzte Symbol-Wahl. |
| Evidence | `#3156`, `#3164`, `#3166`, `#3170` (alle Candidate-Evidence auf BTCUSDT). |
| Gate | PASS: Kandidat ist auf BTCUSDT evidenzgestuetzt. WARNING: Kandidat nutzt andere Symbole ohne repo-backed Discovery. BLOCKED: Kandidat erfordert Symbole ohne repo-backed Dataset-Quality. |

#### 2. Timeframe / Window Boundary

| Feld | Wert |
|------|------|
| Boundary | 1m Baseline. Hoehere Timeframes (z.B. 5m, 15m) nur nach dediziertem Timeframe-Discovery-Slice. |
| Baseline | 1m — aktuell einzige durchgehend backtestbare Aufloesung. |
| Evidence | Roadmap §5.1; `#3035` Dataset Quality Gate. |
| Gate | PASS: 1m mit Dataset-Quality-Verification. WARNING: Hoeherer Timeframe ohne repo-backed Vergleich. BLOCKED: Timeframe ohne Dataset-Quality-Report. |

#### 3. Venue / Data-Quality Boundary

| Feld | Wert |
|------|------|
| Boundary | MEXC Baseline (historische Daten via Public API + WS Capture). Andere Venues nur nach Venue-Discovery-Slice. |
| Baseline | MEXC — einzige aktive Exchange-Integration. |
| Evidence | `#3170` Venue-Rescue-Verbot; ARVP Batch-Compare zeigt `venue_mismatch`-Konfundierung. |
| Gate | PASS: MEXC mit Dataset-Fingerprint. WARNING: Andere Venue ohne repo-backed Datenqualitaets-Abgleich. BLOCKED: Fehlende Dataset-Quality oder unaufgeloeste venue_mismatch-Konfundierung. |

#### 4. Regime Coverage Boundary

| Feld | Wert |
|------|------|
| Boundary | TREND, RANGE, HIGH_VOL_CHAOTIC (Baseline). CRISIS-Regime nicht im aktuellen Dataset. |
| Baseline | Multi-Regime aus `#3174` (run_003) und `#3176` (run_004): TREND 2676, RANGE 3366, HVC 1533 Observationen. |
| Evidence | `#3174` (run_003 candles), `#3176` (run_004 BUY-signals), `#3180` (run_005 PnL attribution). |
| Gate | PASS: Alle erwarteten Regime abgedeckt mit Evidence. WARNING: CRISIS-Regime fehlt (bekannte Data-Limitierung). FAILED: Keine Regime-Attribution moeglich. |

#### 5. Volatility / Liquidity Boundary

| Feld | Wert |
|------|------|
| Boundary | MEXC BTCUSDT Spot-Liquiditaet (Baseline). Niedrigere Liquiditaet = hoeheres Slippage-Risiko. |
| Baseline | `#3032` MEXC-Sample-Expansion; Orderbuch-Tiefe wird aktuell nicht gemessen. |
| Evidence | `#3032` Sample-Expansion; Szenario `low_liquidity` aus `scenario_packs.py`. |
| Gate | PASS: Slippage-Modell beruecksichtigt Liquiditaetsszenario. WARNING: Kein Liquidity-Shock-Szenario definiert. BLOCKED: Kein nachvollziehbares Slippage-Modell. |

#### 6. Fee / Slippage Economics Boundary

| Feld | Wert |
|------|------|
| Boundary | Fee-Free Proxy (gross_return_r) muss >= 0.0R fuer Promotion. Slippage-Modell muss pessimistisch sein. |
| Baseline | `#3170`: Alle Kandidaten negativ bei Fee-Free Proxy. Slippage kein Rescue-Faktor. |
| Evidence | `#3170` Boundary-Tabelle; `#3039` Economics Model Schema. |
| Gate | PASS: Fee-Free Proxy >= 0.0R UND Slippage-Modell definiert. WARNING: Fee-Free Proxy >= 0.0R aber Slippage nicht modelliert. FAILED: Fee-Free Proxy < 0.0R. BLOCKED: Keine Fee/Slippage-Annahme vorhanden. |

#### 7. Directionality Boundary

| Feld | Wert |
|------|------|
| Boundary | Long-only Baseline. Short-capable als Zukunftsthema markiert, nicht implementiert. |
| Baseline | Long-only — einzige repobacked Richtung (alle drei PARK-Kandidaten long-only). |
| Evidence | `#3162` (short-side blocked by simulator constraints), `#3166` (long-only first pass). |
| Gate | PASS: Long-only mit Evidence. WARNING: Short-capable ohne Repo-Evidence. BLOCKED: Short-side erfordert Simulator-Aenderung und ist nicht ausfuehrbar. |

---

## Economics Acceptance Gates

### Gate 1: No candidate promotion from stale PARK states

- Ein Kandidat im `PARK`-Status darf nicht in die Pipeline oder ins Ranking zurueckkehren, ohne dass eine neue Governance-Entscheidung oder neue substanzielle Evidence vorliegt.
- **Evidence:** Live-GitHub-Issue-Status pro Kandidat; `ranking_ready=false` aus Seed-Artifakten.
- **Fail-closed:** Bei unklarem Issue-Status: BLOCKED.

### Gate 2: No same-loop BTCUSDT/MEXC/1m long-only continuation

- `#3170` hat FULL_STOP fuer diese Schleife erklaert. Der Spec-Schritt darf keinen Candidate #4 in diesem Loop definieren.
- **Evidence:** `docs/evidence/profitability_break_even_boundary_cost_slippage_sensitivity_3170.md` §FULL_STOP_ON_THIS_LOOP.
- **Fail-closed:** Jeder Candidate, der BTCUSDT/MEXC/1m long-only ist, wird BLOCKED ohne separate Governance-Lift-Entscheidung.

### Gate 3: Economics gate before strategy implementation

- Ein Kandidat darf erst implementiert werden, nachdem der Economics Gate durchlaufen ist.
- **Bedeutung:** Die Scenario-Pack-First-Philosophie verlangt: Gates vor Implementierung.
- **Fail-closed:** Bei fehlendem Economics-Assessment: BLOCKED.

### Gate 4: Scenario pack must be replayable or explicitly marked evidence-blocked

- Jedes Szenario muss auf deterministischen Inputs basieren und replaybar sein.
- Falls ein Szenario nicht replaybar ist, muss es explizit als `evidence_blocked` markiert werden.
- **Reference:** `scenario_packs.py` existiert mit 5 deterministischen Packs.
- **Fail-closed:** Nicht replaybare Szenarien ohne `evidence_blocked`-Flag sind BLOCKED.

### Gate 5: ranking_ready=false unless numeric economics inputs complete

- `ranking_ready` darf nur `true` sein, wenn alle Economics-Inputs (fee, spread, slippage, cost attribution) vollstaendig sind.
- **Reference:** `#3039` Economics-Model-Schema, `ranking_ready`-Feld.
- **Fail-closed:** Fehlende Economics-Inputs -> `ranking_ready=false`.

### Gate 6: Fail-closed on missing cost/slippage/fee assumptions

- Fehlen Fee-, Slippage- oder Kostenannahmen, ist das Economics Assessment BLOCKED.
- Kein Net-Return ohne vollstaendige Cost Attribution.
- **Reference:** `#3039` Assessment-Design §fail-closed.
- **Fail-closed:** Fehlende Annahme -> BLOCKED.

### Gate 7: Fee-free proxy must be non-negative for any promotion

- Ein Kandidat muss bei der Fee-Free Proxy (gross_return_r) >= 0.0R sein, um promotable zu sein.
- **Evidence:** `#3170` Boundary-Tabelle. Alle drei PARK-Kandidaten negativ bei Fee-Free Proxy.
- **Fail-closed:** Keine Promotion bei negativem Fee-Free Proxy. Zusaetzlich: Economics Gate verhindert Implementierung.

### Gate 8: Stress resilience — baseline vs pessimistic scenarios comparison

- Ein Kandidat muss einen Stress-Vergleich zwischen Baseline- und pessimistischen Szenarien bestehen.
- **Reference:** `#3038` Scenario Pack Library; `scenario_packs.py` (pessimistic_execution, low_liquidity, feed_gap).
- **Fail-closed:** Ohne Stress-Vergleich -> `ranking_ready=false`.

---

## Evidence Requirements

### Per-Scenario-Dimension

Jede Inventar-Dimension (1-7) muss ein Evidence-Artefakt haben:

1. **Symbol Universe:** Referenzierte Candidate-Evidence-Dokumente und Dataset-Quality-Report.
2. **Timeframe:** Dataset-Quality-Report mit Fingerprint und Quality-Verdict.
3. **Venue:** Dataset-Quality-Report; optionaler Venue-Vergleichsbericht.
4. **Regime Coverage:** Regime-Scorecard aus Batch-Compare/Calibration.
5. **Volatility/Liquidity:** Stress-Summary aus `scenario_stress_summary.v1.schema.json`.
6. **Fee/Slippage:** Economics-Assessment aus `execution_economics_assessment.v1.schema.json`.
7. **Directionality:** Explizite Ausschluss-/Einschluss-Dokumentation im Candidate Evidence Packet.

### Per-Candidate-Stress

Ein Kandidat muss pro Szenario-Pack aus `#3038` eine Stress-Summary haben:

- Slippage Shock: Net-Return-Delta vs Baseline.
- Spread Expansion: Net-Return-Delta vs Baseline.
- Partial Fills: Auswirkung auf Fill-Rate und Net-PnL.
- Rejections: Auswirkung auf Order-Success-Rate.
- Latency: Auswirkung bei Signalverzoegerung.
- Feed Gaps: Auswirkung bei Datenluecken.
- Volatility Stress: Hohe Volatilitaet als Stress-Variable.
- Liquidity Stress: Niedrige Liquiditaet als Stress-Variable.

**Fail-closed:** Fehlt eine Stress-Summary fuer ein im Inventar definiertes Szenario, gilt der Candidate als `BLOCKED` oder der Gate als `WARNING` mit explizitem Hinweis.

---

## Ranking Inputs and Fail-Closed Semantics

### Required Inputs before ranking_ready=true

1. Gross return (R, PnL Quote) — vollstaendig.
2. Fee-adjusted return (R, PnL Quote) — vollstaendig.
3. Fee model basis — dokumentiert.
4. Spread model basis — dokumentiert oder explizit als `0.0` markiert.
5. Slippage model basis — dokumentiert oder explizit als `0.0` markiert.
6. Scenario stress summary — vorhanden oder `evidence_blocked` gesetzt.
7. Fee-free proxy — berechnet und bewertet.

### Fail-Closed Semantics

| Condition | Result |
|-----------|--------|
| Missing gross return | BLOCKED |
| Missing fee-adjusted return | BLOCKED |
| Missing fee model basis | BLOCKED |
| Spread cost undeclared | BLOCKED |
| Slippage cost undeclared | BLOCKED |
| Stress scenario incomplete | WARNING (mindestens) |
| Fee-free proxy negative | FAILED (keine Promotion) |
| `ranking_ready=false` | Kein Ranking oder Promotion |

---

## Validation Gates

| Gate | Checks | Artefakt |
|------|--------|----------|
| Schema validation | Batch Manifest, Scenario Catalog, Economics Model, Stress Summary | CI-Lauf (make mcp-config-validate oder direktes JSON-Validate) |
| Dataset Quality | Fingerprint vorhanden, Quality Verdict vorhanden | Dataset-Quality-Report |
| Economics Completeness | Alle Cost-Attribution-Felder ausgefuellt | Economics Assessment |
| Stress Coverage | Alle Inventory-Dimensionen mit Stress-Summary abgedeckt | Stress Summary |
| Rankings-Ready | `ranking_ready=false` ausser alle Inputs komplett | Evidence Packet |
| Same-Loop Guard | Kandidat ist NICHT BTCUSDT/MEXC/1m long-only | Candidate-Vertrag prüft Symbol/Venue/TF/Direction |

---

## Stop Conditions

Die folgenden Bedingungen fuehren zu einem sofortigen STOP dieses Research-Pfads:

| Stop Condition | Ausloeser | Aktion |
|----------------|-----------|--------|
| S1 | Same-Loop Candidate #4 auf BTCUSDT/MEXC/1m long-only | STOP — diese Spec definiert keinen Kandidaten in dieser Schleife |
| S2 | primary_breakout_v1 Rescue- oder Tuning-Versuch | STOP — primary_breakout_v1 bleibt PARKED |
| S3 | Strategie-Implementierung statt Spec | STOP — Scenario-pack-first ist keine Strategie-Implementierung |
| S4 | Live-Go / Echtgeld-Go impliziert | STOP — LR remains NO-GO |
| S5 | Product-Complete Claim | STOP — kein Product-Complete |
| S6 | natural_paper_evidence Claim | STOP — controlled_lab_evidence und Spec sind kein natural_paper_evidence |
| S7 | Runtime/Docker/DB/MCP/Secrets-Arbeit | STOP — nicht im Scope |
| S8 | Parameter-Optimierung | STOP — nicht im Scope |
| S9 | Neue Contract-Schemas ohne Foundation | STOP — #3037/#3038/#3039 sind Foundation |
| S10 | Scope-Drift in Symbol/Venue/Timeframe-Expansion | STOP — Baseline bleibt BTCUSDT/MEXC/1m |

---

## Next Bounded Research Slice

**Recommended next slice:** Build first economics-gated scenario inventory from #3189 spec.

### Scope

- Select concrete scenarios from `scenario_packs.py` (baseline, pessimistic_execution, delayed_execution, low_liquidity, feed_gap).
- Map them to the Scenario Pack Library catalog schema (`#3038`).
- Define per-candidate Economics Assessment boundaries (`#3039`).
- Produce a scenario inventory with acceptance gate status per dimension.
- Map replayability vs evidence-blocked status per scenario.

### Out of scope

- No strategy implementation.
- No candidate ranking.
- No runtime.
- No Live-Go / Echtgeld-Go.
- No Contract-Schema-Änderung.

### Acceptance

- Scenario inventory document with per-dimension acceptance gates.
- Economics gate map showing which candidates would PASS/WARNING/FAILED/BLOCKED.
- Replayability/evidence gaps documented.
- Stop conditions defined per candidate.

---

## Follow-up Issue

**To be created after dedupe verification:**

```
Title: [ARVP][SCENARIO] Build first economics-gated scenario inventory from #3189 spec
Parent: #1900
Refs: #3189, #3188, #3186, #2985
Foundations: #3037, #3038, #3039
```

**Dedupe result:** Three dedupe searches executed — zero open issues found matching "scenario pack first research slice", "scenario inventory economics gates", or "ARVP scenario-pack-first". Follow-up issue can be created.

**Body requirements:**
- Parent: #1900
- Refs: #3189, #3188, #3186, #2985
- Objective: build the first scenario inventory/evidence map from the #3189 spec.
- Scope: docs/evidence only unless explicitly justified by existing tooling.
- Out of scope: strategy implementation, optimization, runtime, Docker, DB/MCP, Live-Go, Echtgeld-Go.
- Acceptance: scenario inventory, economics gate map, replayability/evidence gaps, stop conditions.
- Safety: LR remains NO-GO.

---

## Safety Boundaries

- LR remains NO-GO.
- Board stage trade-capable is not Live-Go.
- No Product-Complete claim.
- No natural_paper_evidence claim.
- No Live-Go / Echtgeld-Go.
- No same-loop Candidate #4 on BTCUSDT/MEXC/1m long-only.
- Scenario-pack-first is a research spec, not a strategy implementation.
- No primary_breakout_v1 rescue path is opened.
- No runtime, Docker, workflow, DB, MCP, or secrets work is authorized.
- No parameter optimization or strategy tuning is authorized.
- No #1905 unpark follows from this spec.
- No Contract-Schema change is authorized by this spec.

---

## Restunsicherheiten

1. Die Scenario-Inventar-Dimensionen sind ein Minimum-Set. Wenn spaetere Arbeit zeigt, dass z.B. eine Correlation-Dimension fehlt, muss das Inventar erweitert werden. Eine Erweiterung darf jedoch nur durch einen dedizierten Issue erfolgen, nicht durch informelle Scope-Expansion.
2. Die Acceptance Gates sind auf dem aktuellen repo-backed Wissensstand definiert. Sollte spaetere Evidence zeigen, dass ein Gate zu streng oder zu schwach ist, kann eine Anpassung per Governance-Entscheidung erfolgen.
3. Der Scenario Pack Library Catalog (`#3038`) definiert 8 Stress-Domains, aber nicht alle muessen fuer jeden Kandidaten ausfuellbar sein. Diese Spec fordert `evidence_blocked`-Flag fuer nicht ausfuellbare Szenarien, was eine ehrliche Track-Record-Einschaetzung erlaubt.
4. Die Fee-Free-Proxy-Regel (Gate 7) ist eine harte Boundary. Ein Kandidat mit negativem Fee-Free Proxy ist nicht promotable. Ob ein Kandidat mit schwach positivem Fee-Free Proxy promotable ist, bleibt eine spaetere Governance-Entscheidung.
5. Der Follow-up Issue muss sauber abgrenzen, dass er die Foundations `#3037/#3038/#3039` referenziert und nicht neu definiert. Falls die Foundations-Luecke groesser ist als angenommen, muss der Issue auf HOLD gehen.

---

## References

- `docs/evidence/arvp_post_tri_regime_candidate_discovery_axis_3188.md`
- `docs/evidence/arvp_next_candidate_selection_after_primary_breakout_park_3186.md`
- `docs/evidence/arvp_roadmap_reconcile_after_primary_breakout_park_2985_1900.md`
- `docs/evidence/profitability_break_even_boundary_cost_slippage_sensitivity_3170.md`
- `docs/evidence/profitability_post_3166_tri_regime_park_next_axis_decision_3168.md`
- `docs/evidence/profitability_next_candidate_selection_3156.md`
- `docs/evidence/profitability_range_mean_reversion_v1_hold_park_decision_3162.md`
- `docs/evidence/profitability_momentum_capture_v1_hold_park_decision_3166.md`
- `docs/strategy/CDB_PROFITABILITY_SCENARIO_PACK_LIBRARY_V1.md`
- `docs/strategy/CDB_PROFITABILITY_ARVP_BATCH_RUNNER_V1.md`
- `docs/strategy/CDB_PROFITABILITY_EXECUTION_ECONOMICS_V1.md`
- `core/replay/scenario_packs.py`
- `docs/roadmaps/ARVP_TO_LIVE_GO_ROADMAP_2026-06.md`
- `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
- `docs/runbooks/CONTROL_REGISTER.md`
