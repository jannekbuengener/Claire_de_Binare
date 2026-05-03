# Context Intelligence — Agent OS Readiness Criteria

**Issue**: #2032
**Epic**: #1976
**Wave**: 20 (#2188–#2196)
**Status**: Proposed criteria catalog / pending PR merge
**Guardrail**: Agent OS Ready != Live Readiness; LR bleibt NO-GO.

---

## 1. Issue / Scope

Dieses Dokument definiert den prüfbaren Kriterienkatalog für die Agent OS Readiness
des CDB Context Intelligence Systems (CIS), wie in Issue #2032 gefordert.

Es ist ein **reines Kriteriendokument** — kein Evaluator, kein MCP Tool, kein Runtime-Code.

## 2. Purpose

Ein neuer Agent oder eine neue Agenten-Runtime muss vor der Aktivierung prüfen können,
ob das CIS als Agent Operating System bereit ist. Dieses Dokument liefert die Kriterien,
Stufen, Mindestwerkzeuge, Gates, Failure Modes und Human-GO-Punkte dafür.

## 3. Non-Goals

- Kein Evaluator-Code (#2191 ist separater Scope)
- Kein MCP Tool
- Kein Readiness Report (#2193 ist separater Scope)
- Kein Readiness Check v0 (#2098 ist separater Scope)
- Kein Trust Summary Builder (#2121 ist separater Scope)
- Keine Completion Gates (#2196 ist separater Scope)
- Keine SurrealDB-Aktivierung
- Kein Runtime-/Trading-/Risk-/Execution-/Strategy-Scope
- Kein Live-Readiness-Go
- Kein Echtgeld-Go
- Keine Autonomie ohne Gates

## 4. Readiness Stages

Die sieben Readiness-Stufen aus #2032 bilden eine aufsteigende Kette.
Jede Stufe setzt die vorherige voraus.

| # | Stufe | Kurzdefinition |
|---|-------|---------------|
| 1 | `context_foundation_ready` | Basisfundament: Repo-Hierarchie, Canon-Pfade, Governance-Docs sind ingestiert und querybar. |
| 2 | `ingestion_ready` | Repo-/Doku-/Code-Ingestion läuft stabil und deterministisch; Hashing und Export-Pipeline funktionieren. |
| 3 | `graph_ready` | Knowledge Graph ist aufgebaut; Knoten und Kanten (Implements, Validates, DependsOn) sind modelliert und querybar. |
| 4 | `evidence_ready` | Evidence Fabric verknüpft Claims mit Quellen; Source-Hashes und Provenance-Trails sind vorhanden. |
| 5 | `briefing_ready` | Agent Briefing Engine erzeugt aufgabenspezifische Context Packages mit Source-Refs und Warnings. |
| 6 | `governance_intelligence_ready` | Contradiction Detection, Scope Drift Firewall und Stale Knowledge Runtime sind aktiv; Governance Gates werden respektiert. |
| 7 | `agent_os_ready` | Alle Stufen erfüllt; Agent OS kann Scope verstehen, Context Packages abrufen, Briefings lesen, Abhängigkeiten tracen, Evidence prüfen, Impact erkennen, Scope Drift erkennen, Stop Conditions respektieren, Memory read-only lesen nach Regeln, Entscheidungen replayen, Erklärungen abrufen und Unsicherheiten melden. |

## 5. Stage Criteria Matrix

### 5.1 `context_foundation_ready`

| Kriterium | Beschreibung | Prüfung |
|-----------|-------------|---------|
| CF-01 Repo-Hierarchie ingestiert | `docs/`, `knowledge/`, `agents/`, `core/`, `services/` sind als Struktur erfasst | Pfade querybar |
| CF-02 Canon-Pfade bekannt | `AGENTS.md`, `agents/AGENTS.md`, `CURRENT_STATUS.md`, `CONTROL_REGISTER.md`, `LR-AUDIT-STATUS` sind als SSOT-Einträge registriert | Canon-Liste abfragbar |
| CF-03 Governance-Docs ingestiert | `CDB_CONSTITUTION.md`, `CDB_GOVERNANCE.md`, `CDB_AGENT_POLICY.md`, `SYSTEM_INVARIANTS.md` sind chunked und querybar | Volltext-Suche |
| CF-04 Ontologie geladen | `context-ontology-v0.yaml` ist geparst und Konzepte sind querybar | Konzept-Lookup |
| CF-05 Board-Stage erkannt | `trade-capable` ist als Stage registriert, orthogonale LR-Trennung dokumentiert | Stage-Query |
| CF-06 LR-Status erkannt | `NO-GO` ist als LR-Verdict registriert | LR-Query |

### 5.2 `ingestion_ready`

| Kriterium | Beschreibung | Prüfung |
|-----------|-------------|---------|
| IN-01 Indexer-Scaffold läuft | Context Indexer Scaffold (#2045) ist funktionsfähig | Dry-Run erfolgreich |
| IN-02 Hashing deterministisch | Alle ingestierten Dokumente haben stabile Content-Hashes | Hash-Vergleich über zwei Runs |
| IN-03 Export-Pipeline intakt | Export produziert schema-valides JSON | Schema-Validierung |
| IN-04 Repo-Doku-Ingestion vollständig | Alle `.md`-Dateien in `docs/`, `knowledge/`, `agents/` sind ingestiert | Datei-Count vs. Ingest-Count |
| IN-05 Code-Symbol-Extraktion läuft | Python AST Extraktion für `core/`, `services/` funktioniert | Symbol-Liste nicht leer |
| IN-06 GitHub-Issues/PRs-Metadaten abrufbar | Issue-States, PR-States, Labels via API abfragbar | Issue-Query liefert `state`, `title`, `labels` |

### 5.3 `graph_ready`

| Kriterium | Beschreibung | Prüfung |
|-----------|-------------|---------|
| GR-01 Knoten modelliert | Code-Symbole, Docs, Issues, Entscheidungen als Knoten vorhanden | Node-Count > 0 |
| GR-02 Kanten modelliert | `Implements`, `Validates`, `DependsOn`, `References` als gerichtete Kanten | Edge-Count > 0 |
| GR-03 SurrealDB Schema geladen | `context-ontology-v0.yaml` Konzepte als SurrealQL Tables/Relations | Schema-Introspection |
| GR-04 Graph querybar | Traversierung über `context.trace` möglich | Trace-Endpoint liefert Lineage |
| GR-05 Symbol-to-Doc-Links vorhanden | Code-Symbole verweisen auf Dokumentation | Symbol-Lookup liefert Doc-Refs |
| GR-06 Issue-to-Commit-Links vorhanden | Issues verweisen auf relevante Commits/PRs | Issue-Query liefert Commit-Refs |

### 5.4 `evidence_ready`

| Kriterium | Beschreibung | Prüfung |
|-----------|-------------|---------|
| EV-01 Evidence Fabric querybar | Claims können gegen Evidence geprüft werden | `context.search` mit `source_type: evidence` |
| EV-02 Source-Hashes vorhanden | Jeder Evidence-Eintrag hat Source-Hash | Hash-Feld nicht leer |
| EV-03 Provenance-Trail vorhanden | Evidence-Einträge haben `created_by`, `created_at`, Chain | Chain-Länge ≥ 1 |
| EV-04 Confidence-Scores gesetzt | Evidence-Einträge haben Confidence (0.0–1.0) | Confidence ≠ null |
| EV-05 Warnings vorhanden | Unsichere oder unvollständige Evidence hat Warnings | Warnings-Array nicht leer bei weak evidence |
| EV-06 Evidence Bundle checkbar | `context.explain_source` liefert Supporting Evidence | Explain-Endpoint funktioniert |

### 5.5 `briefing_ready`

| Kriterium | Beschreibung | Prüfung |
|-----------|-------------|---------|
| BR-01 Context Package generierbar | `context.package` erzeugt Package mit Artifacts | Package-Format valide |
| BR-02 Package enthält Source-Refs | Jedes Artifact im Package hat `source_ref` | Source-Refs nicht leer |
| BR-03 Package enthält Warnings | Package enthält Warnings-Array | Warnings-Feld vorhanden |
| BR-04 Package-ID deterministisch | Gleiche Artifacts → gleiche `package_id` | Zwei Runs, gleiche ID |
| BR-05 Briefing aufgabenspezifisch | Package-Inhalt passt zu `task_scope` | Scope-Filter wirkt |
| BR-06 Impact Radar liefert Abhängigkeiten | Dependency Edges für betroffene Artefakte vorhanden | Radar-Query liefert Edges |

### 5.6 `governance_intelligence_ready`

| Kriterium | Beschreibung | Prüfung |
|-----------|-------------|---------|
| GI-01 Contradiction Detection aktiv | Widersprüche zwischen Docs und Code werden erkannt | Contradiction-Log nicht leer im Test |
| GI-02 Scope Drift Firewall aktiv | Scope-Erweiterungen ohne Authorization werden gewarnt | Drift-Warnung bei Scope-Change |
| GI-03 Stale Knowledge erkannt | Veraltete Docs/Decisions werden als stale markiert | Stale-Flag bei alterierten Quellen |
| GI-04 Governance Gates respektiert | Stop Conditions bei Gate-Verstoß werden ausgelöst | Gate-Verstoß → Block |
| GI-05 Human-GO-Punkte erkannt | Write-/Runtime-/DB-/Trading-Scope wird als Human-GO klassifiziert | Human-GO-Flag bei erkanntem Scope |
| GI-06 Decision Graph querybar | Entscheidungen mit Begründung und Evidence abrufbar | Decision-Lookup funktioniert |

### 5.7 `agent_os_ready`

| Kriterium | Beschreibung | Prüfung |
|-----------|-------------|---------|
| AO-01 Alle Stufen 1–6 erfüllt | `context_foundation_ready` bis `governance_intelligence_ready` sind PASS | Stufen-Check komplett grün |
| AO-02 Scope verstehbar | Agent kann aus Context Package Mission-Scope extrahieren | Scope-Feld im Package |
| AO-03 Context Package abrufbar | Agent kann Package via Tool abrufen | Package-Endpoint antwortet |
| AO-04 Briefing lesbar | Agent kann Briefing-Inhalte parsen und verstehen | Briefing-Felder valide |
| AO-05 Abhängigkeiten tracebar | Agent kann `context.trace` für Dependency-Tracing nutzen | Trace-Endpoint funktioniert |
| AO-06 Evidence prüfbar | Agent kann Claims gegen Evidence Fabric validieren | Evidence-Check-Endpoint antwortet |
| AO-07 Impact erkennbar | Agent kann Impact Radar für Änderungsfolgenabschätzung nutzen | Radar-Endpoint funktioniert |
| AO-08 Scope Drift erkennbar | Agent erkennt Abweichungen vom kanonischen Mission-Scope | Drift-Warnung sichtbar |
| AO-09 Stop Conditions respektierbar | Agent stoppt bei Gate-Verstoß oder Blocking-Finding | Stop bei Block |
| AO-10 Memory/Context lesbar nach Regeln | Agent kann erlaubte Memory-/Context-Informationen read-only abrufen; schreibender Memory-Zugriff ist kein v0-Kriterium und bleibt separater Human-GO-Scope | Read-only Memory-/Context-Lookup antwortet; keine Write-Capability erforderlich |
| AO-11 Entscheidungen replaybar | Agent kann Entscheidungen über Decision Graph nachvollziehen | Decision-Trace funktioniert |
| AO-12 Erklärungen abrufbar | Agent kann Selbst-Erklärungen des Systems einsehen | Self-Explanation-Endpoint antwortet |
| AO-13 Unsicherheiten meldbar | Agent kann Warnings und Confidence-Defizite ausgeben | Warnings sichtbar |
| AO-14 Keine Live-/Echtgeld-Ableitung möglich | Agent OS Ready signalisiert nie Live-Readiness-Go | LR-Status unverändert |

## 6. Minimum Tooling by Stage

| Stufe | Minimum Tools |
|-------|--------------|
| `context_foundation_ready` | `context.search` (Keyword, Struktur) |
| `ingestion_ready` | Indexer-Scaffold, Export-Pipeline (CLI) |
| `graph_ready` | `context.trace`, `context.search` (Graph-Traversierung) |
| `evidence_ready` | `context.explain_source`, `context.search` (Evidence-Filter) |
| `briefing_ready` | `context.package`, `context.show_snapshot` |
| `governance_intelligence_ready` | Contradiction Detection (intern), Scope Drift Firewall (intern), `context.show_audit` |
| `agent_os_ready` | Alle v0 Context Tools (#2092) + Self-Explanation Tool (#2190) |

Anmerkung: Die v0 Context Tools sind in `docs/surrealdb/context-tool-contracts-v0.md` (#2092)
definiert. Interne Komponenten (Indexer, Detection, Firewall) sind keine Agent-facing Tools,
aber notwendige Runtime-Komponenten der jeweiligen Stufe.

## 7. Minimum Gates by Stage

| Stufe | Gates |
|-------|-------|
| `context_foundation_ready` | Canon-Pfade vollständig; keine fehlenden SSOT-Referenzen |
| `ingestion_ready` | Deterministische Hashes; Schema-valider Export |
| `graph_ready` | Knoten- und Kanten-Count > 0; Trace-Endpoint liefert Lineage |
| `evidence_ready` | Source-Hashes für alle Evidence-Einträge; minimum confidence threshold >= 0.5 |
| `briefing_ready` | Package mit Source-Refs und Warnings; deterministische Package-ID |
| `governance_intelligence_ready` | Contradiction Detection liefert Findings; Scope Drift Firewall aktiv; Stale-Flags gesetzt |
| `agent_os_ready` | Alle AO-01 bis AO-14 Kriterien PASS |

Jedes Gate muss **explizit** als PASS dokumentiert werden. Ein fehlendes Gate = Stufe nicht erreicht.
Gate-Passage erfolgt nur durch Evaluation, nicht durch Annahme.

## 8. Failure Modes

### FM-01: Missing Context Package
**Symptom**: `context.package` liefert leeres oder unvollständiges Package.
**Stufe betroffen**: `briefing_ready`, `agent_os_ready`
**Konsequenz**: Agent kann Scope nicht verstehen; Block auf `briefing_ready`.

### FM-02: Missing Source Refs
**Symptom**: Evidence-Einträge oder Package-Artifacts ohne `source_ref`.
**Stufe betroffen**: `evidence_ready`, `briefing_ready`, `agent_os_ready`
**Konsequenz**: Keine Nachvollziehbarkeit; Block auf `evidence_ready`.

### FM-03: Weak Evidence
**Symptom**: Confidence-Scores durchgängig niedrig (< 0.5) oder fehlend.
**Stufe betroffen**: `evidence_ready`, `agent_os_ready`
**Konsequenz**: Agent-Entscheidungen basieren auf schwacher Grundlage; `evidence_ready` gilt als nicht erreicht.

### FM-04: Stale Docs
**Symptom**: Dokumentation hat neuere Git-Commits als der ingestierte Snapshot.
**Stufe betroffen**: `governance_intelligence_ready`, `agent_os_ready`
**Konsequenz**: Agent arbeitet mit veralteten Informationen; Stale-Flag muss gesetzt sein.

### FM-05: Unresolved Dependency
**Symptom**: Vorbedingungs-Issue oder -Komponente ist nicht implementiert.
**Stufe betroffen**: alle Stufen
**Konsequenz**: Stufe kann nicht erreicht werden, solange harte Dependencies offen sind.

### FM-06: Scope Drift Risk
**Symptom**: Task-Scope des Agenten weicht vom kanonischen Mission-Scope ab.
**Stufe betroffen**: `governance_intelligence_ready`, `agent_os_ready`
**Konsequenz**: Scope Drift Firewall muss warnen; Agent muss Scope-Verletzung erkennen.

### FM-07: Human-GO Required
**Symptom**: Operation erfordert Write, Runtime-Mutation, DB-Änderung oder Trading-Bezug.
**Stufe betroffen**: `agent_os_ready`
**Konsequenz**: Agent OS muss Human-GO anfordern; keine automatische Ausführung.

### FM-08: Live-Readiness Confusion Risk
**Symptom**: Agent OS Ready wird als Live-Readiness-Go oder Echtgeld-Freigabe interpretiert.
**Stufe betroffen**: `agent_os_ready`
**Konsequenz**: Kategorischer Fehler. Agent OS Ready ist orthogonal zu LR. LR bleibt SSOT in `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`.

## 9. Human-GO Points

Folgende Operationen erfordern ein explizites Human-GO, **unabhängig vom Agent-OS-Readiness-Status**:

| Human-GO Point | Begründung |
|----------------|-----------|
| Write-capable Operation | Jede Änderung an Repo-Dateien, Issues, PRs |
| Runtime/DB Mutation | Jede Änderung an laufenden Services, SurrealDB, Redis, Postgres |
| MCP Live Write | Jede MCP-Operation mit Write-Intent |
| Trading/Risk/Execution Impact | Jede Operation, die Trading-, Risk- oder Execution-Verhalten berührt |
| Live-Readiness/Echtgeld Claims | Jede Aussage über LR-Go, Echtgeld-Freigabe, Live-Kapital |
| Cross-Agent Memory Handoff | Memory-Schreiboperationen über Agent-Grenzen hinaus (write-capable / beyond-read-only Future-Scope; nicht Teil der v0 Agent-OS-Readiness-Kriterien) |

Human-GO muss **vor** der Operation eingeholt werden, nicht nachträglich.
Human-GO ist eine **explizite, dokumentierte Entscheidung**, keine implizite Annahme.

## 10. Klarstellungen

- **Agent OS Ready ist keine Freigabe.** Es signalisiert nur, dass das CIS technisch
  als Agent Operating System fungiert. Es autorisiert keine Aktion.
- **Agent OS Ready ist kein Live-Readiness-Go.** Live-Readiness wird ausschließlich
  durch `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` bestimmt.
- **Agent OS Ready ist kein Echtgeld-Go.** Kein Kapital, kein Live-Trading,
  keine Order-Ausführung wird durch Agent OS Ready autorisiert.
- **Board-Stage und LR bleiben orthogonal.** `trade-capable` ist eine Board-Stage
  und impliziert weder LR-Go noch Agent-OS-Go.
- **LR bleibt SSOT** in `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`.
  Kein anderes Dokument darf LR-Status überschreiben oder relativieren.

## 11. Example Assessment — Current Known State

**Datum**: 2026-05-04
**Bewertung basiert auf**: GitHub-Issue-States und vorhandener Evidence.

| Stufe | Status | Begründung |
|-------|--------|-----------|
| `context_foundation_ready` | **NICHT ERREICHT** | Kein Indexer-Scaffold implementiert (#2045 offen). Keine Ingest-Pipeline. Kein SurrealDB-Import. Ontology v0 existiert als YAML (#2038), aber nicht geladen/querybar. |
| `ingestion_ready` | **NICHT ERREICHT** | Hängt von Stufe 1 ab. Keine Indexer-/Export-Pipeline. |
| `graph_ready` | **NICHT ERREICHT** | Hängt von Stufe 1–2 ab. Kein Knowledge Graph aufgebaut. |
| `evidence_ready` | **NICHT ERREICHT** | Hängt von Stufe 1–3 ab. Evidence Fabric nicht implementiert. |
| `briefing_ready` | **NICHT ERREICHT** | Hängt von Stufe 1–4 ab. Keine Briefing Engine. |
| `governance_intelligence_ready` | **NICHT ERREICHT** | Hängt von Stufe 1–5 ab. Keine Contradiction Detection oder Scope Drift Firewall. |
| `agent_os_ready` | **NICHT ERREICHT** | Hängt von Stufe 1–6 ab. Keine Stufe erfüllt. |

**Evidence-Lage**:

- ✅ #2189 CLOSED: Self-Explanation Builder v1 existiert
- ✅ #2190 CLOSED: Read-only Self-Explanation MCP Tool existiert
- ✅ #2092: Context Tool Contracts v0 sind dokumentiert
- ❌ #2032 OPEN: Kriterienkatalog (dieses Dokument) wird erstellt
- ❌ #2098 OPEN: Agent Readiness Check v0 fehlt
- ❌ #2121 OPEN: Trust Summary Builder v1 fehlt
- ❌ #2191 OPEN: Agent OS Readiness Evaluator fehlt
- ❌ #2188 OPEN: Wave-20 Anchor
- ❌ #2196 OPEN: Completion Gates

**Issue-Status-Hinweis**: Dieses Dokument definiert den Kriterienkatalog für #2032.
#2032 bleibt bis zum Merge und anschließendem Reconciliation/Close offen. Nach Merge
dieses PR kann #2032 reconciled und geschlossen werden. #2191 (Evaluator) bleibt
separater Scope und wird durch diesen Kriterienkatalog nicht abgeschlossen.

**Ergebnis**: Nicht `agent_os_ready`. Die fundamentalen Implementierungswellen 8–14
sind noch nicht gelandet. Self-Explanation ist der einzige Teilbereich von Wave 20,
der bereits geschlossen ist.

## 12. Example Assessment — Target State

**Ziel**: Alle sieben Readiness-Stufen sind erfüllt.

| Stufe | Ziel-Status | Voraussetzung |
|-------|-------------|--------------|
| `context_foundation_ready` | PASS | Indexer Scaffold, Ingest-Pipeline, SurrealDB-Import (Wellen 8–10) |
| `ingestion_ready` | PASS | Deterministische Hashes, Schema-valider Export |
| `graph_ready` | PASS | Knowledge Graph mit Knoten/Kanten, Trace-Endpoint (Wellen 9–11) |
| `evidence_ready` | PASS | Evidence Fabric, Source-Hashes, Confidence (Wellen 12–14) |
| `briefing_ready` | PASS | Agent Briefing Engine, Context Package (Wellen 13–14) |
| `governance_intelligence_ready` | PASS | Contradiction Detection, Scope Drift Firewall, Stale Knowledge (Wellen 15–18) |
| `agent_os_ready` | PASS | Alle AO-01–AO-14 Kriterien, Self-Explanation aktiv (Wellen 19–21) |

**Evaluator-Nutzung**: Wenn dieser Zielzustand erreicht ist, kann der Evaluator aus
#2191 gegen diesen Kriterienkatalog prüfen und einen Readiness Report (#2193) erzeugen.

**Wichtig**: Auch im Zielzustand gilt: Agent OS Ready ist kein Live-Readiness-Go,
kein Echtgeld-Go, keine Autonomie ohne Human Gates.

## 13. Validation

Die Validierung dieses Kriterienkatalogs erfolgt durch:

1. **Selbstkonsistenz**: Jede Stufe baut auf der vorherigen auf; keine Zirkelschlüsse.
2. **Prüfbarkeit**: Jedes Kriterium ist binär auswertbar (PASS/FAIL).
3. **Issue-Abgleich**: Kriterien decken alle in #2032 geforderten Readiness-Stufen ab.
4. **Abgrenzung**: Agent OS Ready ist klar von Live-Readiness und Echtgeld getrennt.
5. **Evaluator-Kompatibilität**: Der Kriterienkatalog ist so strukturiert, dass ein
   Evaluator (#2191) ihn maschinell abarbeiten kann.

## 14. Residual Uncertainties

1. **Implementierungsreihenfolge**: Die Wellen 8–14 (Implementierung) sind noch nicht
   begonnen. Die Kriterien basieren auf den Design-Dokumenten der Wellen 1–7.
   Änderungen an der Implementierungsreihenfolge könnten Kriterien-Anpassungen nötig machen.

2. **`shared_memory`-Rolle**: Die genaue technologische Verzahnung zwischen CIS und
   `shared_memory` ist laut `context-intelligence-system.md` "nicht final belegt".
   Kriterien, die Memory-Operationen betreffen (AO-10), können sich ändern.

3. **SurrealDB-Instanz**: Keine produktive SurrealDB-Aktivierung bisher. Alle
   Kriterien, die eine laufende SurrealDB voraussetzen (GR-03, EV-01 ff.), sind
   aktuell nicht prüfbar.

4. **Evaluator-Design**: Der Evaluator (#2191) ist noch nicht implementiert. Die
   maschinelle Prüfbarkeit der Kriterien (PASS/FAIL-Auswertbarkeit) ist konzeptionell
   gegeben, aber nicht durch Implementierung bestätigt.

5. **Cross-Agent Memory Handoff**: Die Regeln für Memory-Schreiboperationen über
    Agent-Grenzen hinweg sind in der Ontologie v0 als Konzept angelegt, aber die
    konkreten Contracts sind noch nicht spezifiziert. Write-capable Memory Contracts
    sind nicht Teil dieses read-only Kriterienkatalogs und müssen separat
    spezifiziert werden, bevor sie in eine künftige Agent-OS-Readiness-Stufe
    aufgenommen werden können.

## 15. Boundary: Agent OS Ready != Live Readiness

Diese Abgrenzung ist **kategorisch** und darf nicht aufgeweicht werden:

| Dimension | Agent OS Ready | Live Readiness |
|-----------|---------------|----------------|
| **Zuständigkeit** | Context Intelligence System | Trading Runtime |
| **SSOT** | Dieses Dokument + Evaluator #2191 | `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` |
| **Signalisiert** | Technische Kontext-/Agentenfähigkeit des CIS (read-only) | — |
| **Autorisiert** | Keine Aktion. Kein Write, kein Runtime-Mutate, kein DB-Mutate. | — |
| **Echtgeld-Freigabe** | Wird **nicht** erteilt. Bleibt separaten LR- und Human-Gate-Prozessen vorbehalten. | Wird **nicht allein** durch Live Readiness erteilt. Erfordert zusätzlich explizites Human-GO. |
| **Aktueller Status** | Nicht erreicht (Kriterien definiert) | NO-GO |
| **Board-Stage** | Orthogonal | Orthogonal |

## Provenance / Quellen

- **Issue**: #2032 — Define agent operating system readiness criteria
- **Epic**: #1976 — CDB Context Intelligence System
- **Wave-20 Anchor**: #2188
- **Context Issues (read)**: #2032 (OPEN), #2098 (OPEN), #2121 (OPEN), #2188 (OPEN), #2191 (OPEN), #2196 (OPEN)
- **Evidence Issues (closed)**: #2189 (Self-Explanation Builder v1), #2190 (Self-Explanation MCP Tool)
- **Referenz-Dokumente**:
  - `docs/surrealdb/context-intelligence-system.md` (#2035)
  - `docs/surrealdb/context-ontology-v0.yaml` (#2038)
  - `docs/surrealdb/context-intelligence-roadmap.md` (#2036)
  - `docs/surrealdb/context-tool-contracts-v0.md` (#2092)
  - `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
  - `docs/runbooks/CONTROL_REGISTER.md`
  - `CURRENT_STATUS.md`
