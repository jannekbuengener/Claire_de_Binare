# CDB — Skill-Auswahlhilfe für Prompts

**Stand:** 2026-08-18  
**Repo-Basis:** `origin/main@534c344f13830c66e37cb78484448ae72a869d69`  
**Zweck:** Interne Auswahlhilfe für ChatGPT. Dieses Dokument hilft dabei, für CDB-Aufträge die richtigen CDB-Skills, Cursor-Subagents sowie passende externe, systeminterne und ChatGPT-only Skills auszuwählen.

> Dieses Dokument ist ein Routing-Helfer.  
> Für CDB-Repo-Skills stehen die verbindlichen Inhalte in `docs/skills/<name>/SKILL.md`.  
> Für externe oder systeminterne Skills führt die jeweilige installierte beziehungsweise offizielle Upstream-`SKILL.md`.

**Live-Crosscheck 2026-08-18:** CDB Canon/Registry, Final-Head-Vertrag und Cursor-Subagent-README wurden gegen die oben genannte Repo-Basis geprüft. Repo-Canon schlägt ältere Aussagen in Backoffice-Listen.

---

## 1. Das Wichtigste in einfachen Worten

CDB hat aktuell **34 kanonische Repo-Skills** und **133 aktive Skill-Adapter**. Zusätzlich dokumentiert diese Fassung **12 externe oder systeminterne Skills** sowie **16 ChatGPT-only Skills**. Weder die 12 externen/systeminternen noch die 16 ChatGPT-only Skills erhöhen die CDB-Canon-Zahl.

Für kanonische CDB-Skills ist die inhaltliche Quelle:

```text
docs/skills/<skill-name>/SKILL.md
```

OpenCode, Cursor, Codex und Claude enthalten Spiegelungen dieser Skills. Bei einem Widerspruch führt immer der Canon unter `docs/skills/`.

### Die vier Grundregeln

1. **Eine Repo-Session beginnt mit `cdb-session-start`.**
2. **Vor Planabschluss, Branch, Worktree oder neuem PR läuft `cdb-pr-router`.**
3. **Eine normale Issue-Session liefert einen Slice in den passenden PR. Sie mergt nicht automatisch.**
4. **Vor einem Merge laufen Completeness Review und Batch Merge Conductor; danach übernehmen die getrennten Final-Head-Rollen PR Reviewer und Merge Agent.**

Der normale Ablauf:

```text
Session starten
→ Live-Kontext einordnen
→ bestehende PRs prüfen und Issue routen
→ engen Slice planen
→ umsetzen und gezielt testen
→ Slice in Batch-PR liefern
→ Session ohne Merge abschließen
```

Der aktuelle Merge-Ablauf:

```text
Merge-Trigger erreicht
→ Wiring prüfen
→ Restlücken klassifizieren
→ fachliche Vollständigkeit prüfen
→ MERGE_CANDIDATE
→ Conductor friert PR ein und integriert aktuelles main
→ Final-Head vollständig validieren
→ App-bound cdb-local-ci auf exakt diesem Head
→ PR Reviewer APPROVE auf exakt diesem Head
→ Merge Agent führt regulären Squash-Merge aus
→ Session Close
```

Wichtig: `cdb_final_head_pr_approval_gate` und `cdb_final_head_merge_executor` sind **Repo-Rollen, keine CDB-Skills**. Sie erhöhen die Zahl der 34 Canon-Skills nicht.

---

## 2. Standard-Skillketten

### Neue Implementierung oder Feature

```text
cdb-session-start
→ cdb-pr-router
→ cdb-issue-to-session-plan
→ passender Fachskill
→ cdb-test-first
→ cdb-session-close
```

Zusätzlich `cdb-control-intake`, wenn Board, LR, Runtime, Governance, Trading oder Safety berührt werden.

### Bug oder unklare Fehlfunktion

```text
cdb-session-start
→ cdb-symptom-triage
→ cdb-root-cause
→ cdb-regression-gap
→ passender Fachskill
→ cdb-test-first
→ cdb-debug-handoff
→ cdb-session-close
```

### Roter CI-Check

```text
cdb-session-start
→ gh-fix-ci
→ cdb-ci-cd-guard
→ cdb-root-cause
→ cdb-regression-gap
→ cdb-session-close
```

### Dokumentation, Runbook oder Status

```text
cdb-session-start
→ cdb-pr-router
→ cdb-docs-ops
→ cdb-drift-reconcile
→ cdb-session-close
```

`CURRENT_STATUS.md` nicht durch einen sofortigen Ein-Zeilen-Nachlauf-PR aktualisieren. Statusänderungen gehören entweder vor dem Freeze in den ursprünglichen PR oder später in den nächsten passenden `docs-governance`-Batch.

### PR soll vollständig geprüft und bis zum Merge geführt werden

```text
cdb-session-start
→ cdb-integration-wiring-audit
→ cdb-pr-gap-classifier
→ cdb-pr-completeness-review
→ MERGE_CANDIDATE
→ cdb-batch-merge-conductor
→ FINAL_HEAD_READY_FOR_APPROVAL
→ cdb_final_head_pr_approval_gate
→ cdb_final_head_merge_executor
→ cdb-session-close
```

Der Conductor **merged nicht**. Er endet erfolgreich bei `FINAL_HEAD_READY_FOR_APPROVAL`.

### Trading-, Risk- oder Execution-Arbeit

```text
cdb-session-start
→ cdb-control-intake
→ cdb-pr-router
→ cdb-trading-core
→ cdb-risk-governance
→ cdb-test-first
→ cdb-shadow-validation
→ cdb-contract-evidence-gatekeeper
→ cdb-session-close
```

Je nach Scope zusätzlich `cdb-exchange-adapters` oder `cdb-backtest-engine`.

### Docker, Compose oder lokaler Stack

```text
cdb-session-start
→ ctb-docker-stack
→ cdb-ci-cd-guard
→ cdb-root-cause
→ cdb-session-close
```

### SurrealDB / Context Intelligence

- Query oder Schema: `surrealql`
- Python-Client: `surrealdb-python`
- Vector/HNSW/Retrieval: `surrealdb-vector`
- Bei CDB-Context-/Brain-Arbeit zusätzlich `cdb-control-intake` und bei passendem Auftrag `cdb-context-intelligence-engineer`.

---

## 3. PR-Acceptance und Final-Head

### `cdb-pr-router`

**Wann:** Vor Planabschluss, Branch, Worktree oder PR-Erstellung.

**Macht:**
- liest offene PRs und Issues,
- prüft Batch-Lane, Objective, Contracts und Locks,
- sucht einen passenden vorhandenen PR,
- empfiehlt neuen Batch- oder Dedicated-PR, wenn kein passender PR existiert.

**Macht nicht:** Branch oder PR erstellen, Locks setzen oder Merge autorisieren.

### `cdb-integration-wiring-audit`

Prüft, ob eine Implementierung wirklich über den echten Systempfad erreichbar ist: Entry Point, Registry/Factory, Config, Producer/Consumer, Persistenz, Runtime-Einbindung, Fehlerpfade, Observability und mögliche Bypässe.

### `cdb-pr-gap-classifier`

Ordnet belegte Restpunkte genau einer Klasse zu:

```text
MUST_FIX_IN_CURRENT_PR
FOLLOWUP_AFTER_MERGE
SEPARATE_DEDICATED_PR
PARKED_NOT_ACTIVE
NOT_A_REAL_GAP
```

### `cdb-pr-completeness-review`

Prüft acht Dimensionen:

1. Funktionalität
2. Wiring / Integration
3. Konfiguration
4. Persistenz / Zustand
5. Runtime / Deployment
6. Tests / Validierung
7. Dokumentation / Runbooks / Contracts
8. Operative Readiness / Observability

Nur `MERGE_CANDIDATE` öffnet den Final-Head-Pfad. `UNKNOWN` blockiert.

### `cdb-batch-merge-conductor`

**Wann:** Nur nach einem schema-validen `MERGE_CANDIDATE`.

**Macht:**
- PR einfrieren,
- aktuelles `main` integrieren,
- Head und Base neu binden,
- kombinierten Diff erneut prüfen,
- vollständige Fast-CI auf dem finalen Head ausführen lassen,
- den App-bound `cdb-local-ci` (`app_id=4410232`) auf exakt diesem Head publizieren oder verifizieren,
- `FINAL_HEAD_READY_FOR_APPROVAL` an `cdb_final_head_pr_approval_gate` übergeben.

**Macht nicht:**
- kein GitHub `APPROVE`,
- kein regulärer Merge,
- keine Issue-Closure,
- keine eigene Routing-, CI- oder Gap-Engine,
- niemals `--admin` als Ersatz für fehlende Gates.

Danach gilt:

```text
cdb_final_head_pr_approval_gate
→ APPROVE auf exaktem Final-Head
→ cdb_final_head_merge_executor
→ regulärer Squash-Merge
→ cdb-session-close
```

---

## 4. Vollständiges CDB-Skill-Inventar — 34 Canon-Skills

### Session, Planung und Operator-Steuerung

| Skill | Verwenden, wenn … |
|---|---|
| `onboarding` | ein Agent neu ist, der Clone frisch ist oder der Einstieg verloren ging. |
| `cdb-onboarding` | Codex ausdrücklich den Alias erwartet. Auf anderen Surfaces normalerweise `onboarding`. |
| `cdb-session-start` | echte Repo-Arbeit beginnt. Standardmäßig immer laden. |
| `cdb-pr-router` | ein Issue geplant, ein Branch/Worktree erzeugt oder ein PR geöffnet werden soll. |
| `cdb-session-close` | ein Slice, PR, Review, Merge oder Debug-Fall sauber beendet wird. |
| `cdb-control-intake` | Board, LR, CURRENT_STATUS, Control Register oder Safety-Grenzen eingeordnet werden müssen. |
| `cdb-issue-to-session-plan` | ein GitHub-Issue in einen ausführbaren Agentenplan übersetzt wird. |
| `cdb-operator` | strenge Bootloader-, Plan-GO-, GitHub- und Safety-Governance nötig ist. |

### PR-Acceptance und Final-Head-Vorbereitung

| Skill | Verwenden, wenn … |
|---|---|
| `cdb-integration-wiring-audit` | geprüft werden muss, ob eine Implementierung wirklich angeschlossen und erreichbar ist. |
| `cdb-pr-gap-classifier` | offene PR-Befunde in aktuelle Pflichtarbeit oder Folgearbeit eingestuft werden müssen. |
| `cdb-pr-completeness-review` | ein PR fachlich vollständig abgenommen werden soll. |
| `cdb-batch-merge-conductor` | ein bestätigter Merge-Kandidat eingefroren, gegen aktuelles `main` integriert und bis `FINAL_HEAD_READY_FOR_APPROVAL` final validiert werden soll. Der Skill merged nicht. |

### Tests, Evidence und Freigabe

| Skill | Verwenden, wenn … |
|---|---|
| `cdb-test-first` | Tests, Regression-Guards und Test-Evidence geplant werden. |
| `cdb-shadow-validation` | zwischen Unit, Replay, MockExchange, Shadow oder STOP entschieden werden muss. |
| `cdb-contract-evidence-gatekeeper` | PASS/BLOCKED, Closure, Contract- oder Evidence-Claims hart geprüft werden. |

### Debug und Fehlerfindung

| Skill | Verwenden, wenn … |
|---|---|
| `cdb-symptom-triage` | ein rohes Fehlersignal zuerst sauber gerahmt und geroutet werden muss. |
| `cdb-root-cause` | Symptom und Ursache getrennt und Hypothesen belegt werden müssen. |
| `cdb-regression-gap` | der fehlende Test, Guard oder Evidence-Nachweis gesucht wird. |
| `cdb-debug-handoff` | ein Debug-Fall sauber in Umsetzung, Folgearbeit oder Session Close übergeben wird. |

### Dokumentation, Canon und Drift

| Skill | Verwenden, wenn … |
|---|---|
| `cdb-docs-ops` | Runbooks, Ledger, Status, operative Doku oder Canon-Ansichten gepflegt werden. |
| `cdb-drift-reconcile` | Doku, Repo, Skills, PRs oder Statusflächen voneinander abweichen könnten. |
| `cdb-external-docs` | offizielle externe Dokumentation für GitHub, Docker, SurrealDB, MEXC oder Tools nötig ist. |

### CI, GitHub und Review

| Skill | Verwenden, wenn … |
|---|---|
| `cdb-ci-cd-guard` | Required Checks, Branch Protection, Final-Head-Evidence oder Fake-Green relevant sind. |
| `gh-fix-ci` | ein konkreter PR-Check rot ist und Ursache/Fixplan gebraucht wird. |
| `gh-address-comments` | Review-Kommentare systematisch abgearbeitet werden sollen. |
| `cdb-github-api-ops` | Issues, PRs, Checks, Status-Snapshots oder GitHub-API-Verträge strukturiert ausgewertet werden. |

### Trading, Strategie, Risk und Exchange

| Skill | Verwenden, wenn … |
|---|---|
| `cdb-trading-core` | Trading-Core, Signalfluss oder cross-cutting Trading-Systemarbeit betroffen ist. |
| `cdb-risk-governance` | Limits, Kill-Switch, Fail-closed, Exposure oder Risk-Service betroffen sind. |
| `cdb-exchange-adapters` | REST/WebSocket, MEXC, Rate Limits, Reconnect oder Exchange-Normalisierung betroffen sind. |
| `cdb-backtest-engine` | Backtests, Walk-Forward, Parameter-Sweeps oder Strategy-Evidence gebaut werden. |

### Runtime und Stack

| Skill | Verwenden, wenn … |
|---|---|
| `ctb-docker-stack` | Docker, Compose, Stack-Topologie, Container oder lokale Services betroffen sind. |

### SurrealDB

| Skill | Verwenden, wenn … |
|---|---|
| `surrealql` | SurrealQL-Queries, Syntax oder Schemaarbeit nötig sind. |
| `surrealdb-vector` | Vector Search, HNSW, Embeddings, KNN oder Retrieval betroffen sind. |
| `surrealdb-python` | SurrealDB Python SDK, Async Client oder Client-Tests betroffen sind. |

---

## 5. Externe und systeminterne Skills — keine CDB-Canon-Skills

Diese Skills sind Werkzeuge für passende Spezialaufträge. Sie zählen nicht zu den 34 CDB-Canon-Skills.

### Cursor Thermos

| Skill | In einfachen Worten |
|---|---|
| `thermo-nuclear-review` | Tiefer Branch-/PR-Review auf Bugs, Security, Funktionsbrüche und Gate-Leaks. |
| `thermo-nuclear-code-quality-review` | Sehr strenger Review auf Wartbarkeit, Struktur, Modularität und unnötige Komplexität. |
| `thermos` | Führt beide Thermo-Reviews parallel aus und führt die Findings zusammen. |

Thermos ergänzt CDB-Review und Completeness, ersetzt aber weder CDB-Evidence noch Required Checks, Final-Head-Gates oder Merge-Rollen.

### Cursor SDK

| Skill | In einfachen Worten |
|---|---|
| `cursor-sdk` | Hilft beim programmatischen Starten und Steuern von Cursor-Agenten über `@cursor/sdk`. |

### Codex-System-Utilities

| Skill | Verwenden, wenn … |
|---|---|
| `imagegen` | ein Rasterbild erzeugt oder bearbeitet werden soll. |
| `openai-docs` | aktuelle offizielle OpenAI-Entwicklerdokumentation gebraucht wird. |
| `plugin-creator` | ein Codex-Plugin aufgebaut oder erweitert werden soll. |
| `skill-creator` | ein Codex-Skill gebaut oder substanziell überarbeitet wird. |
| `skill-installer` | ein Codex-Skill gesucht oder installiert werden soll. |

### Interne Skills des OpenAI Codex Claude Code Plugins

Diese drei sind **nicht user-invocable** und gehören nicht in normale CDB-Slash-Lines:

- `codex-cli-runtime`
- `codex-result-handling`
- `gpt-5-4-prompting`

---

## 6. ChatGPT-only Skills — strikt von CDB-Skills trennen

**Status:** `CHATGPT_ONLY`  
**CDB-Canon:** `false`  
**Repo-Skill:** `false`  
**Repo-Agent:** `false`

### In einfachen Worten

Diese Skills sind Denk-, Recherche- und Prüfhilfen, die **ChatGPT selbst** verwenden kann. Sie helfen, bevor eine Repo-Änderung beginnt: Werkzeug wählen, Reuse prüfen, Annahmen trennen, einen Spike planen, Widersprüche finden oder einen Plan gegenprüfen.

Sie sind **keine Befehle für Cursor, Codex, Claude, OpenCode oder CDB-Repo-Agenten**.

```text
ChatGPT-only Skill
= ChatGPT denkt, recherchiert, prüft oder plant damit.

CDB Repo-Skill
= beschreibt, wie im CDB-Repo gearbeitet wird.

Repo-Agent
= führt eine konkrete Rolle im Repo aus.
```

Routing-Regel:

```text
ChatGPT-only Skill
→ ChatGPT erzeugt belegtes Ergebnis / Plan / Entscheidung
→ passender CDB Repo-Skill übernimmt die Repo-Arbeitsweise
→ passender Repo-Agent führt aus oder prüft
→ GitHub- und Repo-Live-State validieren das Ergebnis
```

### 6.1 Globale ChatGPT-only Skills

| Skill | In einfachen Worten | Wann nehmen? |
|---|---|---|
| `chatgpt-plugin-capability-router` | Klärt, welches Werkzeug für die Aufgabe zuständig ist. | Wenn mehrere Skills, Plugins, Apps oder Agenten infrage kommen. |
| `reuse-first-solution-scout` | Prüft, ob es die Lösung schon gibt, bevor wir selbst bauen. | Vor neuer technischer Fähigkeit oder Integration. |
| `evidence-assumption-checker` | Trennt bewiesen, hergeleitet, angenommen und unbekannt. | Vor tragenden technischen Entscheidungen. |
| `spike-experiment-designer` | Plant einen kleinen messbaren Versuch statt sofort groß zu bauen. | Bei unbewiesener Machbarkeit, Qualität oder Performance. |
| `spec-consistency-auditor` | Prüft, ob Issue, Doku, Code, Tests und Live-State dieselbe Geschichte erzählen. | Bei mehreren Specs/PRs oder zweifelhaftem Done-Status. |
| `final-plan-red-team` | Sucht gezielt Schwächen in einem fertigen Plan. | Vor größerem oder riskanterem Implementierungs-GO. |
| `data-contract-migration-designer` | Plant Änderungen an persistenten Datenformaten mit Kompatibilität und Rückweg. | Bei JSON-, Manifest-, SQLite-, Config- oder API-Vertragsänderungen. |
| `epic-meta-issue-decomposer` | Zerlegt große Vorhaben in saubere Teil-Issues. | Bei Epics und großen Ideen. |

Merkhilfe:

```text
Welches Werkzeug? → chatgpt-plugin-capability-router
Gibt es das schon? → reuse-first-solution-scout
Was ist bewiesen? → evidence-assumption-checker
Erst klein testen? → spike-experiment-designer
Widersprüche? → spec-consistency-auditor
Plan belastbar? → final-plan-red-team
Datenvertrag? → data-contract-migration-designer
Epic zu groß? → epic-meta-issue-decomposer
```

### 6.2 Sample-Brain-Fachskills auf der ChatGPT-Seite

Diese acht Skills sind fachlich auf Sample Brain, Musikproduktion, FL Studio, Audio und Suche zugeschnitten. Sie stehen hier nur, damit ChatGPT seine Fähigkeiten vollständig kennt. Sie werden **nicht automatisch bei CDB-Arbeit benutzt**.

| Skill | In einfachen Worten |
|---|---|
| `sample-brain-feature-intelligence` | Prüft Produktnutzen, Verhalten, Grenzen und kleinsten sinnvollen Feature-Slice. |
| `sample-brain-producer-flow` | Prüft Suchen, Vorhören, Auswahl, Workbench und kreativen Producer-Flow. |
| `sample-brain-musical-contracts` | Macht BPM, Beat, Takt, Phrase, Groove, Key und Arrangement eindeutig und testbar. |
| `sample-brain-audio-parameter-contracts` | Macht Frames, Sekunden, Sample Rate, Stretch, Pitch, dB/LUFS, MIDI und Latenz eindeutig. |
| `sample-brain-fl-studio-grounding` | Prüft Aussagen über FL Studio und seine APIs gegen reale Dokumentation. |
| `sample-brain-interaction-state-contracts` | Definiert UI-Zustände, Übergänge, Async-Verhalten, Fehler und Recovery. |
| `sample-brain-native-audio-windows-grounding` | Groundet WASAPI, miniaudio, Callback-Safety, Device Lifecycle, MMCSS und DLL/FFI. |
| `sample-brain-search-ranking-quality-contracts` | Definiert messbare Qualität für Search, Ranking und Empfehlungen. |

### 6.3 Prompt-Regel für ChatGPT-only Skills

Der Skillname gehört normalerweise **nicht** in den späteren Repo-Agenten-Prompt. In den Prompt gehört das Ergebnis.

```text
Falsch:
Repo-Agent, benutze /reuse-first-solution-scout.

Richtig:
ChatGPT führt den Reuse-Check aus.
Danach bekommt der Repo-Agent:
- geprüfte Kandidaten,
- Quellen,
- Entscheidung Reuse vs. Eigenbau,
- offene Unsicherheiten.
```

---

## 7. Cursor-Subagents — 15 Helferrollen, keine Skills

Cursor-Subagents liegen unter `.cursor/agents/`. Der Parent-Agent behält Verantwortung für GO, Scope, Session Start, Router und Locks.

| Subagent | Typ | Sinnvoll für |
|---|---|---|
| `cdb-audit-priority-gatekeeper` | read-only | Audit-Priorität und Eskalation einordnen. |
| `cdb-pr-steward` | read-only | PR-Inventar, Routing-Evidence, Ledger, Locks und Merge-Trigger. |
| `cdb-repository-auditor` | read-only | Repo-Struktur, Hygiene, Drift und Arbeitsbaum-Befund. |
| `cdb-system-architect` | read-only | Service-Grenzen, Dataflow und Architekturverträge. |
| `cdb-code-reviewer` | read-only | Bugs, Contract-Drift, Testlücken und Diff-Review. |
| `cdb-governance-gatekeeper` | read-only | LR-, Board-, Ledger- und Policy-Grenzen. |
| `cdb-validation-evidence-analyst` | read-only | Replay-, Shadow-, Paper- und Determinismus-Evidence. |
| `cdb-security-triage` | read-only | CVEs, Secrets, Supply Chain und Security Alerts. |
| `cdb-stack-ops-auditor` | read-only | Docker-/Stack-/Ops-Audit. |
| `cdb-control-orchestrator` | read-only | Control Board, Status und operative Orchestrierung. |
| `cdb-market-research-analyst` | read-only | Markt- und Strategie-Recherche. |
| `cdb-ci-debugger` | write-fähig nach GO | CI-Root-Cause und eng freigegebene CI-Reparaturen. |
| `cdb-context-intelligence-engineer` | write-fähig nach GO | Context Brain, SurrealDB und Context-Tools. |
| `cdb-docs-canon-maintainer` | write-fähig nach GO | Canon, Registry und Dokumentationspflege. |
| `cdb-implementation-engineer` | write-fähig nach GO | Umsetzung im freigegebenen Issue-Scope. |

`readonly: false` bedeutet nur technische Schreibfähigkeit. Ohne GO, Session Start und erforderlichen Lock bleibt auch ein write-fähiger Subagent fail-closed.

---

## 8. Regeln für Agenten-Prompts

### Skills gezielt auswählen

Nicht alle Skills in jeden Prompt schreiben. Ein guter Prompt enthält:

1. Pflichtskills für Session und Routing,
2. den passenden Fachskill,
3. nötige Test-/Evidence-Skills,
4. Acceptance-/Conductor-Skills nur bei echtem Final-Head-Auftrag.

### Skills und Subagents getrennt aufführen

```text
Session-Skills:
- /cdb-session-start
- /cdb-pr-router
- /cdb-issue-to-session-plan
- /cdb-test-first
- /cdb-session-close

Sub-Agents:
- /cdb-pr-steward
- /cdb-implementation-engineer
- /cdb-code-reviewer
```

### Delivery Mode ist der Default

Normale Umsetzung endet typischerweise mit:

```text
DONE_SLICE_ADDED_TO_BATCH_PR
```

Das heißt: Slice committed/gepusht, gezielte Tests grün, PR-Ledger aktualisiert, Issue bleibt offen, kein vollständiger Final-Head-Lauf und kein Merge.

### Merge Mode nur ausdrücklich

```text
Completeness Review
→ MERGE_CANDIDATE
→ Conductor
→ Full Fast-CI
→ App-bound cdb-local-ci auf exaktem Final-Head
→ FINAL_HEAD_READY_FOR_APPROVAL
→ PR Reviewer APPROVE auf exaktem Final-Head
→ Merge Agent re-verifiziert und führt regulären Squash-Merge aus
→ Session Close
```

### Kein Status-Tail-PR

Nach einem Merge nicht automatisch einen eigenen PR nur für `CURRENT_STATUS.md` erzeugen. Erlaubt sind:

1. Status-/Ledger-Update vor dem Freeze im ursprünglichen PR.
2. Späteres Routing in den nächsten kompatiblen `docs-governance`-Batch.

---

## 9. Nicht als aktive CDB-Skills behandeln

- Die 16 Skills aus Abschnitt 6 — **ChatGPT-only**; nicht als CDB-Repo-Skills, Slash-Skills oder Repo-Agenten behandeln.
- `.cursor/agents/*` — Subagents, keine Skills.
- `.cursor/rules/*` — Cursor-Regeln, keine Skills.
- `.codex/cdb_skills/.system/*` — Codex-System-Utilities; keine CDB-Canon-Skills.
- `codex-cli-runtime`, `codex-result-handling`, `gpt-5-4-prompting` — interne, nicht user-invocable Plugin-Skills.
- `thermo-nuclear-review`, `thermo-nuclear-code-quality-review`, `thermos`, `cursor-sdk` — externe Cursor-Plugin-Skills; nutzbar, aber nicht repo-kanonisch.
- `.claude/skills/*.skill` — Paket-/Aliasfläche, nicht Canon-Quelle.
- `.gemini/skills/` — eingeschränkte Surface, kein normaler Domain-Mirror.
- `skillforge` — Meta-Tool für Skillbau, kein aktiver CDB-Domain-Skill.
- `mockexchange` — kein aktiver Skill.
- Redis Plugin Skills — externes Routing, nicht repo-mirrored.

---

## 10. Aktueller technischer Stand

Verbindliche Inventarbasis:

```text
34/34 Canon-Skills
133/133 aktive Adapter
3 dokumentierte cdb-onboarding-Ausnahmen
SSOT: docs/skills/
```

Aktive Standard-Mirrors:

```text
.opencode/skills/
.cursor/skills/
.codex/cdb_skills/
.claude/skills/
```

Eingeschränkte Gemini-Surface:

```text
cdb-external-docs
surrealdb-python
surrealdb-vector
surrealql
```

Zusätzliche ChatGPT-Surface:

```text
16 ChatGPT-only Skills
Surface: ChatGPT
CDB-Canon: nein
Repo-Mirror: nicht voraussetzen
Stand: 2026-08-18
```

Bei widersprüchlichen Zählungen ist `docs/skills/SKILL_SURFACE_REGISTRY.md` führend.

---

## 11. Dauerhafte CDB-Grenzen

- `trade-capable` ist eine Board-Stage, kein Live-Go.
- LR bleibt `NO-GO`, solange der LR-Canon nichts anderes belegt.
- `CURRENT_STATUS.md` ist ein Engineering-Ledger, nicht automatisch GitHub-Live-Wahrheit.
- GitHub-Live-State und Repo-Canon schlagen Erinnerungen und alte Berichte.
- GitHub-Writes erfolgen in Agenten-Sessions über `gh` CLI.
- `cdb-local-ci` ist im aktuellen Final-Head-Vertrag ein **App-bound Check Run** (`app_id=4410232`) und muss auf dem exakten finalen PR-Head `SUCCESS` sein.
- Ein namensgleicher Commit Status oder ein Check Run der falschen App ersetzt diesen Required Check nicht.
- `--admin` ersetzt niemals fehlende Evidence oder einen fehlenden Required Check.
- Head- oder Base-Drift macht Final-Evidence ungültig.
- Pausierte oder geparkte Arbeit wird vom Router nicht still reaktiviert.

---

## 12. Pflege dieses Dokuments

Dieses Dokument aktualisieren, wenn mindestens eines davon passiert:

- ein Skill wird neu eingeführt, umbenannt oder entfernt,
- ein Skill wechselt seinen Scope,
- ein neuer Pflichtschritt im Session- oder Merge-Ablauf entsteht,
- ein Cursor-Subagent hinzukommt oder seine Schreibfähigkeit wechselt,
- die Registry-Inventarzahlen sich ändern,
- eine neue Skill-Surface aktiviert wird,
- ein externes Plugin installiert, entfernt oder in seinem Trigger/Scope verändert wird.

Beim nächsten Update zuerst prüfen:

```text
docs/skills/README.md
docs/skills/SKILL_SURFACE_REGISTRY.md
agents/AGENTS.md
.cursor/agents/README_CDB_CURSOR_SUBAGENTS.md
docs/contracts/final_head_merge_pipeline.v1.md
docs/runbooks/PR_ROUTING_AND_BATCH_MERGE_POLICY.md
docs/runbooks/merge_policy_ci_gate.md
```

---

## Kurzfassung

Normale Umsetzung:

```text
Start → Router → Plan → Fachskill → Test First → Slice-Handoff → Close
```

Debug:

```text
Triage → Root Cause → Regression Gap → Fix/Test → Debug Handoff → Close
```

Final-Head/Merge:

```text
Wiring Audit → Gap Classifier → Completeness Review → Conductor → PR Reviewer → Merge Agent → Close
```

Deep Review:

```text
Security/Korrektheit → thermo-nuclear-review
Codequalität/Struktur → thermo-nuclear-code-quality-review
Beides → thermos
```

Und immer:

```text
Bestehenden PR suchen, bevor ein neuer PR entsteht.
ChatGPT-only Skills nicht als CDB-Slash-Skills behandeln.
Nicht nach jeder Session mergen.
Vollständige Final-Head-CI nur am eingefrorenen, exakten Head.
Der Conductor bereitet vor; nur der Merge Agent merged.
```