# Migrationsplan zur technischen Validierung durch Claude

**Erstellt von:** Gemini (Senior Repository Architect & Governance Planner)
**Datum:** 2025-12-12
**Zweck:** Dieses Dokument enthält den vollständigen, von Gemini erstellten Migrationsplan und dient als direkte Eingabe für eine technische Validierung durch die Claude-Persona.

---

### 1. Zusammenfassung: Ist-Zustand vs. Ziel-Struktur & Risiken

*   **Ist-Zustand:** Das Repository besteht aus einer leeren Ziel-Struktur (`/core`, `/services` etc.) und einer Sammlung von Governance-Dokumenten. Der eigentliche Anwendungs-Code existiert derzeit nur als *logisches Inventar* in `CDB_REPO_INDEX.md`, aufgeteilt in Tiers (T1/T2/T3).
*   **Ziel-Struktur:** Das in den Briefings definierte Ziel-Schema ist logisch, klar und entspricht modernen Best Practices (IaC, Service-Trennung, K8s-Readiness). Es behebt die Mängel der historisch gewachsenen Struktur.
*   **Kritische Inkonsistenz/Risiko:** Die größte Herausforderung ist, dass die Quell-Dateien für die Migration (`t1/`, `t2/`, `t3/`) im aktuellen `HEAD` nicht physisch vorhanden sind. Der ausführende Migrations-Agent (`Codex`) muss instruiert werden, diese Dateien aus einem früheren Git-Commit oder einem bereitgestellten Archiv zu beziehen. Mein Migrationsplan wird diese logischen `SourcePath`-Angaben verwenden, da sie die "historische Wahrheit" darstellen.

### 2. Vollständiger Migrationsplan

Dieser Plan ist die Single Source of Truth für den Migrations-Agenten. Er listet alle bekannten Dateien aus dem `CDB_REPO_INDEX.md` sowie die aktuell im `HEAD` vorhandenen Projekt- und Governance-Dateien auf.

**Tabelle 1: Governance- & Root-Dateien**

| ID | SourcePath | TargetPath | Action | Tier | Owner/Domain | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| MIG-G001 | `CDB_REPO_STRUCTURE.md` | `governance/CDB_REPO_STRUCTURE.md` | MOVE | - | governance | Zentralisiert Repo-Meta-Dokumentation. |
| MIG-G002 | `CDB_REPO_INDEX.md` | `governance/CDB_REPO_INDEX.md` | MOVE | - | governance | Zentralisiert Repo-Meta-Dokumentation. |
| MIG-G003 | `CDB_REPO_MIGRATION_BRIEF.md` | `governance/archive/CDB_REPO_MIGRATION_BRIEF.md` | MOVE | - | governance | Als historisches Briefing archivieren. |
| MIG-G004 | `PROMPT.txt` | `governance/archive/PROMPT.txt` | MOVE | - | governance | Als historisches Briefing archivieren. |
| MIG-G005 | `governance/` | `governance/` | HOLD | - | governance | Bestehende Governance-Dateien bleiben. |
| MIG-G006 | `.github/CODEOWNERS` | `.github/CODEOWNERS` | HOLD | - | devops | Bleibt, muss aber nach Migration aktualisiert werden. |
| MIG-G007 | `.github/pull_request_template.md` | `.github/PULL_REQUEST_TEMPLATE.md` | HOLD | T2 | devops | Umbenennung zu `.github/PULL_REQUEST_TEMPLATE.md` empfohlen. |
| MIG-G008 | `.gitignore` | `.gitignore` | HOLD | T1 | root | Inhalt muss ggf. nach Migration angepasst werden. |
| MIG-G009 | `nul` | `(none)` | DROP | - | - | Leere Datei, wird nicht benötigt. |
| MIG-G010 | `.claude/` | `.claude/` | HOLD | - | agent-config | Agenten-Konfiguration, ist `gitignored`. |

**Tabelle 2: Tier 1 Migration (Essential Core)**

| ID | SourcePath | TargetPath | Action | Tier | Owner/Domain | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| MIG-T1-001 | `t1/.dockerignore` | `.dockerignore` | MOVE | T1 | root | Globale Docker-Ignore-Datei. |
| MIG-T1-002 | `t1/.env.example` | `.env.example` | MOVE | T1 | root | Globale Konfigurationsvorlage. |
| MIG-T1-003 | `t1/docker-compose.yml` | `docker-compose.yml` | MOVE | T1 | root | Haupt-Compose-Datei. |
| MIG-T1-004 | `t1/Makefile` | `Makefile` | MOVE | T1 | root | Haupt-Makefile. |
| MIG-T1-005 | `t1/pytest.ini` | `pytest.ini` | MOVE | T1 | root | Globale Test-Konfiguration. |
| MIG-T1-006 | `t1/requirements.txt` | `(none)` | DROP | T1 | root | Veraltet, Dependencies sind service-spezifisch. |
| MIG-T1-007 | `t1/requirements-dev.txt`| `(none)` | DROP | T1 | root | Veraltet, Dev-Dependencies sind service-spezifisch. |
| MIG-T1-008 | `t1/DATABASE_SCHEMA.sql` | `infrastructure/database/schema.sql` | MOVE | T1 | infra-db | Zentrales DB-Schema. |
| MIG-T1-009 | `t1/migrations/` | `infrastructure/database/migrations/` | MOVE | T1 | infra-db | DB-Migrationen. |
| MIG-T1-010 | `t1/prometheus.yml` | `infrastructure/monitoring/prometheus.yml` | MOVE | T1 | infra-mon | Prometheus-Konfiguration. |
| MIG-T1-011 | `t1/grafana/` | `infrastructure/monitoring/grafana/` | MOVE | T1 | infra-mon | Grafana-Dashboards und Provisioning. |
| MIG-T1-012 | `t1/run-tests.ps1` | `infrastructure/scripts/run-tests.ps1` | MOVE | T1 | devops | Test-Ausführungsskript. |
| MIG-T1-013 | `t1/.github/workflows/ci.yaml` | `.github/workflows/ci.yaml` | MOVE | T1 | devops | CI-Workflow. |
| MIG-T1-014 | `t1/Dockerfile` | `(none)` | DROP | T1 | root | Veraltet, Dockerfiles sind service-spezifisch. |
| MIG-T1-015 | `t1/cdb_paper_runner/` | `services/market/` | MOVE | T1 | service-market| Umbenennung `cdb_paper_runner` zu `market`. |
| MIG-T1-016 | `t1/db_writer/` | `services/db_writer/` | MOVE | T1 | service-db | Service bleibt bestehen. |
| MIG-T1-017 | `t1/execution_service/`| `services/execution/` | MOVE | T1 | service-exec | Umbenennung `execution_service` zu `execution`. |
| MIG-T1-018 | `t1/risk_manager/` | `services/risk/` | MOVE | T1 | service-risk | Service bleibt bestehen. |
| MIG-T1-019 | `t1/signal_engine/` | `services/signal/` | MOVE | T1 | service-signal| Service bleibt bestehen. |
| MIG-T1-020 | `t1/tests/unit/` | `tests/unit/` | MOVE | T1 | tests | Leere Unit-Test-Ordner. |
| MIG-T1-021 | `t1/tests/README.md` | `tests/README.md` | MOVE | T1 | tests | Doku für Tests. |

**Tabelle 3: Tier 2 & 3 Migration (Tools, Legacy, Research)**

| ID | SourcePath | TargetPath | Action | Tier | Owner/Domain | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| MIG-T2-001 | `t2/.github/` | `.github/` | MOVE | T2 | devops | Templates für Issues und PRs. |
| MIG-T2-002 | `t2/services/execution_simulator.py` | `tests/integration/execution_simulator.py` | MOVE | T2 | tests | Klares Test-Tool, kein Prod-Service. |
| MIG-T3-001 | `t3/backoffice/` | `archive/backoffice/` | HOLD | T3 | ops-legacy | Veraltete Ops-Skripte, als Referenz halten. |
| MIG-T3-002 | `t3/scripts/` | `archive/scripts/` | HOLD | T3 | dev-tools | Veraltete Dev-Tools, als Referenz halten. |
| MIG-T3-003 | `t3/scripts/security_audit.sh` | `infrastructure/scripts/security_audit.sh` | MOVE | T3 | infra-sec | Nützliches Skript, wird übernommen. |
| MIG-T3-004 | `t3/services/cdb_paper_runner/` | `(none)` | DROP | T3 | service-market| Duplikat/Alternative zu T1-Version. |
| MIG-T3-005 | `t3/backoffice/services/portfolio_manager/`|`(none)`| DROP | T3 | service-psm | Veraltet, wird durch neuen PSM-Service ersetzt. |
| MIG-T3-006 | `t3/tests/` | `archive/tests-experimental/` | HOLD | T3 | research | Experimentelle Tests, nicht für CI. |
| MIG-T3-007 | `scripts/validate_write_zones.sh` | `infrastructure/scripts/validate_write_zones.sh` | MOVE | - | devops | CI-Skript, gehört zur Infrastruktur. |

### 3. Vorschläge für Governance-Dokumente

**3.1. Vorschlag für `CDB_REPO_STRUCTURE.md`**

```markdown
# CDB Repository Structure (v2.0)
Date: 2025-12-12
Status: Final Target Layout

## 1. Top-Level-Struktur

Dieses Schema ist die Single Source of Truth für die Organisation des Repositories.

/ (repo root)
├── core/
├── services/
├── infrastructure/
├── tests/
├── governance/
├── .github/
├── .cdb_agent_workspace/ (gitignored)
├── CDB_KNOWLEDGE_HUB.md
├── .gitignore
├── .dockerignore
├── docker-compose.yml
├── Makefile
├── README.md
└── LICENSE

## 2. Ordner-Definitionen

*   **/core/**: Geteilte Bibliotheken und Domänenlogik (Events, Models). Stabil und selten geändert.
*   **/services/**: Alle laufenden Applikations-Komponenten. Jeder Ordner ist ein stateless, containerisierter Microservice.
*   **/infrastructure/**: Infrastructure as Code (IaC). Enthält alles für Deployment, Monitoring, Datenbank-Schemata und CI/CD-Skripte.
*   **/tests/**: Alle Tests (Unit, Integration, Replay). Die Struktur spiegelt die `/services`-Struktur wider.
*   **/governance/**: Das Gehirn des Projekts. Alle Policies, Agenten-Guides und Meta-Dokumente wie dieses hier. **SINGLE SOURCE OF TRUTH**.
*   **/.github/**: GitHub-spezifische Konfigurationen wie CI-Workflows und PR-Templates.
*   **/CDB_KNOWLEDGE_HUB.md**: Der einzige Ort, an dem KI-Agenten persistent in das Repository schreiben. Dient als Logbuch und Wissensspeicher.
```

**3.2. Vorschlag für `CDB_REPO_INDEX.md`**

Dieses Dokument sollte nach der Migration den **finalen Zustand** widerspiegeln, nicht den historischen.

```markdown
# CDB Repository Index (v2.0)
Date: 2025-12-12
Status: Post-Migration

Dieses Dokument listet den finalen Ort aller relevanten Dateien nach der Restrukturierung auf.

## / (root)
- .dockerignore
- .env.example
- .gitignore
- docker-compose.yml
- Makefile
- pytest.ini
- README.md
- LICENSE
- CDB_KNOWLEDGE_HUB.md

## /core
- /core/domain/
- /core/config/
- /core/utils/

## /services
- /services/market/
- /services/signal/
- /services/risk/
- /services/execution/
- /services/db_writer/
- /services/psm/ (Ziel, noch leer)

## /infrastructure
- /infrastructure/database/
- /infrastructure/monitoring/
- /infrastructure/compose/
- /infrastructure/k8s/
- /infrastructure/scripts/

## /tests
- /tests/unit/
- /tests/integration/
- /tests/replay/
- /tests/README.md

## /governance
- (Liste aller .md Dateien)
```

### 4. Optionale Hinweise & Unsicherheiten

*   **Abhängigkeit zu Git History:** Der Plan setzt voraus, dass der Migrations-Agent (`Codex`) Zugriff auf die Git-Historie hat, um die `t1/`, `t2/`, `t3/` Inhalte abzurufen. Dies muss im Skript berücksichtigt werden.
*   **Service-interne Struktur:** Der Plan migriert Service-Ordner als Ganzes (z.B. `t1/risk_manager/` nach `services/risk/`). Eine detailliertere Refaktorierung *innerhalb* der Services (z.B. Aufteilung von `models.py` in `/core/domain`) ist ein nachgelagerter Schritt und nicht Teil dieser strukturellen Migration.
*   **`requirements.txt` Konsolidierung:** Ich habe die Root-`requirements.txt`-Dateien als `DROP` markiert. Die Annahme ist, dass jeder Service seine eigenen Dependencies in seinem Verzeichnis verwalten wird. Dies muss im Build-Prozess (Makefile, Dockerfiles) berücksichtigt werden.



# CDB – Repo-Struktur & Migrationsbriefing (für Claude)

## 1. Kontext & Ziel

Dieses Briefing bündelt den aktuellen Stand zur geplanten Neustrukturierung des Repositories *Claire de Binare v2.0* und dient als Eingabe für eine Roadmap-/Timetable-Erstellung durch Claude.

Kernentscheidungen des Owners (Jannek):

- **Struktur zuerst, Inhalt später.**
- **Tier‑1-Code und kritische Services bleiben solange unsichtbar**, bis die neue Struktur steht und der Altbestand sauber einsortiert ist.
- Das von Gemini vorgeschlagene Ziel-Schema (Tree-View) wird als **Zielbild** verwendet, darf aber bei Bedarf optimiert werden.
- Die eigentliche Migration erfolgt **deterministisch per Skript**, nicht manuell per „Klicken & Ziehen“.

Claude soll auf Basis dieses Briefings eine phasenbasierte Roadmap mit Timetable und klarer Aufgabenverteilung erstellen.

---

## 2. Finales Ziel-Schema (Tree-View, read-only)

Aktuelles Zielbild der Repo-Struktur (aus Gemini/Claude-Analyse, als logisches Ziel, nicht zwingend 1:1 final):

```text
/ (repo root)
├── core/                           # Shared Libraries & Domain Logic (KI read-only)
│   ├── domain/                     # Events, Models, Schemas, Contracts
│   ├── config/                     # Typed config loader, env mapping
│   └── utils/                      # Shared helpers
├── services/                       # Stateless Runtime Services (KI read-only)
│   ├── market/
│   ├── signal/
│   ├── risk/
│   ├── execution/
│   ├── psm/                        # Portfolio & State Manager
│   └── (weitere services)
├── infrastructure/                 # IaC, Deployment, Ops (KI read-only)
│   ├── compose/                    # Docker-Compose fragments & env templates
│   ├── k8s/                        # K8s manifests / Helm (zukünftig)
│   ├── database/                   # Schema, migrations
│   ├── monitoring/                 # Prometheus, Grafana provisioning
│   └── scripts/                    # Ops & CI/CD scripts (z.B. validate_write_zones.sh)
├── tests/                          # Unit, Integration, Replay Tests (KI read-only)
│   ├── unit/
│   ├── integration/
│   └── replay/
├── governance/                     # SINGLE SOURCE OF TRUTH (Policies, Agent Guides)
│   ├── CDB_CONSTITUTION.md
│   ├── CDB_GOVERNANCE.md
│   ├── CDB_AGENT_POLICY.md
│   ├── CDB_INFRA_POLICY.md
│   ├── CDB_PSM_POLICY.md
│   ├── (weitere Policies)...
│   ├── CLAUDE.md                   # Agent Guide
│   ├── GEMINI.md                   # Agent Guide
│   ├── NEXUS.MEMORY.md             # System Memory
│   ├── CDB_REPO_STRUCTURE.md       # Repo-Blaupause (dieses Schema)
│   └── CDB_REPO_INDEX.md           # File Inventory & Tier-Mapping
├── .github/                        # CI/CD, PR Templates, CODEOWNERS
│   └── workflows/
│       └── ci.yaml
├── .cdb_agent_workspace/           # KI Local Workspace (GITIGNORED)
│
├── CDB_KNOWLEDGE_HUB.md            # Einzige KI-beschreibbare Datei im Repo (Log/Audit-Trail)
├── .gitignore
├── .dockerignore
├── docker-compose.yml              # Haupt-Compose-Datei
├── Makefile
├── README.md
└── LICENSE
```

Dieses Schema ist das **Skelett**, das zunächst (weitgehend) leer angelegt wird. Inhalte werden erst nach explizitem Go des Owners schrittweise eingebracht.

---

## 3. Strategische Prinzipien & Arbeitsregeln

1. **Struktur vor Inhalt**
   - Zuerst wird die finale Ordnerstruktur erzeugt (ggf. mit minimalen Pflichtdateien wie README/Policies).
   - Tier‑1-Code (core, services) wird erst migriert, wenn der Altbestand einsortiert und freigegeben ist.

2. **Tier‑1 bleibt vorerst unsichtbar**
   - Keine neuen Tier‑1-Dateien anlegen.
   - Keine halbfertigen Services oder Skeleton-Implementierungen.
   - Tier‑1 kommt erst, wenn:
     - die Struktur stabil ist und
     - der Owner das explizit freigibt.

3. **Klare Trennung Governance vs. Arbeitsflächen**
   - `governance/` enthält alle kanonischen Policies & Governance-Dokumente.
   - `CDB_KNOWLEDGE_HUB.md` ist **der einzige** KI-beschreibbare Ort im Repo.
   - `.cdb_agent_workspace/` ist lokal, gitignored, frei für Agent-„Gekritzel“, aber ohne Governance-Relevanz.

4. **Deterministische Migration statt manuellem Chaos**
   - Keine Ad-hoc-Verschiebungen im Dateisystem.
   - Alle Moves/Renames/Archive-Läufe erfolgen skriptbasiert und nachvollziehbar.
   - Ziel: Ein sauberer Migrations-Commit statt Dutzender inkonsistenter Änderungen.

5. **Owner bleibt Kontrollinstanz**
   - Nur der Owner hebt Phasen-Grenzen auf (z.B. Freigabe Tier‑1, Start Migration).
   - Dev-Freeze ist jederzeit möglich und verbindlich.

---

## 4. Logische Migrationsphasen (ohne Zeitangaben)

Diese Phasen sind **logisch**, nicht zeitlich. Claude soll daraus einen Timetable ableiten.

### Phase 0 – Governance Lock-In

Ziel: Zielbild und Spielregeln festnageln, bevor sich jemand bewegt.

- Dieses Briefing + Ziel-Schema als „Truth Source“ bestätigen.
- Format für den Migrationsplan definieren (siehe Abschnitt 5).
- Schreibregeln klarziehen:
  - Keine unkoordinierten File-Moves.
  - Ordnerstrukturänderungen nur im Rahmen der geplanten Migration.
- Optional: Branch für die Migration vorsehen (z.B. `feature/repo-structure-migration`).

### Phase 1 – Struktur-Skelett anlegen (leere Ordner)

Ziel: Die Struktur ist sichtbar, aber noch nicht mit Altlasten gefüllt.

- Alle Ziel-Ordner gemäß Tree-View anlegen.
- Ordner bleiben inhaltlich leer oder nur mit minimalen Pflicht-Dateien (z.B. `README.md` oder bestehende Governance-Dateien).
- Keine neuen Services, keine neuen Code-Artefakte.

### Phase 2 – Bestandsaufnahme & Migrationsplan (Gemini)

Ziel: Vollständiger, tabellarischer Migrationsplan auf Dateiebene.

Aufgaben für Gemini (Analyse, keine Dateisystemoperationen):

- Vollständiger Scan des Repos (aktueller Zustand).
- Abgleich mit `CDB_REPO_STRUCTURE.md` und `CDB_REPO_INDEX.md`.
- Erstellung eines Migrationsplans `governance/CDB_REPO_MIGRATION_PLAN_YYYYMMDD.md`.

Der Plan enthält pro Datei u.a.:

- aktuellen Pfad
- Zielpfad
- Aktion (MOVE | HOLD | ARCHIVE | DROP)
- Tier (T1/T2/T3, falls relevant)
- Verantwortliche Rolle / Service
- Kommentar (z.B. „deprecated“, „legacy“, „kandidat für rewrite“)

Beispiel-Struktur siehe Abschnitt 5.

Phase-Ende:
- Owner reviewed und genehmigt den Plan.

### Phase 3 – Deterministische Ausführung (Codex)

Ziel: Migrationsplan technisch exekutieren, ohne Inhalte zu verändern.

Aufgaben für Codex:

1. PowerShell-Skript implementieren, z.B.  
   `infrastructure/scripts/migrate_repo_structure.ps1` mit u.a.:
   - Einlesen des Migrationsplans (Markdown-Tabelle oder JSON-Export).
   - Ausführen der definierten Aktionen (MOVE/HOLD/ARCHIVE).
   - `-WhatIf`/Dry-Run-Option für Preview.
2. Ausführung in einem separaten Branch:
   - Dry-Run + Log.
   - Real-Run nach Freigabe.
3. Nachlauf:
   - `git status` prüfen (nur erwartete Änderungen).
   - Aktualisierung von `CDB_REPO_INDEX.md` falls nötig.

Keine Refactorings, keine inhaltlichen Änderungen, keine Policy-Änderungen.

### Phase 4 – Post-Migrations-Review & Stabilisierung

Ziel: Sicherstellen, dass Struktur und Governance konsistent sind.

- Struktur-Review durch Gemini/Claude:
  - Ist der reale Tree = Ziel-Schema (oder bewusst dokumentierte Abweichungen)?
  - Stimmen `CDB_REPO_INDEX.md` und `CDB_REPO_STRUCTURE.md` mit dem tatsächlichen Zustand überein?
- Anpassung von CI/Workflows:
  - Pfade für Scripts (z.B. `validate_write_zones.sh`) aktualisieren.
  - CODEOWNERS für `/core`, `/services`, `/governance` aktivieren.
- Erst wenn diese Phase abgeschlossen ist: Owner-Go für die schrittweise Einführung von Tier‑1-Code.

---

## 5. Formales Schema für den Migrationsplan

Empfohlene Struktur für `governance/CDB_REPO_MIGRATION_PLAN_YYYYMMDD.md`:

```markdown
# CDB_REPO_MIGRATION_PLAN_YYYYMMDD

| ID      | SourcePath                                   | TargetPath                              | Action   | Tier | Owner/Domain | Notes                               |
|---------|----------------------------------------------|-----------------------------------------|---------|------|-------------|-------------------------------------|
| MIG-001 | misc/CDB_GOVERNANCE_alt.md                  | governance/CDB_GOVERNANCE.md            | MOVE    | T1   | governance  | Alt-Doku wird zur kanonischen Datei |
| MIG-002 | scratch/old_backtest_script.py              | (none)                                  | ARCHIVE | T3   | research    | Lokal sichern, nicht ins neue Repo |
| MIG-003 | governance/legacy/CDB_REPO_STRUCTURE_old.md | governance/CDB_REPO_STRUCTURE_legacy.md | HOLD    | T2   | governance  | Historische Referenz                |
```

Varianten / Anmerkungen:

- **Action**:
  - `MOVE`  → verschieben/umbenennen in Zielstruktur
  - `HOLD`  → bewusst parken (z.B. `archive/`-Ordner)
  - `ARCHIVE` → aus Repo entfernen, aber lokal sichern
  - `DROP` → bewusst verwerfen (nur nach harter Freigabe)
- Der Plan kann bei Bedarf zusätzlich als `.json` exportiert werden, um das Skript zu vereinfachen.

Claude soll auf Basis dieses Schemas u.a. definieren:
- Wer liefert den Plan final (Gemini)?
- In welchem Format braucht Codex ihn bestmöglich (Markdown vs. JSON)?
- Welche Reviews/Gates vor Ausführung Pflicht sind.

---

## 6. Rollen & Verantwortlichkeiten

**Owner (Jannek)**  
- Bestätigt Ziel-Schema und dieses Briefing.  
- Gibt Migrationsplan frei (oder schiebt Dev-Freeze).  
- Gibt Tier‑1-Einführung frei.  

**Gemini – Struktur & Planung**  
- Vollständige Bestandsaufnahme des Repos (lesend).  
- Pflege/Erstellung von:
  - `governance/CDB_REPO_STRUCTURE.md` (Ziel-Schema)
  - `governance/CDB_REPO_INDEX.md` (Ist-Bestand + Tier-Mapping)
  - `governance/CDB_REPO_MIGRATION_PLAN_YYYYMMDD.md` (tabellarisches Mapping)  
- Keine Dateisystem-Operationen, keine inhaltlichen Refactorings.

**Codex – Deterministische Ausführung**  
- Implementiert das Migrationsskript (PowerShell).  
- Führt die Migration *nur* anhand des Plans aus.  
- Kein inhaltliches Editieren von Dateien, kein „Mitdenken“ bei Strukturänderungen.  
- Arbeitet in separatem Branch, liefert sauberen Migrations-Commit.

**Claude – Governance & Roadmap (dieses Briefing ist Input)**  
- Erstellt eine **Roadmap mit Timetable** für die Phasen 0–4.  
- Schärft Aufgabenpakete, Abhängigkeiten und Milestones.  
- Definiert Review-/Freigabepunkte (z.B. Owner-Signoff, Gemini-Review, Codex-Ausführung).  
- Optional: Ergänzt Risks & Mitigations je Phase.

---

## 7. Konkreter Auftrag an Claude

> **Ziel für Claude:**  
> Erstelle auf Basis dieses Briefings eine phasenbasierte Roadmap inkl. Timetable, Aufgabenverteilung und Freigabepunkten.

Erwarteter Output von Claude (Vorschlag):

1. **Übersichtstabellen je Phase**  
   - Tasks, Verantwortliche (Owner/Gemini/Codex/Claude), Abhängigkeiten.

2. **Zeitliche Einordnung (Timetable)**  
   - Realistische Reihenfolge, keine exakten Tage zwingend nötig, aber klare Sequenz und Mindestvoraussetzungen.

3. **Checklisten & Done-Kriterien je Phase**  
   - Woran erkennen wir, dass Phase X wirklich abgeschlossen ist?

4. **Risiko- & Governance-Notizen**  
   - Wo sind Governance-Risiken (z.B. versehentliche Tier‑1-Leaks, CI-Brüche)?  
   - Welche Gates und Signoffs sind zwingend?

Dieses Dokument ist bewusst **struktur- und governance-orientiert** gehalten, damit Claude sich auf Roadmap & Orchestrierung konzentrieren kann – nicht auf technische Detaildiskussionen.
