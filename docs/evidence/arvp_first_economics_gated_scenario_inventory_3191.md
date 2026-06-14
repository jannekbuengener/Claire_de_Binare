# ARVP First Economics-Gated Scenario Inventory

**Issue:** [#3191](https://github.com/jannekbuengener/Claire_de_Binare/issues/3191)
**Parent:** [#1900](https://github.com/jannekbuengener/Claire_de_Binare/issues/1900)
**Refs:** [#3189](https://github.com/jannekbuengener/Claire_de_Binare/issues/3189), [#3188](https://github.com/jannekbuengener/Claire_de_Binare/issues/3188), [#3186](https://github.com/jannekbuengener/Claire_de_Binare/issues/3186), [#2985](https://github.com/jannekbuengener/Claire_de_Binare/issues/2985)
**Foundations:** [#3037](https://github.com/jannekbuengener/Claire_de_Binare/issues/3037), [#3038](https://github.com/jannekbuengener/Claire_de_Binare/issues/3038), [#3039](https://github.com/jannekbuengener/Claire_de_Binare/issues/3039)
**Decision date:** 2026-06-14
**Status:** DONE_MERGED_SCENARIO_INVENTORY_READY

---

## Brain Evidence

```
brain_source: repo-only
brain_status: not-used
tools_or_queries:
  - read: vollstaendiger Bootloader (AGENTS.md, agents/AGENTS.md, WORKING_REPO_CANON.md)
  - read: CURRENT_STATUS.md, CONTROL_REGISTER.md, LR-AUDIT-STATUS-2026-03-05.md
  - bash: git fetch origin --prune, git status -sb, git rev-parse HEAD, git rev-parse origin/main
  - bash: gh pr list --state open, gh issue view 3191, 3189, 3188, 1900
  - bash: gh issue list --state open --search (3 dedupe searches)
  - read: docs/evidence/arvp_scenario_pack_first_research_spec_3189.md
  - read: docs/evidence/arvp_post_tri_regime_candidate_discovery_axis_3188.md
  - read: docs/evidence/arvp_next_candidate_selection_after_primary_breakout_park_3186.md
  - read: docs/evidence/arvp_roadmap_reconcile_after_primary_breakout_park_2985_1900.md
  - read: docs/strategy/CDB_PROFITABILITY_SCENARIO_PACK_LIBRARY_V1.md
  - read: docs/strategy/CDB_PROFITABILITY_ARVP_BATCH_RUNNER_V1.md
  - read: docs/strategy/CDB_PROFITABILITY_EXECUTION_ECONOMICS_V1.md
  - read: core/replay/scenario_packs.py
  - read: docs/evidence/profitability_break_even_boundary_cost_slippage_sensitivity_3170.md
  - read: docs/evidence/profitability_post_3166_tri_regime_park_next_axis_decision_3168.md
records_or_results:
  - git: HEAD=7c119507 (origin/main, fast-forwarded)
  - gh: #3191 OPEN (leerer Body, keine Comments)
  - gh: #3189 CLOSED (Spec gemergt via PR #3192)
  - gh: #3188 CLOSED (Discovery gemergt via PR #3190)
  - gh: #1900 OPEN (Parent Epic)
  - gh: 0 open PRs, 0 dedupe matches fuer follow-up
  - Spec #3189 vollstaendig auf main: 7 Inventory-Dimensionen, 8 Economics Gates, 10 Stop Conditions
  - scenario_packs.py: 5 deterministische Packs (baseline, pessimistic_execution, delayed_execution, low_liquidity, feed_gap)
  - Alle 3 PARK-Kandidaten negativ bei Fee-Free Proxy (PB1: -0.075, RMR: -0.347, MC1: -0.206)
repo_crosscheck:
  - Alle foundation evidence/strategy/contract docs auf main vorhanden
  - Alle conditional files vorhanden (scenario_packs.py + 2 evidence docs)
  - Spec #3189 liefert direktes Template fuer Inventory-Dimensionen und Gates
impact_on_plan:
  - Inventory kann vollstaendig docs-only aus vorhandener Evidence gebaut werden
  - Kein Replay-Run oder Runtime-Zugriff erforderlich
  - SCC: 5/5 Packs REPLAYABLE, kein EVIDENCE_BLOCKED
  - Staerkster Gap: fehlender Stress-Vergleich (Slippage=0.0 in allen Assessments)
limitations:
  - repo-only; kein SurrealDB/Context-Brain Evidence
  - Working Tree: bekannte Fremdflaechen (.opencode/plans/, docs/decisions/)
  - Dieses Inventory ist Evidence-Mapping, keine Strategie-Implementierung
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

Stand: 2026-06-14 nach `git fetch origin --prune`, Fast-Forward auf `origin/main` und GH-Live-Pruefung:

| Item | Status | Ref |
|------|--------|-----|
| `#3191` | **OPEN** — dieser Inventory-Slice | Ziel-Issue |
| `#3189` | **CLOSED** — Spec gemergt via PR #3192 (`7c119507`) | Spec-Quelle |
| `#3188` | **CLOSED** — Discovery Axis gemergt via PR #3190 (`3d51aef4`) | Vorgaenger |
| `#3186` | **CLOSED** — `NO_PROMOTABLE_EXISTING_CANDIDATE` | Vorgaenger |
| `#1900` | **OPEN** — ARVP North-Star Epic | Parent |
| `#2985` | **OPEN** — Live-Roadmap Meta | North-Star Ref |
| Foundation Issues | **ALLE CLOSED** (#3037, #3038, #3039) | Contracts auf main |
| Open PRs | **None** | Saubere Startflaeche |
| HEAD | `7c119507` (origin/main, fast-forwarded) | Sauberer Startpunkt |
| Working tree | Nur bekannte Untracked (`.opencode/plans/`, `docs/decisions/`) | Nicht im Scope |
| LR-Verdikt | **NO-GO** | Unveraendert |
| Board Stage | `trade-capable` | Nicht Live-Go |

---

## Scenario Inventory

### Dimension 1: Symbol Universe Boundary

| Feld | Wert |
|------|------|
| Boundary | BTCUSDT only (Baseline). Erweiterung nur nach dediziertem Symbol-Discovery-Slice. |
| Baseline | BTCUSDT — einzige durchgehend evidenzgestuetzte Symbol-Wahl. |
| Evidence | `#3156`, `#3164`, `#3166`, `#3170` (alle Candidate-Evidence auf BTCUSDT). |
| Economics Gate | PASS: Kandidat ist auf BTCUSDT evidenzgestuetzt. WARNING: Kandidat nutzt andere Symbole ohne repo-backed Discovery. BLOCKED: Kandidat erfordert Symbole ohne repo-backed Dataset-Quality. |
| Replayability Status | REPLAYABLE — BTCUSDT 1m Dataset vorhanden (run_003/004/005). |
| Evidence Status | EVIDENCE_READY — alle drei Candidates auf BTCUSDT belegt. |
| Stop Condition if Failed | S10 (Scope-Drift in Symbol-Expansion) |
| Next Action | Baseline halten. Keine Symbol-Expansion ohne dedizierten Issue. |

### Dimension 2: Timeframe / Window Boundary

| Feld | Wert |
|------|------|
| Boundary | 1m Baseline. Hoehere Timeframes (5m, 15m) nur nach dediziertem Timeframe-Discovery-Slice. |
| Baseline | 1m — aktuell einzige durchgehend backtestbare Aufloesung mit Dataset-Quality. |
| Evidence | Roadmap §5.1; `#3035` Dataset Quality Gate. |
| Economics Gate | PASS: 1m mit Dataset-Quality-Verification. WARNING: Hoeherer Timeframe ohne repo-backed Vergleich. BLOCKED: Timeframe ohne Dataset-Quality-Report. |
| Replayability Status | REPLAYABLE — 1m Replay-Harness auf main (run_003/004/005). |
| Evidence Status | EVIDENCE_READY — 1m Dataset vorhanden und validiert. |
| Stop Condition if Failed | S10 (Scope-Drift in Timeframe-Expansion) |
| Next Action | Baseline halten. Hoehere Timeframes nur nach Datensatz-Beschaffung (#3031). |

### Dimension 3: Venue / Data-Quality Boundary

| Feld | Wert |
|------|------|
| Boundary | MEXC Baseline. Andere Venues nur nach Venue-Discovery-Slice. |
| Baseline | MEXC — einzige aktive Exchange-Integration. |
| Evidence | `#3170` Venue-Rescue-Verbot; ARVP Batch-Compare zeigt `venue_mismatch`-Konfundierung. |
| Economics Gate | PASS: MEXC mit Dataset-Fingerprint. WARNING: Andere Venue ohne repo-backed Datenqualitaets-Abgleich. BLOCKED: Fehlende Dataset-Quality oder unaufgeloeste venue_mismatch-Konfundierung. |
| Replayability Status | REPLAYABLE — MEXC 1m Capture vorhanden. |
| Evidence Status | PARTIAL — Dataset-Fingerprint vorhanden, aber venue_mismatch-Konfundierung nicht vollstaendig aufgeloest. |
| Stop Condition if Failed | S10 (Scope-Drift in Venue-Expansion) |
| Next Action | Bei Bedarf: Venue-Vergleichsbericht aus Batch-Compare-Evidence ableiten. |

### Dimension 4: Regime Coverage Boundary

| Feld | Wert |
|------|------|
| Boundary | TREND, RANGE, HIGH_VOL_CHAOTIC (Baseline). CRISIS-Regime nicht im aktuellen Dataset. |
| Baseline | Multi-Regime aus `#3174` (run_003) und `#3176` (run_004): TREND 2676, RANGE 3366, HVC 1533 Observationen. |
| Evidence | `#3174` (run_003 candles), `#3176` (run_004 BUY-signals), `#3180` (run_005 PnL attribution). |
| Economics Gate | PASS: Alle erwarteten Regime abgedeckt mit Evidence. WARNING: CRISIS-Regime fehlt (bekannte Data-Limitierung). FAILED: Keine Regime-Attribution moeglich. |
| Replayability Status | REPLAYABLE — run_003/004/005 haben Regime-Attribution bewiesen. |
| Evidence Status | EVIDENCE_READY — Regime-Scorecard aus run_005 vorhanden. |
| Stop Condition if Failed | Keine — CRISIS-Regime ist bekannte Data-Limitierung, kein Stop-Grund. |
| Next Action | CRISIS-Regime als bekannte Lücke dokumentieren; nicht blockierend. |

### Dimension 5: Volatility / Liquidity Boundary

| Feld | Wert |
|------|------|
| Boundary | MEXC BTCUSDT Spot-Liquiditaet (Baseline). Niedrigere Liquiditaet = hoeheres Slippage-Risiko. |
| Baseline | Aktuelle Orderbuch-Tiefe wird nicht gemessen. Slippage=0.0 in allen Assessments. |
| Evidence | `#3032` Sample-Expansion; Szenario `low_liquidity` aus `scenario_packs.py` (fill_depth_factor=0.3). |
| Economics Gate | PASS: Slippage-Modell beruecksichtigt Liquiditaetsszenario. WARNING: Kein Liquidity-Shock-Szenario definiert. BLOCKED: Kein nachvollziehbares Slippage-Modell. |
| Replayability Status | SPEC_READY — `low_liquidity` Pack existiert in scenario_packs.py, aber nie fuer PARK-Kandidaten ausgefuehrt. |
| Evidence Status | MISSING — kein Stress-Vergleich baseline vs low_liquidity existiert. |
| Stop Condition if Failed | Keine — Gap ist bekannt, Inventory dokumentiert ihn. |
| Next Action | Replay-Run mit `low_liquidity` Pack auf primary_breakout_v1. |

### Dimension 6: Fee / Slippage Economics Boundary

| Feld | Wert |
|------|------|
| Boundary | Fee-Free Proxy (gross_return_r) muss >= 0.0R fuer Promotion. Slippage-Modell muss definiert sein. |
| Baseline | `#3170`: Alle Kandidaten negativ bei Fee-Free Proxy (PB1: -0.075, RMR: -0.347, MC1: -0.206). Slippage=0.0 in allen Assessments. |
| Evidence | `#3170` Boundary-Tabelle; `#3039` Economics Model Schema; 3 Execution Economics JSONs auf main. |
| Economics Gate | PASS: Fee-Free Proxy >= 0.0R UND Slippage-Modell definiert. WARNING: Fee-Free Proxy >= 0.0R aber Slippage nicht modelliert. FAILED: Fee-Free Proxy < 0.0R. BLOCKED: Keine Fee/Slippage-Annahme vorhanden. |
| Replayability Status | REPLAYABLE — Fee-Berechnung ist deterministisch aus Trade-Log. |
| Evidence Status | PARTIAL — Fee-Daten vorhanden, Slippage=0.0 in allen Assessments (Spread/Slippage nie decomposed). |
| Stop Condition if Failed | S4 (wenn Economics Gate fuer Promotion umgangen wird) |
| Next Action | Slippage-Modell definieren (#3039 Execution Economics Model anwenden). |

### Dimension 7: Directionality Boundary

| Feld | Wert |
|------|------|
| Boundary | Long-only Baseline. Short-capable als Zukunftsthema markiert, nicht implementiert. |
| Baseline | Long-only — einzige repobacked Richtung (alle drei PARK-Kandidaten long-only). |
| Evidence | `#3162` (short-side blocked by simulator constraints), `#3166` (long-only first pass). |
| Economics Gate | PASS: Long-only mit Evidence. WARNING: Short-capable ohne Repo-Evidence. BLOCKED: Short-side erfordert Simulator-Aenderung und ist nicht ausfuehrbar. |
| Replayability Status | OUT_OF_SCOPE — Short-Side ist simulator-blocked, kein legitimer Inventory-Gegenstand. |
| Evidence Status | EVIDENCE_READY — Short-Side Blockade ist dokumentiert. |
| Stop Condition if Failed | Keine — Boundary ist bekannt, Inventory dokumentiert ihn korrekt. |
| Next Action | Short-Side bleibt blocked bis Simulator-Arbeit erfolgt. Kein Action-Item aus diesem Inventory. |

---

## Economics Gate Map

| Gate | Bedingung | Status fuer PARK-Kandidaten | Evidence | Fail-Closed |
|------|-----------|----------------------------|----------|-------------|
| G1 | Keine stale PARK-Promotion | **PASS** — alle 3 Kandidaten PARKED, keine Promotion | Issue-Status auf GitHub | BLOCKED bei unklarem Status |
| G2 | No same-loop BTCUSDT/MEXC/1m | **PASS** — Spec blockt Candidate #4 | #3170 FULL_STOP | BLOCKED bei same-loop |
| G3 | Economics vor Implementierung | **BLOCKED** — Gate existiert als Spec, nie auf Candidate angewandt | #3039 Economics Model | BLOCKED bei fehlendem Assessment |
| G4 | Scenario replayable oder evidence_blocked | **PASS** — 5/5 Packs replayable via scenario_packs.py | scenario_packs.py + Harness | BLOCKED ohne Flag |
| G5 | ranking_ready=false ohne vollst. Inputs | **PASS** — alle 3 haben `ranking_ready=false` | Seed JSONs auf main | ranking_ready=false |
| G6 | Fail-closed bei fehlenden Cost-Assumptions | **PARTIAL** — Fee-Daten vorhanden, Slippage=0.0 | Economics Assessments | BLOCKED bei fehlender Annahme |
| G7 | Fee-Free Proxy >= 0.0R | **FAIL** — alle 3 negativ | #3170 Boundary-Tabelle | Keine Promotion |
| G8 | Stress-Vergleich Baseline vs Pessimistic | **MISSING** — nie ausgefuehrt | scenario_packs.py existiert, kein Run | ranking_ready=false |

**Gate-Gesamtstatus:** 4 PASS, 1 PARTIAL, 1 BLOCKED, 1 FAIL, 1 MISSING

**Bedeutung:** Das Economics Gate System ist funktionsfaehig. Es blockt korrekt:
- G7 (negativer Fee-Free Proxy) blockt Promotion aller drei Kandidaten.
- G3 blockt Implementierung ohne Economics Assessment.
- G8 (fehlender Stress-Vergleich) ist der groesste operative Gap.

---

## Replayability Map

| Scenario Pack | Replayable | Deterministic | Evidence Source | Config Overrides |
|---------------|------------|---------------|-----------------|------------------|
| baseline | **REPLAYABLE** | Ja | `scenario_packs.py` | Keine (ungestoerter Replay) |
| pessimistic_execution | **REPLAYABLE** | Ja | `scenario_packs.py` | slippage=30bps, fill_rate=0.7, posture=pessimistic |
| delayed_execution | **REPLAYABLE** | Ja | `scenario_packs.py` | delay=1 bar, posture=delayed |
| low_liquidity | **REPLAYABLE** | Ja | `scenario_packs.py` | fill_depth=0.3, posture=low_liquidity |
| feed_gap | **REPLAYABLE** | Ja | `scenario_packs.py` | gap=2 bars |

**SCC (Scenario Coverage Check):** 5/5 Packs REPLAYABLE. Kein Pack ist EVIDENCE_BLOCKED. Alle Packs sind deterministisch und ueber `run_builtin_scenario_group()` aufrufbar.

**Einschraenkung:** REPLAYABLE bedeutet "technisch ausfuehrbar", nicht "ausgefuehrt und evidenziert". Der Stress-Vergleich (baseline vs pessimistisch) wurde fuer keinen der drei PARK-Kandidaten jemals ausgefuehrt.

---

## Evidence-Gap Map

| Gap | Typ | Schwere | Status | Naechster Schritt |
|-----|-----|---------|--------|-------------------|
| Slippage/Spread = 0.0 in allen Economics Assessments | Datenluecke | **HOCH** | OFFEN | Slippage-Modell aus #3039 anwenden; Replay mit pessimistic_execution |
| Stress-Vergleich nie ausgefuehrt (baseline vs pessimistic/feed_gap/low_liquidity) | Ausfuehrungsluecke | **HOCH** | OFFEN | Replay-Run mit scenario_packs auf primary_breakout_v1 |
| Kein Dataset-Quality-Report fuer kuenftige Kandidaten | Prozessluecke | **MITTEL** | OFFEN | #3035 Dataset Quality Gate anwenden |
| ranking_ready=false bei allen Kandidaten | Status | **KEIN GAP** | KORREKT | Fail-closed, kein Handlungsbedarf |
| Fee-Free Proxy < 0.0R fuer alle Kandidaten | Economics | **KEIN GAP** | BEKANNT | G7 blockt Promotion korrekt |
| Short-Side simulator-blocked | Constraint | **KEIN GAP** | BEKANNT | Dokumentiert in #3162 |
| CRISIS-Regime nicht im Dataset | Data | **NIEDRIG** | BEKANNT | Nicht blockierend fuer aktuellen Inventory-Scope |
| Keine Correlation-Dimension im Inventory | Spec | **NIEDRIG** | OFFEN | Kann in zukuenftiger Inventory-Erweiterung adressiert werden |

**Top-Evidence-Gap:** Fehlender Stress-Vergleich (Slippage=0.0 + kein scenario_packs-Run). Dieser Gap blockt ehrliches Ranking und Economics-Assessment.

---

## Candidate Stress Domains

Alle 8 Stress-Domains aus #3038 (Scenario Pack Library v1) gegen die drei PARK-Kandidaten:

| Domain | primary_breakout_v1 | range_mean_reversion_v1 | momentum_capture_v1 | Verfuegbarer Pack |
|--------|---------------------|------------------------|---------------------|-------------------|
| Slippage Shock | NOT_TESTED | NOT_TESTED | NOT_TESTED | `pessimistic_execution` (30bps) |
| Spread Expansion | NOT_TESTED | NOT_TESTED | NOT_TESTED | Kein eigener Pack |
| Partial Fills | NOT_TESTED | NOT_TESTED | NOT_TESTED | `pessimistic_execution` (fill=0.7) |
| Rejections | NOT_TESTED | NOT_TESTED | NOT_TESTED | Kein eigener Pack |
| Latency | NOT_TESTED | NOT_TESTED | NOT_TESTED | `delayed_execution` (1 bar) |
| Feed Gaps | NOT_TESTED | NOT_TESTED | NOT_TESTED | `feed_gap` (2 bars) |
| Volatility Stress | NOT_TESTED | NOT_TESTED | NOT_TESTED | Kein eigener Pack |
| Liquidity Stress | NOT_TESTED | NOT_TESTED | NOT_TESTED | `low_liquidity` (fill=0.3) |

**Befund:** 3 von 8 Domains haben einen existierenden scenario_pack (pessimistic_execution deckt Slippage+Partial Fills, delayed_execution deckt Latency, low_liquidity deckt Liquidity, feed_gap deckt Feed Gaps). 4 Domains haben keinen eigenen Pack (Spread, Rejections, Volatility Stress) bzw. sind durch andere Packs abgedeckt.

**Naechster Schritt:** Replay-Run mit den verfuegbaren Packs (baseline + pessimistic_execution + feed_gap) auf primary_breakout_v1 als Proof-of-Concept.

---

## Stop Conditions

| SC | Bedingung | Ausloeser | Status im Inventory |
|----|-----------|-----------|---------------------|
| S1 | Same-Loop Candidate #4 auf BTCUSDT/MEXC/1m long-only | Candidate-Vertrag prüft Symbol/Venue/TF/Direction | **Kein Trigger** — Inventory definiert keinen Kandidaten |
| S2 | primary_breakout_v1 Rescue- oder Tuning-Versuch | Evidence zeigt PARK-Versuch | **Kein Trigger** — primary_breakout_v1 bleibt PARKED |
| S3 | Strategie-Implementierung statt Spec | Scope-Check | **Kein Trigger** — Inventory ist Evidence-Mapping |
| S4 | Live-Go / Echtgeld-Go impliziert | LR-Verdikt | **Kein Trigger** — LR bleibt NO-GO |
| S5 | Product-Complete Claim | Claim-Check | **Kein Trigger** — nicht beansprucht |
| S6 | natural_paper_evidence Claim | Claim-Check | **Kein Trigger** — nicht beansprucht |
| S7 | Runtime/Docker/DB/MCP/Secrets-Arbeit | Scope-Check | **Kein Trigger** — nicht im Scope |
| S8 | Parameter-Optimierung | Scope-Check | **Kein Trigger** — nicht im Scope |
| S9 | Neue Contract-Schemas ohne Foundation | Foundation-Check | **Kein Trigger** — #3037/#3038/#3039 referenziert |
| S10 | Scope-Drift in Symbol/Venue/Timeframe-Expansion | Boundary-Check | **Kein Trigger** — Baseline bleibt BTCUSDT/MEXC/1m |

**Fazit:** Keine Stop Condition wird getriggert. Inventory bleibt sauber im Scope.

---

## Decision

1. **Scenario Inventory ist vollstaendig docs-only gebaut.** Alle 7 Dimensionen aus Spec #3189 sind mit konkreten Werten, Evidence-Quellen und Gates befuellt.

2. **Economics Gate System ist funktionsfaehig.** Es blockt korrekt:
   - G7 (Fee-Free Proxy < 0.0R) blockt Promotion aller drei PARK-Kandidaten.
   - G3 (Economics vor Implementierung) blockt Implementierung ohne Assessment.
   - Kein Gate wird umgangen oder ist fehlerhaft konfiguriert.

3. **5/5 Scenario Packs sind REPLAYABLE.** Kein EVIDENCE_BLOCKED. Die technische Infrastruktur (`scenario_packs.py` + `run_builtin_scenario_group()`) ist vorhanden und wartet auf Ausfuehrung.

4. **Groesster Evidence-Gap: fehlender Stress-Vergleich.** Slippage=0.0 in allen Assessments, kein scenario_packs-Run jemals ausgefuehrt. Dieser Gap blockt ehrliches Ranking und Economics-Assessment.

5. **Keine Stop Condition wird getriggert.** Inventory bleibt Scope-konform.

6. **LR remains NO-GO.** Keine Aenderung an Live-Readiness.

---

## Recommended Next Bounded Slice

**Controlled scenario-stress evidence closure for the existing PARKED candidates using existing scenario_packs/harness only, starting with baseline vs pessimistic/feed_gap where available.**

Begruendung:

- Das Inventory zeigt den groessten Evidence-Gap: fehlender Stress-Vergleich.
- `scenario_packs.py` + `core.replay.scenario_harness` existieren auf `main`.
- `primary_breakout_v1` ist der evidenzstaerkste Kandidat (hoechste Evidence-Tiefe).
- Ein Replay-Run mit `run_builtin_scenario_group(["baseline", "pessimistic_execution", "feed_gap"], ...)` kann den Gap schliessen.

**Nicht im Scope dieses Slices:**
- Kein Live-Go, kein Echtgeld-Go.
- Keine Strategie-Implementierung.
- Keine Optimierung.
- Keine Candidate-Promotion.
- Kein Same-Loop Candidate #4.
- Nur bestehende Harness/Scenario-Packs. Wenn Replay-Voraussetzungen fehlen: HOLD_EVIDENCE_BLOCKED statt improvisieren.

---

## Follow-up Issue

**Dedupe-Befund:** Drei dedizierte `gh issue list`-Suchen ergaben keine offenen Issues zum Thema "scenario inventory evidence gap", "economics gated scenario replayability" oder "ARVP scenario inventory". #3191 ist das einzige offene Issue in diesem Kontext.

**Erstelltes Issue:** `[ARVP][EVIDENCE] Close first scenario-inventory evidence gaps from #3191`

Body:
- Parent: #1900
- Refs: #3191, #3189, #3188, #3186, #2985
- Objective: close the bounded evidence gaps identified by the first scenario inventory.
- Scope: docs/evidence or read-only validation only, unless explicitly justified.
- Out of scope: strategy implementation, optimization, runtime, Docker, DB/MCP, Live-Go, Echtgeld-Go.
- Acceptance: evidence gap list, required inputs, validation gates, stop conditions.
- Safety: LR remains NO-GO.

---

## Safety Boundaries

- LR remains NO-GO.
- Board stage trade-capable is not Live-Go.
- No Product-Complete claim.
- No natural_paper_evidence claim.
- No Live-Go / Echtgeld-Go.
- No same-loop Candidate #4 on BTCUSDT/MEXC/1m long-only.
- This scenario inventory is evidence mapping, not strategy implementation.
- No primary_breakout_v1 rescue path is opened.
- No runtime, Docker, workflow, DB, MCP, or secrets work is authorized.
- No parameter optimization or strategy tuning is authorized.
- No #1905 unpark follows from this inventory.
- No Contract-Schema change is authorized by this inventory.

---

## Restunsicherheiten

1. **Slippage=0.0** ist der groesste operative Blocker. Ohne Slippage-Modell bleibt jeder Stress-Vergleich unvollstaendig.
2. **Stress-Vergleich nie ausgefuehrt.** Das Inventory kann nur konstatieren, dass die Packs existieren — ob sie fuer die PARK-Kandidaten aussagekraeftige Ergebnisse liefern, ist offen.
3. **4 von 8 Stress-Domains haben keinen eigenen scenario_pack** (Spread Expansion, Rejections, Volatility Stress). Diese koennen im Inventory nur als NOT_TESTED markiert werden.
4. **Dataset-Quality-Report (#3035) fehlt fuer alle Datensaetze.** Der naechste Slice (Stress-Replay) braucht zwingend einen Quality-Report, sonst ist das Ergebnis nicht vertrauenswuerdig.
5. **Die Inventory-Dimensionen sind ein Minimum-Set.** Sollte z.B. eine Correlation-Dimension fehlen, muss das Inventar per dediziertem Issue erweitert werden — nicht durch Scope-Expansion.

---

## References

- `docs/evidence/arvp_scenario_pack_first_research_spec_3189.md`
- `docs/evidence/arvp_post_tri_regime_candidate_discovery_axis_3188.md`
- `docs/evidence/arvp_next_candidate_selection_after_primary_breakout_park_3186.md`
- `docs/evidence/arvp_roadmap_reconcile_after_primary_breakout_park_2985_1900.md`
- `docs/evidence/profitability_break_even_boundary_cost_slippage_sensitivity_3170.md`
- `docs/evidence/profitability_post_3166_tri_regime_park_next_axis_decision_3168.md`
- `docs/strategy/CDB_PROFITABILITY_SCENARIO_PACK_LIBRARY_V1.md`
- `docs/strategy/CDB_PROFITABILITY_ARVP_BATCH_RUNNER_V1.md`
- `docs/strategy/CDB_PROFITABILITY_EXECUTION_ECONOMICS_V1.md`
- `core/replay/scenario_packs.py`
- `docs/roadmaps/ARVP_TO_LIVE_GO_ROADMAP_2026-06.md`
- `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
- `docs/runbooks/CONTROL_REGISTER.md`
