# ARVP Post-Tri-Regime Candidate Discovery Axis

**Issue:** #3188
**Decision date:** 2026-06-14
**Status:** DONE_MERGED_DISCOVERY_AXIS_SELECTED

---

## Brain Evidence

brain_source: repo-only
brain_status: not-used
tools_or_queries:
  - read: AGENTS.md, agents/AGENTS.md
  - read: full canonical read-order (governance, invariants, knowledge hub, working repo canon)
  - read: CONTROL_REGISTER.md, LR-AUDIT-STATUS-2026-03-05.md
  - bash: git fetch origin --prune, git status -sb, git rev-parse HEAD, git rev-parse origin/main
  - bash: gh pr list --state open, gh issue view 3188, 3186, 2985, 1900
  - bash: gh issue list --state open (three dedupe searches)
  - task: adjacent research surface scan (8 axis families)
  - task: seed evidence analysis (8 evidence files)
  - context.search x3 (0 hits)
records_or_results:
  - git: HEAD=origin/main=0738e7beecd6d30f276185a155230dc33577e2df
  - gh: #3188 OPEN, #3186 CLOSED, #2985 OPEN, #1900 OPEN
  - gh: no open PRs
  - context.search: 0 hits for #3188 / named candidate families / scenario+economics
repo_crosscheck:
  - docs/evidence/arvp_next_candidate_selection_after_primary_breakout_park_3186.md
  - docs/evidence/profitability_post_3166_tri_regime_park_next_axis_decision_3168.md
  - docs/evidence/profitability_break_even_boundary_cost_slippage_sensitivity_3170.md
  - docs/evidence/arvp_exit_regime_decay_diagnosis_3183.md
  - docs/evidence/profitability_next_candidate_selection_3156.md
  - docs/evidence/profitability_third_candidate_selection_3164.md
  - docs/evidence/profitability_range_mean_reversion_v1_hold_park_decision_3162.md
  - docs/evidence/profitability_momentum_capture_v1_hold_park_decision_3166.md
  - docs/strategy/CDB_PROFITABILITY_SCENARIO_PACK_LIBRARY_V1.md
  - docs/strategy/CDB_PROFITABILITY_ARVP_BATCH_RUNNER_V1.md
  - docs/strategy/CDB_PROFITABILITY_EXECUTION_ECONOMICS_V1.md
impact_on_plan:
  - No DB-backed context evidence was found; plan stays GitHub+repo-backed.
  - Existing closed spec surfaces #3037/#3038/#3039 make scenario-pack-first viable without reinventing contracts.
limitations:
  - git fetch origin --prune was executed post-PLAN; remote state is fresh.
  - HEAD==origin/main verified against freshly fetched remote.
  - Context KB search returned 0 hits; no additional DB-backed shortlist exists.

---

## Bootloader-/Read-Order-Evidence

Canonical read-order executed:
1. `knowledge/governance/CDB_CONSTITUTION.md` — oberste Autorität: Systemziel ist deterministisches, reproduzierbares Trading-System.
2. `knowledge/governance/CDB_GOVERNANCE.md` — Rollenmodell, Betriebsmodi, Change-Control.
3. `knowledge/governance/CDB_AGENT_POLICY.md` §4 — Write-Gates, Single-Writer Lock, HARD STOP.
4. `knowledge/governance/SYSTEM_INVARIANTS.md` — INV-001 bis INV-020: Fail-Closed, Determinismus, Contract Drift Protection.
5. `knowledge/CDB_KNOWLEDGE_HUB.md` — Shared Decisions & Agent Handoffs.
6. `docs/meta/WORKING_REPO_CANON.md` — Working Repo ist produktiver Canon; Status-SSOT-Rules.
7. `CURRENT_STATUS.md` — als Ledger behandelt, nicht als Live-Wahrheit.
8. `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` — LR remains NO-GO.
9. `docs/runbooks/CONTROL_REGISTER.md` — Stage `trade-capable` nicht Live-Go.
10. `agents/OPEN_CODE_AGENTS.md` — Brain Evidence Gate, Skill Routing.

**Operative Grenzen bestätigt:**
- LR remains NO-GO. Keine Echtgeld-Freigabe.
- Board-Stage `trade-capable` orthogonal zu LR; autorisiert kein Live-Kapital.
- `DELIVERY_APPROVED.yaml` bleibt human-only.

---

## Live-Lage

Stand: 2026-06-14 nach `git fetch origin --prune` und GH-Live-Pruefung:

| Item | Status | Ref |
|------|--------|-----|
| `#3188` | **OPEN** — dieser Discovery-Slice | Ziel-Issue |
| `#3186` | **CLOSED** — `NO_PROMOTABLE_EXISTING_CANDIDATE` | Vorgänger |
| `#2985` | **OPEN** — Live-Roadmap Meta | Parent-Ref |
| `#1900` | **OPEN** — ARVP North-Star | Parent-Ref |
| Open PRs | **None** | Keine offenen Branches |
| HEAD | `0738e7be...` (origin/main, fresh) | Sauberer Startpunkt |
| Working tree | Nur bekannte Untracked (`.opencode/plans/`, `docs/decisions/`) | Nicht im Scope |

---

## Problem Statement

Nach dem `FULL_STOP_ON_THIS_LOOP` auf BTCUSDT/MEXC/1m long-only (siehe `#3170`) und dem Feststellen von `NO_PROMOTABLE_EXISTING_CANDIDATE` (siehe `#3186`) ist der repo-backed Candidate-Pool auf dieser Achse erschöpft. Drei PARK-Kandidaten (`primary_breakout_v1`, `range_mean_reversion_v1`, `momentum_capture_v1`) demonstrieren einheitlich negative Ergebnisse, sogar am Fee-Free Proxy.

Die nächste legitime Forschungsachse darf nicht sein:
- ein gleicher Candidate #4 auf BTCUSDT/MEXC/1m long-only
- eine PB1-Rescue-Parameter-Optimierung
- eine unbewiesene Familienauswahl ohne repo-backed Evidenz

Stattdessen ist eine Discovery-/Spec-Entscheidung gefragt, die die nächste legitime Achse bestimmt, bevor irgendein Kandidat implementiert wird.

---

## Full-Stop Boundary

Der Full-Stop ist **explizit begrenzt** auf:

- **Symbol:** BTCUSDT
- **Venue:** MEXC
- **Timeframe:** 1m
- **Direction:** long-only

Diese Begrenzung bedeutet:
- Die Schleife ist nicht automatisch für andere Symbole, Venues oder Timeframes invalid.
- Andere Richtungen (Short, Long-Short) bleiben durch Simulator-/Replay-Constraints blockiert, nicht widerlegt.
- Der Full-Stop ist eine erzwungene Pause aus repo-backed Evidenz, kein absolutes Verbot von Krypto-Candidate-Arbeit.

---

## Research Axis Inventory

| Achse | Repo-Backed Stand | Urteil jetzt | Quelle |
|---|---|---|---|
| Symbol-Achse (multi-symbol) | Explizit erwähnt, nicht invalidiert | **Legitim als Spec, aber nicht stärkste nächste Achse.** `#3168` verwarf multi-symbol nur bis zur Economics-Klärung. `#3186` begrenzt den Full-Stop auf BTCUSDT/MEXC/1m. | `#3168` §Rejected, `#3186` §Restunsicherheiten |
| Timeframe-Achse (höhere TF) | Spec-Level, Roadmap bevorzugt >5min | **Legitim als Spec only.** Aktuelle Candidate-Evidence bleibt 1m-lastig. Reine eine Spec ohne Scenario-Acceptance-Struktur ist weniger wertvoll. | Roadmap §5.1 |
| Venue-Achse | Daten-/Venue-Evidence aus ARVP | **Legitim als Datenqualitäts-Spec, nicht als Rescue-These.** `#3170` verbietet Venue-Rescue aus der Economics-Slice. ARVP Batch-Compare zeigt `venue_mismatch`-Konfundierung. | `#3170`, `arvp_batch_compare_2971.md` |
| Direction-Achse (short) | Boundary-only | **Blockiert.** Short-side bleibt per `#3162`/`#3166` simulator-/replay-blocked. Kein legitimer nächster Slice ohne breitere Simulator-Arbeit. | `#3162`, `#3166` |
| Regime-Achse | Nur Namensanker | **Zu schwach für direkte Auswahl.** `regime_switch_v1` hat laut `#3164`/`#3186` keine Repo-Evidence. | `#3164`, `#3186` |
| Liquidity-Achse | Nur Namensanker | **Zu schwach für direkte Auswahl.** `liquidity_filtered_breakout_v1` hat laut `#3164`/`#3186` keine Repo-Evidence. | `#3164`, `#3186` |
| Scenario-Achse (scenario-pack-first) | Starke geschlossene Spec-Surfaces | **STÄRKSTE legitime nächste Achse.** `#3037`, `#3038`, `#3039` sind CLOSED und liefern Contracts, Batch-Runner-Schema und Economics-Layer. `scenario_packs.py` existiert als Core-Implementierung. | `docs/strategy/CDB_PROFITABILITY_SCENARIO_PACK_LIBRARY_V1.md` |
| Economics-Achse | Stark, aber bereits verbraucht als Gate | **Hard Gate, nicht nächste Achse.** `#3170` hat diese Achse bereits zum `FULL_STOP_ON_THIS_LOOP` ausgewertet. Wiederverwendung als eigener Slice ist Duplikation. | `#3170` |

---

## Evidence-Gap Map

| Gap | Natur | Status |
|-----|-------|--------|
| `regime_switch_v1` | Keinerlei Repo-Evidence | Muss Gap bleiben bis Dedicated-Discovery |
| `liquidity_filtered_breakout_v1` | Keinerlei Repo-Evidence | Muss Gap bleiben bis Dedicated-Discovery |
| Short-Side | Simulator-/Replay-blocked | Nicht widerlegt, aber nicht ausführbar |
| Venue/Microstructure Rescue | Keine gemessene Spread-/Slippage-Zerlegung | `#3170` hält das explizit offen; Gap bestätigt |
| Non-BTCUSDT / non-1m | Keine repo-backed Auswahl- und Acceptance-Logik | Macht multi-symbol als nächsten Spec-Slice nicht unmöglich, aber erfordert mehr Aufwand |
| Scenario-Economics-Kopplung | Spec existiert (`#3037/#3038/#3039`), aber noch kein Acceptance Gate definiert, das Candidate-Implementierung erst nach Scenario-Bestehen erlaubt | **Der schließbare Gap für diese Discovery-Achse** |

---

## Reject / Lower-Priority Reasons

### Endgültig für diesen Slice abgelehnt
- **Regime-Achse / Liquidity-Achse:** Keine Repo-Evidence. Direkte Auswahl ohne Discovery-Phase wäre ungedeckt.
- **Direction-Achse:** Aktuell durch Simulator-/Replay-Constraints blockiert.
- **Economics-Achse:** Bereits durch `#3170` als `FULL_STOP_ON_THIS_LOOP` ausgewertet. Wiederverwendung wäre Duplikation.

### Nachrangig / später valid
- **Symbol-Achse:** Gültige Alternative, falls der Maintainer bewusst eine Marktachse statt einer Methodenachse wählt. Aber: multi-symbol Discovery braucht zuerst eine Acceptance-Struktur (Scenario/Economics), sonst wiederholt sie den Fehler der Loop-Expansion vor Boundary-Verständnis.
- **Venue-Achse:** Datenqualitäts-Spec ist legitim, aber die Economics-Achse hat bereits gezeigt, dass Venue-Wechsel allein nicht ausreicht. Venue-Arbeit sollte nachgelagert zu Scenario-Findings kommen.
- **Timeframe-Achse:** Roadmap-konform, aber weniger wertvoll als eine Scenario-Acceptance-Struktur, die alle Achsen gated.

---

## Decision: Scenario-Pack-First

**Selected axis:** `scenario-pack-first` (framed as `economics-gated scenario-pack-first`)

**Begründung:**

1. **Repo-backed Spec-Foundation:** Die Contracts `#3037/#3038/#3039` sind geschlossen. Das Scenario Pack Library Schema, der Batch Runner Manifest, und das Execution Economics Model liegen als versionierte Schemas und Dokumentation auf `main` vor. `core/replay/scenario_packs.py` implementiert deterministische Szenarien (`baseline`, `pessimistic_execution`, `delayed_execution`, `low_liquidity`, `feed_gap`). Keine der anderen Achsen hat eine vergleichbare repo-backed Basis.

2. **Vermeidet Candidate-#4-Falle:** `#3170` hat gezeigt, dass der Fee-Free Proxy negativ bleibt für alle drei Kandidaten. Ein weiterer gleicher Loop-Kandidat wäre wertlos. Die Scenario-Achse ist intrinsisch keine Candidate-Promotion — sie definiert Acceptance-Gates, bevor ein Kandidat implementiert wird.

3. **Hard-Gate Economics:** Die Economics-Achse (`#3170`) ist bereits als Hard Gate verbraucht. Die Scenario-Achse baut darauf auf, indem sie economics-gated Scenario Acceptance definiert: Ein Kandidat beweist erst Scenario-Stress-Resilienz, bevor er in die Pipeline darf.

4. **Keine unevidenced Familien:** Anders als `regime_switch_v1` und `liquidity_filtered_breakout_v1` ist die Scenario-Achse nicht auf Namen angewiesen. Sie referenziert existierende, versionierte Contract- und Code-Artifakte.

5. **Vereinbar mit #1900 North-Star:** Accelerated Replay Paper-Mode profitiert von klareren Scenario-Acceptance-Gates. Stress-Resilienz ist eine Voraussetzung für ehrliche Paper-Evidence.

**Abgrenzung:**
- Diese Entscheidung wählt keine Candidate-Familie aus.
- Diese Entscheidung legt fest, dass der nächste ausführbare Slice eine Spec ist (keine Candidate-Implementierung).
- Der Follow-up Issue definiert, welche Scenarios, Economics-Schwellen und Acceptance-Gates für künftige Candidates gelten.

---

## Recommended Next Executable Slice

**Slice:** Scenario-Pack-First Spec (docs-only)
**Achse:** economics-gated scenario-pack-first
**Ziel:** Definieren der Scenario-Acceptance-Gates, die jeder künftige Candidate bestehen muss, bevor er in Pipeline-, Paper- oder Replay-Evidenz geht.

Erwarteter Umfang:
- Scenario-Inventar (welche Packs aus `core/replay/scenario_packs.py` sind für Prosperity relevant)
- Economics-Schwellen (fee/slippage/spread boundary test als Gate, nicht als Rescue)
- Acceptance-Gates (PASS / WARNING / FAILED / BLOCKED pro Scenario)
- Stop Conditions (kein Same-Loop Candidate #4, keine PB1-Rescue, kein Live-Go)

---

## Follow-up Issue

**Dedupe-Befund:** Keine offenen Issues zu scenario-pack-first / economics-gated discovery gefunden. `#3037/#3038/#3039` sind CLOSED und werden als Foundations referenziert, nicht dupliziert.

**Erstelltes Issue:** `[ARVP][SPEC] Define scenario-pack-first research spec after post-tri-regime full stop`

Refs:
- Parent: #1900
- Refs: #3188, #3186, #2985, #3181, #3183
- Foundations: #3037, #3038, #3039

Scoping:
- **In Scope:** read-only spec, scenario inventory, economics acceptance gates, evidence requirements, stop conditions.
- **Out of Scope:** runtime, implementation, optimization, Docker, DB/MCP, Live-Go, Echtgeld-Go.
- **Acceptance:** clear scenario-pack-first spec, required evidence artifacts, validation gates, stop conditions.

---

## Safety Boundaries

- LR remains NO-GO.
- Board stage trade-capable is not Live-Go.
- No Product-Complete claim.
- No natural_paper_evidence claim.
- No Live-Go / Echtgeld-Go.
- No same-loop Candidate #4 on BTCUSDT/MEXC/1m long-only.
- Scenario-pack-first is a spec/discovery axis, not a strategy implementation.
- No primary_breakout_v1 rescue path is opened.
- No runtime, Docker, workflow, DB, MCP, or secrets work is authorized.

---

## Restunsicherheiten

1. Die Scenario-Achse ist die stärkste repo-backed Option, aber sie ist nicht die einzige legitime. Ein Maintainer mit explizitem multi-symbol Fokus könnte `symbol_axis` höher gewichten. Die vorliegende Entscheidung priorisiert Methoden-Acceptance vor Markt-Expansion, weil das dem aus der `#3170` gelernten "Boundary-first"-Prinzip entspricht.
2. Der Follow-up Issue muss sorgfältig abgrenzen, dass er `#3037/#3038/#3039` referenziert und nicht neu definiert.
3. Falls sich bei der Spec-Erstellung zeigt, dass die Acceptance-Gates ohne echte Pipeline-Candidate-Implementierung nicht bestimmbar sind, muss der Issue auf HOLD gehen statt künstliche Gates zu erfinden.

---

## References

- `docs/evidence/arvp_next_candidate_selection_after_primary_breakout_park_3186.md`
- `docs/evidence/profitability_post_3166_tri_regime_park_next_axis_decision_3168.md`
- `docs/evidence/profitability_break_even_boundary_cost_slippage_sensitivity_3170.md`
- `docs/evidence/arvp_post_run_005_primary_breakout_v1_decision_3181.md`
- `docs/evidence/arvp_exit_regime_decay_diagnosis_3183.md`
- `docs/strategy/CDB_PROFITABILITY_SCENARIO_PACK_LIBRARY_V1.md`
- `docs/strategy/CDB_PROFITABILITY_ARVP_BATCH_RUNNER_V1.md`
- `docs/strategy/CDB_PROFITABILITY_EXECUTION_ECONOMICS_V1.md`
- `docs/roadmaps/ARVP_TO_LIVE_GO_ROADMAP_2026-06.md`
