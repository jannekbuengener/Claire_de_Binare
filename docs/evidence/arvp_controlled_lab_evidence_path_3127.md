# ARVP Controlled-Lab Regime-Segment Evidence Path — #3127

**Decision Date:** 2026-06-12
**Status:** `DONE_DESIGN_COMPLETED`
**Scope:** Design / Evidence Boundary / Policy — keine Code-, Runner-, Artifact- oder Runtime-Änderung
**Parent:** #3087b (Split from #3087 Option-E Decision C via PR #3126, merged `bbc57662`)

---

## Brain Evidence

| Field | Value |
|-------|-------|
| `brain_source` | `repo-only` |
| `brain_status` | `not-used` |
| `tools_or_queries` | `gh issue view` (#3127, #3087, #3094, #3095, #3096, #3103, #2974, #1900), `gh pr list --state open`, `git fetch/prune/status/rev-parse`, file reads across 25+ evidence/runbook/runner/roadmap/governance files |
| `records_or_results` | 8 live GitHub issue queries (all live state captured below), 0 open PRs. Repo reads: canonical governance (10 files), evidence docs (6), runbooks (2), roadmap (1), source files (4), runner module headers (3) |
| `repo_crosscheck` | #3127 body confirmed in GitHub live. Option-E split decision doc defines #3087b scope. Evidence classes from `arvp_deterministic_window_production_3094.md` confirmed. #3096 OPEN confirmed. Campaign manifest contract requires `evidence_class` field. |
| `impact_on_plan` | Design document operationalizes existing #3094 evidence classes for `controlled_lab_evidence`. Does not re-litigate class definitions. Does not implement enforcement (#3096 dependency). |
| `limitations` | No SurrealDB/Context Brain/DB-backed memory. No runtime has been started to verify any candidate source produces non-empty `regime_segments`. |

---

## Bootloader-/Read-Order-Evidence

- `AGENTS.md` root pointer resolved
- `agents/AGENTS.md` canonical registry read (read order, brain evidence gate, status surfaces)
- Read order: `CDB_CONSTITUTION.md`, `CDB_GOVERNANCE.md`, `CDB_AGENT_POLICY.md`, `SYSTEM_INVARIANTS.md`, `CDB_KNOWLEDGE_HUB.md`, `WORKING_REPO_CANON.md`, `CURRENT_STATUS.md`, `LR-AUDIT-STATUS-2026-03-05.md`, `CONTROL_REGISTER.md`, `OPEN_CODE_AGENTS.md`
- Git truth: HEAD `bbc57662` = `origin/main`. Clean worktree at session start.

---

## Live-Lage (GitHub Live Truth as of 2026-06-12)

| Issue | State | Key Fact |
|-------|-------|----------|
| #3127 | **OPEN** | Target issue — fresh, no comments. Body matches scope. |
| #3087 | **OPEN** | Parent — §5.2.4 remains BLOCKED. Split decision made (PR #3126). |
| #3094 | **CLOSED** | Design: Options B+C+E hybrid. Evidence classes formalized. |
| #3095 | **OPEN** | Campaign execution — 3/3 slots consumed, `HOLD_DECISION_REQUIRED`. |
| #3096 | **OPEN** | Evidence class policy enforcement — NOT yet implemented. |
| #3103 | **CLOSED** | Start policy clarified — HIGH_VOL_CHAOTIC restricted. |
| #2974 | **CLOSED** | Product-complete review — BLOCKED by §5.2.4. |
| #1900 | **OPEN** | ARVP north-star anchor. |
| Open PRs | **0** | No open pull requests. |
| LR | **NO-GO** | `LR-AUDIT-STATUS-2026-03-05.md`, `CONTROL_REGISTER.md` |

---

## Befund

1. **Evidence classes exist (#3094).** Vier Klassen sind definiert: `natural_paper_evidence`, `controlled_lab_evidence`, `pipeline_test_evidence`, `waiver_decision`. Kein Artefakt im Repo trägt einen `evidence_class`-Label.

2. **Kein Runner produziert controlled_lab_evidence.** `paper_runtime_stimulus_runner.py` ist `pipeline_test_evidence`. Regime Scorecard Runner hat kein `evidence_class`-Feld. Campaign-Manifest verlangt es, aber keine Implementierung existiert.

3. **Kandidaten-Quellen existieren ohne Label.** Backtest-Artefakte, Replay-Traces und historische Fixtures können `regime_segments` produzieren — aber keines ist dokumentiert oder klassifiziert.

4. **#3096 (Policy Enforcement) ist OPEN.** Ohne #3096 sind implementierte Labels nicht CI-erzwungen — ein späterer Agent könnte `controlled_lab_evidence` stillschweigend als `natural_paper_evidence` interpretieren.

5. **controlled_lab_evidence kann §5.2.4 nicht schließen.** Dies ist der Kern der Evidence-Boundary.

6. **Replay-Infrastruktur kann regime_segments aus historischen Daten produzieren.** Das Regime-Scorecard-Modul akzeptiert Replay-Traces — ob vorhandene Traces non-empty Segmente enthalten, ist nicht geprüft.

---

## Evidence Boundary Matrix

| Evidence Class | §5.2.4 relevant? | Source | Label | Warning Banner |
|---|---|---|---|---|
| `natural_paper_evidence` | **Ja — kann Gate schließen** | Natürliche SIGNAL→DECISION→ORDER(paper)→FILL-Kette aus Paper-Runtime | — | — |
| `controlled_lab_evidence` | **Nein** | Kontrollierte/quasi-historische/simulierte Regime-Segment-Evidenz via Replay → Regime Scorecard | `evidence_class: controlled_lab_evidence` | `⚠ NOT natural_paper_evidence — cannot satisfy §5.2.4` |
| `pipeline_test_evidence` | **Nein** | Stimulus/Test-Only Runner Output | `evidence_class: pipeline_test_evidence` | `⚠ Pipeline test only — NOT valid for Product-Complete gate` |
| `waiver_decision` | **Nur mit formalem Governance-Votum** | Roadmap Amendment / explizite Governance-Entscheidung | `evidence_class: waiver_decision` | `⚠ Policy decision — not evidence. Requires formal governance vote.` |

---

## Allowed Capabilities

1. **Reproduzierbare regime_segments aus nicht-natürlichen Quellen.** Historische Daten → Replay → Regime Scorecard.
2. **Kandidaten-Quellen identifizieren.** Backtest-Artefakte, historische Replay-Traces, Fixture-Packs.
3. **Evidence-Class-Labeling.** Alle kontrollierten Artefakte tragen `evidence_class: controlled_lab_evidence`.
4. **Warning Banner.** Alle Outputs enthalten: `⚠ NOT natural_paper_evidence — cannot satisfy §5.2.4`.
5. **Acceptance Criteria für kontrollierte Evidence-Packets.** Schema, Pflichtfelder, Evidence-Trail.
6. **Execution-Boundary-Dokumentation.**

**Präzisierung Runtime-Boundary:**
- **Offline controlled-lab runs** (Backtest-Trace → Replay → Scorecard) brauchen keine Runtime-Mutation, keinen Stack-Start, kein Docker. Sie arbeiten auf repo-backed Artefakten.
- **Falls ein controlled-lab run die Paper-Runtime nutzen würde** (z.B. um neue Replay-Traces mit Regime-Kontext zu produzieren), dann müssen MOCK_TRADING=true, DRY_RUN=true, MEXC_TESTNET=true belegt sein. Dieses Szenario ist für #3127 nicht vorgesehen — der erste Implementierungs-Schritt arbeitet offline auf bestehenden Artefakten.

---

## Forbidden Interpretations

1. **Nicht §5.2.4 Substitute.** controlled_lab_evidence kann den Product-Complete Gate nicht öffnen.
2. **Kein Silent Upgrade.** controlled_lab_evidence wird NIEMALS natural_paper_evidence.
3. **Kein Live-Go / Echtgeld-Go.** LR bleibt NO-GO.
4. **Kein Product-Complete Claim.** #3087a bleibt OPEN/BLOCKED.
5. **Kein Threshold-Lowering.** 0.5% Breakout-Schwelle unverändert.
6. **Kein Campaign-Ersatz.** controlled-lab ersetzt keine natürlichen Campaigns.
7. **Kein #3087 Closure.** #3127 schließt #3087 nicht.
8. **Keine Stack-/DB-/Runtime-Mutation.** Read-only oder Fixture-getrieben.
9. **Keine Evidence-Class-Enforcement-Umgehung.** #3096 muss implementiert werden, bevor Produktiv-Artefakte erzeugt werden.

---

## Candidate Evidence Sources

| # | Source | Typ | regime_segments via | Vorteil | Limitation |
|---|--------|-----|---------------------|---------|------------|
| 1 | **Backtest-Artefakt** `artifacts/backtests/primary_breakout_v1/20260418-212643/` | Historischer Replay von echten Marktdaten | Replay → Regime Scorecard Runner | Echte 1m-Candles mit Breakout-Events | Nicht Paper-Evidenz; Replay-Only FILLs |
| 2 | **Historisches Fixture** `tests/fixtures/arvp/paper_runtime_stimulus_btcusdt_breakout_v1.json` | Synthetischer Breakout-Datensatz | Fixture → Replay → Regime Scorecard Runner | Deterministic, repo-versioniert | Aktuell Stimulus-Only; braucht Replay-Pass für Scorecard |
| 3 | **Existierende Replay-Traces** `artifacts/regime_scorecards/2975/` | Bereits berechnete Scorecards | Neu-Evaluierung mit Regime-Modul | Zwei Scorecards existieren | Beide haben `segments: []` — keine Garantie für non-empty |
| 4 | **Re-Run Replay gegen historische Candle-Daten** (offline, kein Stack) | Offline Replay via `strategy_replay_runner.py` | Candle-Dataset + Config-Hash → Replay → Scorecard | Candle-Daten existieren in Backtest-Artefakten | Braucht korrekte Config-Hash-Matching |
| 5 | **Simulierter kontinuierlicher Marktdatensatz** (neues Fixture, Design-only) | Synthetisches Multi-Stunden-Fixture mit Regime-Übergängen | Neues Fixture → Replay → Scorecard | Kann gezielt Regime-Segmente erzeugen | Braucht Fixture-Erstellung (außerhalb #3127 Scope) |

**Primary Recommendation für erste Implementierung:** Quelle #1 (Backtest-Artefakt). Der existierende Backtest-Lauf enthält echte Marktdaten mit nachweisbaren Breakouts und minimalem Zusatzaufwand.

---

## Acceptance Criteria for #3127

1. **Mindestens eine reproduzierbare controlled-lab-Quelle identifiziert.** Source-Path, Schema, Reproducibility-Contract dokumentiert.
2. **Evidence-Class `controlled_lab_evidence` dokumentiert.** Nach #3094 Klassifikation: Schema, Pflichtfelder, Banner-Text.
3. **Explizite Aussage: NOT natural_paper_evidence.** In allen Artefakt-Templates enthalten.
4. **Explizite Aussage: NOT Product-Complete Gate Substitute.** Warning Banner für §5.2.4.
5. **Alle späteren Artefakte müssen `evidence_class` + Warning Banner tragen.** Manifest-Ebene.
6. **Kein Threshold-Lowering vorgeschlagen.** 0.5% Breakout bleibt.
7. **Keine Runtime/Stack/DB Mutation erforderlich.** Alle Kandidaten-Quellen sind offline/repo-backed.
8. **LR bleibt NO-GO.** Bestätigt.
9. **#3096-Dependency dokumentiert.** Implementierung von controlled-lab-Artefakten darf nicht vor #3096-Merge erfolgen (oder muss #3096-Scope absorbieren).

---

## Required Later Artifacts

Nach Jannek-GO für den Implementierungs-Slice:

1. **`docs/evidence/arvp_controlled_lab_evidence_path_3127.md`** — Dieses Design-Dokument (wird mit diesem PR committed).

2. **Evidence-Pack (nach #3096 oder gemeinsam mit #3096):**
   - Ein Kandidaten-Quelle (empfohlen: Backtest-Artefakt) durchlaufen
   - `arvp_regime_scorecard_runner.py` mit Backtest-Trace ausführen
   - Ergebnis committed als `artifacts/controlled_lab_evidence/run_001/` mit `evidence_class: controlled_lab_evidence` + Warning Banner
   - Wenn `segments: []`: als Negativ-Evidenz dokumentieren und nächste Quelle versuchen

3. **Runner-Label-Integration (nach #3096 oder gemeinsam mit #3096):**
   - `arvp_regime_scorecard_runner.py`: `--evidence-class` Parameter
   - `paper_reference_window_runner.py`: Evidence-Class-Metadaten
   - Campaign-Manifest: `evidence_class` Pflichtfeld
   - CI-Gate: Artefakte ohne `evidence_class` → BLOCK

4. **Contract-Dokument:**
   - `docs/contracts/evidence_class_contract.md` (oder Extension bestehender Contracts)
   - Alle 4 Evidence-Class-Werte
   - Pflicht-Metadaten-Felder pro Klasse
   - Banner-Text pro Klasse
   - Regel: kein Silent Upgrade, kein Class-Omission

---

## Dependency on #3096

| Aspekt | Verhältnis |
|--------|------------|
| **Design (#3127)** | Kann unabhängig schließen — definiert WAS controlled-lab IST und welche Artefakte gebraucht werden |
| **Evidence-Pack (nach #3127)** | **Empfohlen: warten bis #3096 gemerged.** Ohne Enforcement sind Labels nicht CI-erzwungen |
| **Runner-Labels** | **Gehört in #3096 Scope.** Evidence-Class-Feld in Rennern ist Policy-Enforcement, nicht Design |
| **Minimaler Pfad** | #3127 schließt auf Design. Evidence-Pack und Runner-Labels folgen als eigenständiger PR |
| **Risiko falls #3096 offen bleibt** | Artefakte ohne Enforcement: ein späterer Agent könnte `controlled_lab_evidence` als `natural_paper_evidence` interpretieren |

**Daher:** Dieses Design-Dokument ist vollständig ohne #3096. Der implementierende PR (Evidence-Pack + Runner-Labels) sollte #3096-Scope einschließen oder auf #3096-Merge warten.

---

## Stop Conditions

- [ ] Plan-Versuch #3087 durch controlled-lab-Evidence zu schließen.
- [ ] Plan-Versuch synthetic/simulated/stimulus Output zu `natural_paper_evidence` hochzustufen.
- [ ] Plan-Versuch `primary_breakout_v1` Threshold zu senken (0.5% Breakout).
- [ ] Plan-Versuch Product-Complete ohne §5.2.4 Caveat zu erklären.
- [ ] Plan-Versuch BLUE/RED Runtime-Änderungen, Stack-Start oder Docker-Mutation.
- [ ] Plan-Versuch DB-Writes oder Live-Redis-Publication.
- [ ] LR/Live/Echtgeld-Implikation.
- [ ] Plan-Versuch #3096-Enforcement-Lücke mit Annahme zu umgehen.

---

## Recommended Slice Order

### Slice 1 — Design-Dokument (DIESES, #3127)
- Scope: Design/Evidence-Boundary only
- Output: `docs/evidence/arvp_controlled_lab_evidence_path_3127.md`
- Status: `DONE_DESIGN_COMPLETED`
- Merged via PR

### Slice 2 — #3096 Enforcement + Runner Labels
- Scope: `--evidence-class` in Runnern, CI-Gate, Contract-Doc
- **Muss #3127 enthalten oder referenzieren**
- Output: Contract, Runner-Änderungen, CI-Workflow
- **Dieser Slice ist #3096 oder Teil von #3096**

### Slice 3 — Evidence Pack
- Scope: Ein Kandidaten-Quelle offline evaluieren
- Output: `artifacts/controlled_lab_evidence/run_001/` mit JSON + MD
- **Erst nach Slice 2 (oder mit #3096 gemeinsam)**

---

## Restunsicherheiten

1. **Unbewiesen: dass vorhandene Backtest-Traces non-empty `regime_segments` produzieren.** Zwei existierende Scorecards haben `segments: []`. Längere Backtest-Traces könnten ebenso leere Segmente haben.

2. **Unklar: ob der Offline-Replay-Pfad (`strategy_replay_runner.py`) gegen historische Candle-Daten sauber funktioniert.** Der Pfad ist definiert, aber in dieser Session nicht getestet.

3. **Unklar: wann #3096 geschlossen wird.** Falls #3096 lange offen bleibt, entsteht eine Lücke zwischen Design und Enforcement. Dann müsste der Evidence-Pack entweder warten oder #3096-Scope absorbieren.

4. **Unklar: ob Warning Banner als ausreichendes Governance-Signal akzeptiert werden.** Menschen lesen Banner möglicherweise nicht. Machine-readable Enforcement (#3096) ist der eigentliche Schutz.

5. **Nicht belegt: die tatsächliche Reproduzierbarkeit von Backtest-Trace → Segments.** Der Hash-basierte Determinismus ist im Code verankert, aber für den kontrollierten Pfad nicht erprobt.

6. **Offene Frage: Ob `controlled_lab_evidence` jemals zu `natural_paper_evidence` "reifen" kann.** Design sagt NEIN — die Klassen sind orthogonal. Ein Artefakt kann nicht durch zusätzliche Evidenz die Klasse wechseln. Falls gewünscht, müsste ein neues `natural_paper_evidence`-Artefakt separat erzeugt werden.

---

## Status

**DONE_DESIGN_COMPLETED**

- Design-Dokument definiert controlled-lab evidence path für #3127.
- Evidence Boundary Matrix dokumentiert vier Klassen mit klarer Abgrenzung.
- Kandidaten-Quellen identifiziert (Primary: Backtest-Artefakt).
- #3096 Dependency explizit dokumentiert.
- Acceptance Criteria für Design (#3127) erfüllt.
- LR bleibt NO-GO.
- #3087/§5.2.4 bleibt BLOCKED (wird durch dieses Doc nicht geschlossen).
- Kein Product-Complete Claim.
- Keine Runtime/Code/DB-Änderung.

---

## Referenzen

- #3087 — Comparison-grade paper reference window (OPEN, BLOCKED)
- #3094 — Deterministic window production design (CLOSED)
- #3095 — Volatility-window campaigns (OPEN, 3/3 consumed)
- #3096 — Evidence class policy enforcement (OPEN)
- #3103 — blocked_regimes policy clarification (CLOSED)
- #2974 — Product-complete review (CLOSED, §5.2.4 BLOCKED)
- #1900 — ARVP north-star anchor (OPEN)
- PR #3126 — Option-E split decision (MERGED, `bbc57662`)
- `docs/evidence/arvp_option_e_waiver_split_decision_3087_3095.md`
- `docs/evidence/arvp_deterministic_window_production_3094.md`
- `docs/evidence/arvp_volatility_window_start_policy_3103.md`
- `docs/runbooks/arvp_campaign_supervisor_manifest_state_machine.md`
- `docs/roadmaps/ARVP_TO_LIVE_GO_ROADMAP_2026-06.md`
- `core/replay/arvp_regime_scorecards.py`
- `services/validation/arvp_regime_scorecard_runner.py`
- `services/validation/paper_runtime_stimulus_runner.py`
- `services/validation/paper_reference_window_runner.py`
- `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
- `docs/runbooks/CONTROL_REGISTER.md`
