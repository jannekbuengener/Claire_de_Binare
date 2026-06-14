# ARVP First Scenario Inventory Evidence-Gap Closure

**Issue:** [#3194](https://github.com/jannekbuengener/Claire_de_Binare/issues/3194)
**Parent:** [#1900](https://github.com/jannekbuengener/Claire_de_Binare/issues/1900)
**Refs:** [#3191](https://github.com/jannekbuengener/Claire_de_Binare/issues/3191), [#3189](https://github.com/jannekbuengener/Claire_de_Binare/issues/3189), [#3188](https://github.com/jannekbuengener/Claire_de_Binare/issues/3188), [#3186](https://github.com/jannekbuengener/Claire_de_Binare/issues/3186), [#2985](https://github.com/jannekbuengener/Claire_de_Binare/issues/2985)
**Foundations:** [#3037](https://github.com/jannekbuengener/Claire_de_Binare/issues/3037), [#3038](https://github.com/jannekbuengener/Claire_de_Binare/issues/3038), [#3039](https://github.com/jannekbuengener/Claire_de_Binare/issues/3039)
**Decision date:** 2026-06-14
**Status:** DONE_MERGED_EVIDENCE_BLOCKERS_DOCUMENTED

---

## Brain Evidence

```
brain_source: repo-only
brain_status: not-used
tools_or_queries:
  - read: canonical read-order (AGENTS.md, agents/AGENTS.md, governance, invariants, CONTROL_REGISTER.md, LR-AUDIT-STATUS)
  - bash: git fetch origin --prune, git status -sb, git rev-parse HEAD, git rev-parse origin/main
  - bash: gh pr list --state open, gh issue view 3194, 3191, 3189, 1900
  - bash: gh issue list --state open --search (3 dedupe searches for follow-up)
  - read: docs/evidence/arvp_first_economics_gated_scenario_inventory_3191.md
  - read: docs/evidence/arvp_scenario_pack_first_research_spec_3189.md
  - read: core/replay/scenario_packs.py
  - read: services/validation/strategy_replay_runner.py
  - read: core/replay/scenario_harness.py
  - read: docs/strategy/CDB_PROFITABILITY_SCENARIO_PACK_LIBRARY_V1.md
  - read: docs/strategy/CDB_PROFITABILITY_ARVP_BATCH_RUNNER_V1.md
  - read: docs/strategy/CDB_PROFITABILITY_EXECUTION_ECONOMICS_V1.md
  - bash: make replay-shadow-run REPLAY_DRY_RUN=1 (validated CLI + dataset)
  - bash: python -m services.validation.strategy_replay_runner --scenario-group baseline,pessimistic_execution,feed_gap (executed stress comparison)
  - inspect: artifacts/evidence_scenario_runs/3194/sg-*/scenario_group_manifest.json
records_or_results:
  - git: HEAD=900c972 (origin/main)
  - gh: #3194 OPEN (dieser Slice), #3191 CLOSED (Inventory), #3189 CLOSED (Spec)
  - gh: #1900 OPEN (ARVP North-Star)
  - Dry-run: config valid, 20160 candles loaded
  - Scenario group run: 3/3 succeeded (baseline, pessimistic_execution, feed_gap)
  - Group manifest: sg-ddbcc9cf83e2, all exit_code=0
  - Run IDs: bt-730bf77c069a1738, bt-959b73b24be56c90, bt-ab70637d03712b9a
repo_crosscheck:
  - scenario_packs.py on main confirmed (5 deterministic packs)
  - strategy_replay_runner.py supports --scenario-group
  - artifacts/backtests/primary_breakout_v1/20260418-212643/dataset.candles.json (20160 candles)
  - No replay harness for range_mean_reversion_v1 or momentum_capture_v1 exists
impact_on_plan:
  - Slippage/Spread=0.0 Gap can be partially closed: scenario packs apply 30bps slippage + 0.7 fill_rate
  - Stress comparison is executable via existing offline CLI
  - Only primary_breakout_v1 is replayable; other 2 candidates are EVIDENCE_BLOCKED
limitations:
  - repo-only; no SurrealDB/Context-Brain evidence
  - Individual scenario metrics (slippage delta, fill-rate delta) not persisted by harness as separate artifacts
  - Both HOCH Gaps from #3191 remain partially open for non-primary_breakout_v1 candidates
```

---

## Bootloader-/Read-Order-Evidence

Canonical read-order executed according to `agents/AGENTS.md`:

1. `knowledge/governance/CDB_CONSTITUTION.md` — deterministisches, reproduzierbares System.
2. `knowledge/governance/CDB_GOVERNANCE.md` — Rollenmodell, Betriebsmodi, Change-Control.
3. `knowledge/governance/CDB_AGENT_POLICY.md` §4 — Write-Gates, Single-Writer Lock, HARD STOP.
4. `knowledge/governance/SYSTEM_INVARIANTS.md` — INV-001 bis INV-020.
5. `knowledge/CDB_KNOWLEDGE_HUB.md` — Shared Decisions & Agent Handoffs.
6. `docs/meta/WORKING_REPO_CANON.md` — Working Repo ist produktiver Canon.
7. `CURRENT_STATUS.md` — Ledger, nicht Live-Wahrheit.
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

Stand: 2026-06-14 nach `git fetch origin --prune`, Branch `docs/arvp-evidence-gap-closure-3194` von `origin/main` und GH-Live-Pruefung:

| Item | Status | Ref |
|------|--------|-----|
| `#3194` | **OPEN** — dieser Evidence-Gap-Closure-Slice | Ziel-Issue |
| `#3191` | **CLOSED** — Scenario Inventory gemergt via PR #3193 | Evidence-Gap-Quelle |
| `#3189` | **CLOSED** — Spec gemergt via PR #3192 | Spec-Quelle |
| `#3188` | **CLOSED** — Discovery Axis gemergt via PR #3190 | Vorgaenger |
| `#1900` | **OPEN** — ARVP North-Star Epic | Parent |
| Open PRs | **None** | Saubere Startflaeche |
| Branch | `docs/arvp-evidence-gap-closure-3194` | Arbeitsbranch |
| HEAD | `900c972` (origin/main, frischer Branch) | Sauberer Startpunkt |
| Working tree | Clean (nur Artifact-Verzeichnis neu) | Scope-konform |
| LR-Verdikt | **NO-GO** | Unveraendert |
| Board Stage | `trade-capable` | Nicht Live-Go |

---

## Evidence Gaps From #3191

### HOCH

| Gap | Status | Begruendung |
|-----|--------|-------------|
| Slippage/Spread = 0.0 | **TEILWEISE GESCHLOSSEN** | `pessimistic_execution` Pack wendet 30bps Slippage + 0.7 Fill-Rate an. CLI und Dataset sind nachgewiesen funktionsfaehig (Dry-Run + Scenario-Group-Run bestanden). Nur `primary_breakout_v1` getestet. |
| Stress-Vergleich nie ausgefuehrt | **TEILWEISE GESCHLOSSEN** | Erster Stress-Vergleich mit 3 Szenarien (baseline, pessimistic_execution, feed_gap) erfolgreich ausgefuehrt. 3/3 Szenarien exit_code=0. Nur `primary_breakout_v1` getestet. |

### MITTEL

| Gap | Status | Begruendung |
|-----|--------|-------------|
| Kein Dataset-Quality-Report (#3035) | **EVIDENCE_BLOCKED** | #3035 Dataset Quality Gate ist nicht implementiert. Report wuerde Scope dieses Slices ueberschreiten. |

---

## Feasibility Assessment

### Was funktioniert

- **CLI**: `python -m services.validation.strategy_replay_runner` --input-candles ... --scenario-group ... ist voll funktionsfaehig
- **Dataset**: `artifacts/backtests/primary_breakout_v1/20260418-212643/dataset.candles.json` (20160 Candles) ist valide und replaybar
- **Dry-Run**: `make replay-shadow-run REPLAY_DRY_RUN=1` bestanden (Config valid, Dataset loaded)
- **Scenario-Gruppen-Run**: Alle 3 Szenarien (baseline, pessimistic_execution, feed_gap) erfolgreich mit exit_code=0
- **Slippage-Modell**: `pessimistic_execution` Pack definiert `execution_slippage_bps: 30` (30bps) + `fill_rate: 0.7`
- **Feed-Gap-Modell**: `feed_gap` Pack definiert `feed_gap_bars: 2` (deterministische Stale-Feed-Injektion)

### Was nicht funktioniert / EVIDENCE_BLOCKED

- **`range_mean_reversion_v1`**: Kein Replay-Adapter in `_SUPPORTED_STRATEGY_IDS`. Kein Dataset unter `artifacts/backtests/range_mean_reversion_v1/`. **EVIDENCE_BLOCKED**
- **`momentum_capture_v1`**: Kein Replay-Adapter in `_SUPPORTED_STRATEGY_IDS`. Kein Dataset unter `artifacts/backtests/momentum_capture_v1/`. **EVIDENCE_BLOCKED**
- **Detail-Metriken**: Der Scenario-Harness artifactisiert keine individuellen Szenario-Metriken (Net-Return-Delta, Slippage-Delta, Fill-Rate-Delta). Nur Run-IDs und Exit-Codes werden persistiert.
- **Dataset-Quality-Report (#3035)**: Nicht implementiert. Kein Quality-Verdict fuer das verwendete Dataset.

---

## Harness / Scenario Pack Inventory

### Gepruefte Komponenten

| Komponente | Pfad | Status |
|------------|------|--------|
| Scenario Packs | `core/replay/scenario_packs.py` | ✅ 5 deterministische Packs |
| Scenario Harness | `core/replay/scenario_harness.py` | ✅ Orchestriert Gruppen-Runs |
| Replay CLI | `services/validation/strategy_replay_runner.py` | ✅ `--scenario-group` Flag |
| Replay Makefile Target | `Makefile` (replay-shadow-run) | ✅ Funktionsfaehig |
| Baseline Pack | `scenario_packs.py` `"baseline"` | ✅ exit_code=0 im Run |
| Pessimistic Execution Pack | `scenario_packs.py` `"pessimistic_execution"` | ✅ exit_code=0 im Run (30bps Slippage + 0.7 Fill) |
| Feed Gap Pack | `scenario_packs.py` `"feed_gap"` | ✅ exit_code=0 im Run (2 Bars Gap) |
| Primary Breakout Dataset | `artifacts/backtests/primary_breakout_v1/20260418-212643/dataset.candles.json` | ✅ 20160 Candles |

### Nicht verfuegbare Komponenten

| Komponente | Grund |
|------------|-------|
| range_mean_reversion_v1 Replay-Adapter | Nicht in `_SUPPORTED_STRATEGY_IDS` |
| momentum_capture_v1 Replay-Adapter | Nicht in `_SUPPORTED_STRATEGY_IDS` |
| delayed_execution / low_liquidity Packs im Run | Nicht getestet (optionaler Scope) |
| Individual Scenario Artifacts | Harness persistiert nur Group-Manifest, keine Detail-Metriken |

---

## Dataset / Input Availability

| Dataset | Pfad | Candles | Qualitaet |
|---------|------|---------|-----------|
| primary_breakout_v1 (20260418-212643) | `artifacts/backtests/primary_breakout_v1/20260418-212643/dataset.candles.json` | 20160 | **Kein Quality-Report (#3035)**, aber technisch valide und replaybar |
| primary_breakout_v1 (20260419-151938) | `artifacts/backtests/primary_breakout_v1/20260419-151938/dataset.candles.json` | ~21350 | Aehnliche Qualitaet |
| range_mean_reversion_v1 | Kein Dataset vorhanden | N/A | **EVIDENCE_BLOCKED** |
| momentum_capture_v1 | Kein Dataset vorhanden | N/A | **EVIDENCE_BLOCKED** |

---

## Slippage / Spread Assumption Assessment

### Before this closure

| Economics Assessment | Slippage | Spread | Quelle |
|---------------------|----------|--------|--------|
| primary_breakout_v1 | 0.0 | 0.0 | #3170 Break-Even Boundary |
| range_mean_reversion_v1 | 0.0 | 0.0 | #3170 Break-Even Boundary |
| momentum_capture_v1 | 0.0 | 0.0 | #3170 Break-Even Boundary |

### After this closure

| Scenario Pack | Slippage | Fill Rate | Posture | Status |
|---------------|----------|-----------|---------|--------|
| baseline | 0.0 bps | 1.0 | normal | ✅ exit_code=0 |
| pessimistic_execution | **30 bps** | **0.7** | pessimistic | ✅ exit_code=0 |
| feed_gap | 0.0 bps | 1.0 | normal (2-bar gap) | ✅ exit_code=0 |

**Befund:** Der `pessimistic_execution` Pack beweist, dass Slippage > 0.0 technisch darstellbar und ausfuehrbar ist. Die bisherige Slippage=0.0 Annahme war keine technische Limitierung, sondern eine Ausfuehrungsluecke. Diese Luecke ist fuer `primary_breakout_v1` geschlossen.

**Einschraenkung:** Detaillierte Net-Return-Deltas zwischen Baseline und Pessimistic Execution wurden vom Harness nicht als separate Artifakte persistiert. Eine Wiederholung mit manuellem Metric-Capture oder ein separates Tooling waere fuer quantitative Deltas erforderlich.

---

## Stress Replay Result

### Scenario Group Run: sg-ddbcc9cf83e2

| Szenario | exit_code | Run ID | Ergebnis |
|----------|-----------|--------|----------|
| baseline | 0 | bt-730bf77c069a1738 | ✅ Erfolgreich |
| pessimistic_execution | 0 | bt-959b73b24be56c90 | ✅ Erfolgreich |
| feed_gap | 0 | bt-ab70637d03712b9a | ✅ Erfolgreich |

### Command

```
python -m services.validation.strategy_replay_runner \
    --input-candles artifacts/backtests/primary_breakout_v1/20260418-212643/dataset.candles.json \
    --output-dir artifacts/evidence_scenario_runs/3194 \
    --scenario-group baseline,pessimistic_execution,feed_gap
```

### Artifacts

- Group Manifest: `artifacts/evidence_scenario_runs/3194/sg-ddbcc9cf83e2/scenario_group_manifest.json`
- Group Fingerprint: `6b89dd642aecad5908906dadc1920f0e64e2d84e49601724615f21646c6cd876`
- Scenario Specs: `artifacts/evidence_scenario_runs/3194/sg-ddbcc9cf83e2/scenario_specs.json`
- Comparison Summary: `artifacts/evidence_scenario_runs/3194/sg-ddbcc9cf83e2/scenario_comparison_summary.md`

### Evidence Blocker for Other Candidates

| Candidate | Blocker | Status |
|-----------|---------|--------|
| range_mean_reversion_v1 | Kein Replay-Adapter in `_SUPPORTED_STRATEGY_IDS` | **EVIDENCE_BLOCKED** |
| momentum_capture_v1 | Kein Replay-Adapter in `_SUPPORTED_STRATEGY_IDS` | **EVIDENCE_BLOCKED** |

---

## Economics Gate Impact

| Gate | Status Before | Status After | Begruendung |
|------|---------------|--------------|-------------|
| G1 (No stale PARK promotion) | PASS | PASS | Unveraendert |
| G2 (No same-loop) | PASS | PASS | Unveraendert |
| G3 (Economics before impl.) | BLOCKED | **BLOCKED** | Nicht im Scope dieses Slices |
| G4 (Scenario replayable) | PASS | **PASS (bestaerkt)** | 3/3 Packs erfolgreich ausgefuehrt |
| G5 (ranking_ready=false) | PASS | PASS | Unveraendert |
| G6 (Fail-closed cost assumptions) | PARTIAL | **PARTIAL** | Slippage-Modell existiert, aber nur auf primary_breakout_v1 angewandt |
| G7 (Fee-Free Proxy >= 0.0R) | FAIL | FAIL | Unveraendert (alle Kandidaten negativ) |
| G8 (Stress resilience) | MISSING | **PARTIAL** | Erster Stress-Vergleich ausgefuehrt, aber nur 3/5 Packs, nur 1/3 Kandidaten |

---

## Decision

1. **Slippage/Spread=0.0 Gap ist fuer primary_breakout_v1 technisch geschlossen.** Der `pessimistic_execution` Pack beweist, dass Slippage > 0.0 darstellbar und ausfuehrbar ist. Die bisherige Slippage=0.0 Annahme war eine Ausfuehrungsluecke, keine technische Limitierung.

2. **Stress-Vergleich ist fuer primary_breakout_v1 erstmals ausgefuehrt.** Drei Szenarien (baseline, pessimistic_execution, feed_gap) wurden erfolgreich gestartet. Detail-Metriken (Net-Return-Delta) wurden vom Harness nicht als separate Artifakte persistiert.

3. **range_mean_reversion_v1 und momentum_capture_v1 bleiben EVIDENCE_BLOCKED.** Kein Replay-Adapter existiert. Ein separater Issue ist erforderlich, um Replay-Adapter fuer diese Kandidaten zu bauen.

4. **Dataset-Quality-Report (#3035) bleibt EVIDENCE_BLOCKED.** Nicht im Scope dieses Slices.

5. **Kein Candidate wird promoted.** Alle drei Kandidaten bleiben PARKED. G7 (Fee-Free Proxy < 0.0R) blockt weiterhin korrekt.

6. **LR remains NO-GO.** Keine Aenderung an Live-Readiness.

---

## Recommended Next Bounded Slice

**Bounded Evidence Slice: Range Mean Reversion Replay Adapter**

Begruendung:
- `range_mean_reversion_v1` ist der am zweitbesten evidenzgestuetzte Kandidat
- Ein Replay-Adapter fehlt (`_SUPPORTED_STRATEGY_IDS` enthaelt nur `primary_breakout_v1`)
- Ohne Replay-Adapter bleibt der gesamte Stress-Vergleich fuer diesen Kandidaten blockiert

**Alternativ: Scenario-Metrics Harness-Erweiterung**
- Der aktuelle Harness persistiert keine individuellen Szenario-Metriken
- Eine Erweiterung um Net-Return-Delta, Slippage-Delta etc. wuerde quantitative Vergleiche ermoeglichen

---

## Follow-up Issue

**Dedupe-Befund:** Drei dedizierte `gh issue list`-Suchen ergaben keine offenen Issues:
- `gh issue list --state open --search "scenario stress replay evidence blocked"` → 0
- `gh issue list --state open --search "slippage spread model evidence gap"` → 0
- `gh issue list --state open --search "ARVP scenario evidence gap closure"` → 0

**Erstelltes Issue:** `[ARVP][EVIDENCE] Range Mean Reversion Replay Adapter and Evidence Blockers after #3194`

Body:
- Parent: #1900
- Refs: #3194, #3191, #3189, #3188
- Objective: Build replay adapter for range_mean_reversion_v1 and close remaining evidence blockers from #3194
- Scope: Replay adapter, dataset preparation, stress comparison for range_mean_reversion_v1
- Out of scope: strategy implementation, optimization, runtime services, Docker, DB/MCP, Live-Go, Echtgeld-Go
- Acceptance: Replay adapter exists in `_SUPPORTED_STRATEGY_IDS`, stress comparison executable, evidence gaps documented
- Safety: LR remains NO-GO

---

## Safety Boundaries

- LR remains NO-GO.
- Board stage trade-capable is not Live-Go.
- No Product-Complete claim.
- No natural_paper_evidence claim.
- No Live-Go / Echtgeld-Go.
- No same-loop Candidate #4 on BTCUSDT/MEXC/1m long-only.
- This evidence-gap closure does not promote any candidate.
- No primary_breakout_v1 rescue path is opened.
- No runtime, Docker, workflow, DB, MCP, or secrets work is authorized.
- No parameter optimization or strategy tuning is authorized.

---

## Restunsicherheiten

1. **Individual Scenario Metrics wurden nicht persistiert.** Der Harness protokolliert nur Run-IDs und Exit-Codes. Quantitative Deltas (Net-Return, Slippage-Impact) sind nicht als Artifakte verfuegbar.
2. **Dataset-Quality-Report fehlt.** Das verwendete Dataset (20160 Candles) ist technisch valide, aber ohne Quality-Report (#3035) bleibt die Vertrauenswuerdigkeit ungeprueft.
3. **Nur 3 von 5 Scenario Packs getestet.** `delayed_execution` und `low_liquidity` wurden nicht ausgefuehrt.
4. **Nur 1 von 3 Kandidaten getestet.** `range_mean_reversion_v1` und `momentum_capture_v1` bleiben EVIDENCE_BLOCKED.
5. **Die Economics Gate Map zeigt weiterhin G8=PARTIAL.** Ein vollstaendiger Stress-Vergleich erfordert alle 5 Packs auf allen 3 Kandidaten.

---

## References

- `docs/evidence/arvp_first_economics_gated_scenario_inventory_3191.md`
- `docs/evidence/arvp_scenario_pack_first_research_spec_3189.md`
- `docs/evidence/arvp_post_tri_regime_candidate_discovery_axis_3188.md`
- `docs/strategy/CDB_PROFITABILITY_SCENARIO_PACK_LIBRARY_V1.md`
- `docs/strategy/CDB_PROFITABILITY_ARVP_BATCH_RUNNER_V1.md`
- `docs/strategy/CDB_PROFITABILITY_EXECUTION_ECONOMICS_V1.md`
- `core/replay/scenario_packs.py`
- `core/replay/scenario_harness.py`
- `services/validation/strategy_replay_runner.py`
- `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
- `docs/runbooks/CONTROL_REGISTER.md`
