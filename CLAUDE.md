CLAUDE.md – Cleanroom File-Sorting Protocol (KI-optimierte Version)
🔒 Verbindlicher System-Operator-Modus

---

## 🎯 Start Here (for AI Agents)

**Repository**: Claire_de_Binare_Cleanroom
**Status**: ✅ Cleanroom Baseline established (2025-11-16)
**Current Phase**: N1 - Paper-Test Vorbereitung

**Central Orientation Point**:
📖 **[CLEANROOM_ONBOARDING_AND_REPO_NAVIGATION.md](backoffice/docs/CLEANROOM_ONBOARDING_AND_REPO_NAVIGATION.md)**

This document provides:
- Complete repository structure overview
- Canonical document locations
- Naming conventions
- Development workflow
- Quick links to all key resources

**Before starting any task**: Read the onboarding document to understand the repository structure and current state.

---

#0 – Mission

Du arbeitest im Repository:

Claire_de_Binare_Cleanroom/


Dein Auftrag:

🔶 ALLE Dateien (inkl. sandbox/) korrekt einsortieren → ohne zu löschen, ohne zu interpretieren.

Goldene Regeln:

❌ Nichts löschen

❌ Nichts überschreiben

❌ Nichts umbenennen

❌ Keine Inhaltsanalyse

✔️ Nur verschieben/kopieren nach Regeln

✔️ Duplikate behandeln nach Datum

Neuere → einsortieren

Ältere → am Ursprungsort belassen

#1 – Fundamentale Operator-Regeln
1.1 Du DARFST NICHT:

❌ Dateien löschen

❌ Dateien überschreiben

❌ Dateien zusammenführen



❌ Code analysieren

❌ Dokumentation logisch auswerten

1.2 Du DARFST:

✔️ Ordnerstruktur rekursiv scannen

✔️ Dateinamen & Änderungsdatum nutzen

✔️ Dateien verschieben

✔️ Dateien kopieren

✔️ Duplikate erkennen (Name + Datum)

✔️ Unklarheiten melden

✔️ Bewegungen protokollieren


#4 – Dateimapping (Klare Routing-Logik)
4.1 Architektur

ARCHITEKTUR, FLUSSDIAGRAMM, SYSTEMFLOW
→ docs/architecture/

4.2 Services / Events / Topics

SERVICE_DATA_FLOWS.md
→ docs/services/

4.3 Security

HARDENING.md, infra_conflicts.md
→ docs/security/

4.4 Kanonisches Schema

canonical_schema.yaml

Hauptversion → backoffice/docs/schema/

Optional Kopie → docs/schema/

4.5 Knowledge-Layer

input.md, output.md, extracted_knowledge.md, conflicts.md
→ docs/knowledge/

4.6 Provenance / Pipeline-Historie

EXECUTIVE_SUMMARY.md
PIPELINE_COMPLETE_SUMMARY.md
FINAL_STATUS.md
sources_index.md
extraction_log.md
Claire-de-Binare – Projektindex.md
INDEX.md
→ docs/provenance/

4.7 Runbooks & Checklists

MIGRATION_READY.md
pre_migration_checklist.md
PRE_MIGRATION_README.md
PRE_MIGRATION_EXECUTION_REPORT.md
→ docs/runbooks/ oder docs/infra/

4.8 Backoffice Templates

project_template.md, infra_templates.md
→ backoffice/templates/

4.9 Infra-Index

file_index.md, repo_map.md, env_index.md, infra_knowledge.md, test_coverage_map.md
→ backoffice/docs/infra/

4.10 Meetings

MEETINGS_SUMMARY.md
→ docs/meetings/

4.11 Kodex / Governance

KODEX – Claire de Binaire.md
DECISION_LOG.md
→ Root von docs/
→ Kopie nach backoffice/docs/

#5 – Duplikate (Har­te Regel)

Wenn Dateien denselben Namen haben:

🔶 1. Änderungsdatum vergleichen
🔶 2. Neuere Version einsortieren
🔶 3. Ältere bleibt am Ursprungsort
🔶 4. Niemals löschen

Jede Entscheidung wird im Duplikat-Report dokumentiert.

#6 – Ablauf (Pipeline)
6.1 – Repo scannen

Erstelle rekursiven Baum (max. Tiefe 4)

Liste jede Datei vollständig auf

6.2 – Migrationsplan erzeugen

Für jede Datei:

| Quelle | Ziel | Begründung | Duplikat-Status | Aktion |

6.3 – Einsortieren

Moves gemäß Tabelle durchführen

Sandbox respektieren

Trennungsregeln beachten

6.4 – Abschlussbericht

Alle Moves

Alle Duplikate

Alle nicht einsortierten Dateien

Strukturvalidierung

#7 – Verbote (nochmal klar & laut)

❌ Inhalte lesen
❌ Inhalte interpretieren
❌ Dateien löschen
❌ Dateien verändern
❌ Dateien umbenennen
❌ Ordner erfinden, die nicht in Kapitel 3 stehen
❌ Doku-Welten zusammenführen

#8 – Sandbox-Regel

Der Ordner:

sandbox/


ist archiviert aber voll gültig.

Du:

sortierst Dateien aus sandbox/ ein

verschiebst nur Kopien

löscht nie Dateien in sandbox/

markierst unsichere Fälle als Review nötig

#9 – Zielzustand

Repository vollständig sortiert

Keine Datei verloren

Sandbox vollständig erhalten

Neue Dateien korrekt eingeordnet

Alte Versionen sichtbar im Root

Vollständige Dokumentation erzeugt

#10 – Multi-Agent Verification Protocol (obligatorisch)
🔶 Nach dem Sortieren MUSST du weitere KI-Agenten hinzuziehen.
10.1 – Vollständigen Snapshot erzeugen

Baum vor Sortierung

Baum nach Sortierung

Move-Liste

Duplikatliste

„Review nötig“-Liste

10.2 – Mindestens 2 externe KI-Agenten einladen

Agenten prüfen:

Pfad für Pfad

Zielstruktur

Duplikate

Falschzuordnungen

potenzielle Konflikte

Agenten dürfen NICHT:

löschen

selbst reorganisieren

Inhalte ändern

10.3 – Ergebnisse zusammenführen

Bestätigte Sortierungen

Beanstandungen

Offene Fälle

Empfehlungen

10.4 – FINAL VERIFICATION REPORT

Enthält:

VALID oder ATTENTION REQUIRED

Strukturvalidierung

Agentenfeedback

Menschliche Follow-Ups

Liste aller unsicheren Dateien

10.5 – Keine automatischen Korrekturen

Wenn Agenten Fehler finden:

→ nur melden, niemals reparieren.

#11 – Verhalten bei Inkonsistenzen

Bei fehlenden, zweideutigen oder widersprüchlichen Dateien:

→ Sortierung stoppen
→ Problem im Finalreport markieren
→ Nicht eigenständig lösen

#12 – Finale Bedingungen für „FERTIG“

Einsortierung vollständig

Multi-Agent-Verification abgeschlossen

Final Verification Report erstellt

Keine offenen unmarkierten Punkte

Zielstruktur vollständig erfüllt

 Claire de Binaire - Architecture Refactoring Plan

 Goals

 - Improve maintainability through shared modules and reduced duplication
 - Align with architecture principles (Kodex, event-driven design)
 - Enable safe refactoring via test infrastructure

 Phase 1: Foundation & Shared Infrastructure (Priority: CRITICAL)

 1.1 Create Shared Common Module
 - Create backoffice/common/ with shared components:
   - models.py - Canonical data models (Signal, Order, OrderResult, Alert)
   - events.py - Event base class with versioning support
   - redis_client.py - Redis connection factory
   - config_base.py - Base configuration utilities
 - Impact: Eliminates duplication across 3+ services

 1.2 Standardize Event Schemas
 - Add version field to all events (e.g., "version": "1.0")
 - Standardize field names (side not direction)
 - Enforce int timestamps consistently (no ISO strings)

 1.3 Refactor Services to Use Common Module
 - Update signal_engine, risk_manager, execution_service
 - Remove duplicated model definitions
 - Migrate to shared Redis client

 Phase 2: Service Architecture Cleanup (Priority: HIGH)

 2.1 Reorganize Screener Service
 - Move mexc_top5_ws.py → backoffice/services/screener_ws/service.py
 - Create dedicated Dockerfile (consistency with other services)
 - Update docker-compose.yml

 2.2 Split Risk Manager Responsibilities
 - Extract portfolio tracking into separate service
 - Keep risk validation as single responsibility
 - Clarify state ownership (who owns position truth?)

 2.3 Encapsulate Global State
 - Move module-level stats, risk_state into class instances
 - Enable dependency injection for testability
 - Remove global state anti-patterns

 Phase 3: Infrastructure & Quality (Priority: HIGH)

 3.1 Implement Test Infrastructure (per ADR-038)
 - Add requirements-dev.txt (pytest, pytest-cov, black, mypy)
 - Create tests/ structure with unit + integration tests
 - Target 80% coverage for Risk Manager first

 3.2 Separate Development vs Production
 - Remove source volume mounts from main docker-compose.yml
 - Create docker-compose.dev.yml override
 - Use multi-stage Docker builds

 3.3 Fix Missing Configuration Files
 - Add backoffice/logging_config.json
 - Move DATABASE_SCHEMA.sql from docs/ to backoffice/schema/
 - Complete .env.template with all options

 Phase 4: Complete Architecture Implementation (Priority: MEDIUM)

 4.1 Implement Missing Risk Layers
 - Layer 2: Market Anomaly Detector (slippage/spread monitoring)
 - Layer 3: Data Staleness Monitor
 - Layer 4: Frequency Limiter
 - Match documented 6-layer architecture

 4.2 Update Documentation
 - Sync N1_ARCHITEKTUR.md with actual implementation
 - Standardize naming (cdb_core vs Signal Engine)
 - Remove references to deleted services

 Estimated Impact

 - Code Duplication: ~40% reduction
 - Test Coverage: 0% → 80% (Risk Manager)
 - Service Clarity: Split 1 service, relocate 1 service
 - Architecture Alignment: 75% → 95%
 - Maintainability: Shared modules enable faster iterations

-----------

## Audit-Engine Routing

Wenn der Nutzer das Kommando **"audit"** ausführt:

1. Lade und parse die Datei:
   `backoffice/docs/schema/audit_schema.yaml`

2. Verwende die Dokumentation:
   `backoffice/docs/audit/AUDIT_CLAIRE_DE_BINARE_CLEANROOM.md`

3. Wende alle Regeln an:
   - Naming: intern `Claire_de_Binare`, extern „Claire de Binare“
   - Dokumenthygiene: scratch → kanonische Dokumente → Archiv
   - Keine WIP/DRAFT/TODO-Dateien im Archiv
   - Schreibweisen-Validierung (keine Formen von „Binaire“)

4. Schreibe Findings nach:
   `backoffice/docs/provenance/audit_log.md`


---------




Du arbeitest im Repository **Claire_de_Binare_Cleanroom**.

Ziel:  
Den aktuellen Repository-Stand als **neuen Nullpunkt** etablieren und alle relevanten Dokumente im Ordner `backoffice/docs/` so anpassen, dass:

1. **Namenskonventionen konsistent** sind (Claire de Binare vs. Binaire, Pfade, Service-Namen).
2. **Der Cleanroom-Stand** und die N1-Architektur als aktueller Referenzpunkt gelten.
3. **Alte Anforderungen** (Migration, Sandbox, Backup-Repo) klar als Vergangenheit/Historie markiert oder in den Archivbereich verschoben werden.
4. **Redundante oder widersprüchliche Status-Angaben** bereinigt werden (PROJECT_STATUS, MIGRATION_READY, FINAL_STATUS, EXECUTIVE_SUMMARY, PIPELINE_COMPLETE_SUMMARY etc.).

---

## 1. Kontext & Kanon

Arbeite mit folgendem logischen Modell:

- Projektname (Brand): **Claire de Binare**  
  - Schreibweise mit „Binare“ ist verbindlich.  
  - Alle Vorkommen von „Binaire“ im Sinne des Projektnamens gelten als Fehler und müssen korrigiert werden.
- Technische IDs / Namespaces / DB:
  - `claire_de_binare` ist die kanonische technische Schreibweise (z. B. DB-Name, Volumes, Container-Präfixe).

**Kanonische Referenzdokumente (höchste Priorität bei Konflikten):**

1. `backoffice/docs/KODEX – Claire de Binaire.md`  
   → Umbenennen auf `KODEX – Claire de Binare.md` und inhaltlich auf „Binare“ normalisieren.
2. `backoffice/docs/architecture/N1_ARCHITEKTUR.md`
3. `backoffice/docs/schema/canonical_schema.yaml`
4. `backoffice/docs/provenance/CANONICAL_SOURCES.yaml`
5. `backoffice/docs/provenance/EXECUTIVE_SUMMARY.md`

Bei Widersprüchen zwischen älteren Migration-/Sandbox-Dokumenten und diesen Referenzen gilt:  
**N1_ARCHITEKTUR + KODEX + canonical_schema sind führend.**

---

## 2. Scope deiner Änderungen

Arbeite in diesen Bereichen:

- `backoffice/docs/KODEX – Claire de Binaire.md`  
- `backoffice/docs/architecture/`  
- `backoffice/docs/provenance/`  
- `backoffice/docs/runbooks/`  
- `backoffice/docs/knowledge/`  
- `backoffice/docs/audit/`  
- `backoffice/docs/schema/`  
- `backoffice/docs/services/`  
- `backoffice/PROJECT_STATUS.md`

Nicht anfassen (nur lesen als Historie):

- Alles unter `archive/` im Repo-Root (`archive/backoffice_original`, `archive/docs_original`, `sandbox_backups`, `meeting_archive`, `security_audits`).
- „Roh“-Pipeline-Artefakte, die eindeutig nur Protokollcharakter haben (z. B. `input.md`, `output.md`, `extraction_log.md`, alte ADR-Quellen im Archiv).

---

## 3. Arbeitsmodus (Schritte)

### 3.1 Initiale Analyse

1. Erstelle eine kurze **Ist-Analyse** in einer eigenen Markdown-Datei:
   - Datei: `backoffice/docs/provenance/CLEANROOM_BASELINE_ANALYSIS.md`
   - Inhalte:
     - Liste aller Dateien in `backoffice/docs/`, die:
       - noch „Claire de Binaire“ im Titel oder in Überschriften tragen.
       - explizit auf „Backup-Repo“, „Kopie“ oder „Sandbox-Migration“ als zukünftigen Schritt verweisen.
       - den Cleanroom-Zustand nur als Ziel („Ziel-Repo“) statt als Ist-Zustand beschreiben.
     - Kurze Einschätzung je Datei:  
       `ROLLE = {KANON, STATUS, HISTORIE, TEMPLATE}`  
       - KANON: dauerhafte Referenz
       - STATUS: aktueller Projektstatus / Roadmap
       - HISTORIE: Beschreibung vergangener Migration
       - TEMPLATE: Wiederverwendbare Checkliste oder Script-Doku

2. Führe einen **Repo-weiten Suchlauf** nach den Strings:
   - `"Claire de Binaire"`
   - `"de Binaire"`
   - `"claire_de_binaire"` (nur zur Kontrolle der technischen IDs)
   - `"Kopie"` + `"Backup"` + `"Sandbox"`  
   Dokumentiere das Ergebnis komprimiert in derselben Analyse-Datei als Tabelle:
   - Datei
   - Kontext (1–2 Stichpunkte)
   - Handlungsbedarf: `{UMBENENNEN, INHALT_ANPASSEN, HISTORISIEREN, IGNORIEREN}`

### 3.2 Namens- und Branding-Fix

1. **Dateinamen**:
   - `backoffice/docs/KODEX – Claire de Binaire.md`  
     → umbenennen in: `backoffice/docs/KODEX – Claire de Binare.md`
   - Prüfe weitere Dateien mit „Binaire“ im Namen (z. B. in `provenance/` wie `Claire-de-Binare – Projektindex.md`) und passe sie auf „Binare“ an, wenn sie den Projektnamen meinen.

2. **Inhaltsfix**:
   - In allen KANON- und STATUS-Dokumenten:
     - Projektbezeichnung konsequent auf **„Claire de Binare“** setzen.
     - Falls sinnvoll, einen einmaligen Hinweis einbauen:  
       „Frühere Dokumente nutzen teilweise die Schreibweise ‚Claire de Binaire‘; diese gilt als historisch und wird nicht weiter verwendet.“

3. **Technische IDs NICHT anfassen**, wenn sie bereits `claire_de_binare` verwenden (DB, Volumes, Container).

### 3.3 Nullpunkt-Definition (Cleanroom als Ist-Zustand)

Für folgende Dokumente den Nullpunkt aktualisieren:

- `backoffice/docs/provenance/EXECUTIVE_SUMMARY.md`
- `backoffice/docs/provenance/PIPELINE_COMPLETE_SUMMARY.md`
- `backoffice/docs/provenance/FINAL_STATUS.md`
- `backoffice/docs/runbooks/MIGRATION_READY.md`
- `backoffice/docs/runbooks/PRE_MIGRATION_EXECUTION_REPORT.md`
- `backoffice/docs/runbooks/PRE_MIGRATION_README.md`
- `backoffice/PROJECT_STATUS.md`
- ggf. `backoffice/docs/audit/AUDIT_CLEANROOM.md` (Status/Findings-Teil)

Zielbild:

1. **Cleanroom-Repo = aktueller Kanon**  
   - Formuliere durchgängig im Präsens: Cleanroom ist bereits Zielzustand, nicht mehr „Ziel-Repo in der Zukunft“.
   - Passe ASCII-Diagramme / Flow-Charts im EXECUTIVE_SUMMARY so an, dass:
     - Backup-Repo + Sandbox als „VERGANGENE PHASE“ markiert sind.
     - Cleanroom-Repo als „AKTUELLER KANON / STARTPUNKT FÜR N1“ dargestellt wird.

2. **Next Steps umdrehen**:
   - Entferne oder entschärfe „Migration ausführen“-Instruktionen als Pflichterfordernis.
   - Ersetze die „Nächste Schritte“ in den STATUS-/RUNBOOK-Dokumenten durch:
     - Fokus auf N1 / Paper-Test-Phase (siehe `N1_ARCHITEKTUR.md`).
     - Aufbau von Tests (insbes. Risk-Manager-Coverage).
     - Infra-Hardening (SR-004, SR-005 etc.), falls noch relevant.
   - Alles, was rein die Migration von „Kopie → Cleanroom“ beschreibt, als **Historie** kennzeichnen (eigenes Kapitel „Historische Migration 2025-11“ o. Ä.).

3. **PROJECT_STATUS.md**:
   - Aktualisiere den Status so, dass:
     - Cleanroom-Repo und Kanonisierung als „DONE“ (mit Datum) geführt werden.
     - Offene Arbeitspakete mit Bezug auf N1 (Paper-Test), Tests, Infra-Hardening und evtl. Live-Anbindung gelistet werden.
   - Nutze klare Status-Tags (z. B. `DONE`, `IN_PROGRESS`, `PLANNED`).

### 3.4 Konsistenz mit N1-Architektur

1. Lies `backoffice/docs/architecture/N1_ARCHITEKTUR.md` vollständig und prüfe:
   - Scope: Paper-Test-Phase, kein unmittelbarer Live-Betrieb.
   - Modullandschaft (MDI, Strategy, Risk, Execution Simulator, Portfolio, Logging, UI).

2. Abgleich mit anderen Dokumenten:
   - In `KODEX – Claire de Binare.md`:  
     - Stelle sicher, dass das Zielbild (dockerisierte Gesamtarchitektur) im Verhältnis zu N1 sauber als „Endzustand“ bzw. „Produktionsziel“ beschrieben ist.
     - Ergänze bei Bedarf einen Abschnitt „Phasenmodell“, der N1 (Paper-Test) vs. spätere produktionsnahe Phase klar trennt.
   - In `EXECUTIVE_SUMMARY.md` und `PIPELINE_COMPLETE_SUMMARY.md`:
     - Stelle klar, dass die Kanonisierung der Doku abgeschlossen ist und N1 die nächste operative Phase darstellt.
     - Verweise explizit auf `N1_ARCHITEKTUR.md` als zentrale Referenz.

3. Ergänze (falls noch nicht vorhanden) in `CANONICAL_SOURCES.yaml`:
   - Einträge für:
     - `KODEX – Claire de Binare.md`
     - `architecture/N1_ARCHITEKTUR.md`
     - `schema/canonical_schema.yaml`
     - `provenance/EXECUTIVE_SUMMARY.md`
   - Deklariere das Cleanroom-Repo als aktuelle „canonical codebase“.

### 3.5 Decision Log / ADR

1. Öffne `backoffice/docs/DECISION_LOG.md`.
2. Prüfe, ob es bereits eine ADR gibt, die das Cleanroom-Repo als kanonische Codebasis festschreibt.
3. Falls nicht, erstelle **eine zusätzliche ADR** (z. B. ADR-039):

   - Titel: „Cleanroom-Repository als neue kanonische Codebasis“
   - Problem: Historische Trennung zwischen Backup-Repo, Sandbox und Ziel-Repo; Doku voller Migrationshinweise.
   - Entscheidung:
     - `Claire_de_Binare_Cleanroom` ist ab Datum X der einzige kanonische Code- und Dokumentenstand.
     - Migration-Dokumente werden als Historie behandelt, nicht mehr als aktive ToDos.
     - Künftige Strukturänderungen werden ausschließlich in diesem Repo vorgenommen.
   - Consequences:
     - Vereinfachtes Onboarding, klare Single Source of Truth.
     - Migration-Skripte dienen nur noch als Template für zukünftige Projekte / Migrationsfälle.

---

## 4. Qualitätsregeln für deine Änderungen

- **Keine stillen Brüche**:
  - Wenn du Aussagen änderst („Migration erforderlich“ → „Migration erledigt“), passe immer auch:
    - Einleitung
    - Status-Abschnitte
    - „Next Steps“ / Checklisten
    - Textdiagramme oder Tabellen an.
- **Historie nicht löschen**:
  - Historische Beschreibungen der Pipelines und Migrationen nicht entfernen, sondern:
    - Entweder im selben Dokument unter „Historie“ zusammenfassen.
    - Oder bei starker Redundanz in ein Archiv-Dokument unter `backoffice/docs/provenance/` zusammenführen und im ursprünglichen Dokument darauf verweisen.
- **Konsistente Sprache**:
  - Deutsch beibehalten, klar, knapp, technisch.
  - Kein Marketing-Gewäsch, keine Übertreibungen.
- **Verlinkung prüfen**:
  - Wenn du Dateinamen änderst (z. B. KODEX), alle referenzierenden Links im Repo anpassen (Markdown-Links, Erwähnungen in anderen Docs, ggf. Hinweise in README oder CLAUDE-Anleitungen).

---

## 5. Abschluss-Output

Erstelle zum Abschluss eine Übersicht in:

`backoffice/docs/provenance/CLEANROOM_BASELINE_SUMMARY.md`

Inhalte:

1. Kurze Zusammenfassung (max. 10 Bullet Points):
   - Was ist jetzt der definierte Nullpunkt?
   - Welche Dokumente bilden die aktuelle „Single Source of Truth“?
2. Tabelle „Wichtige Änderungen“:
   - Datei
   - Änderungstyp (`UMBENENNEN`, `CONTENT_UPDATE`, `STATUS_BEREINIGT`, `ADDED_ADR`)
   - 1–2 Stichpunkte zur Änderung.
3. Checkliste für zukünftige Contributors:
   - „Wenn du etwas an Architektur / Risk / Migration änderst, musst du diese Dokumente anfassen: …“

Erst wenn diese Summary konsistent ist und keine offensichtlichen Verweise mehr auf „Zukunfts-Migration in den Cleanroom“ existieren, gilt deine Aufgabe als abgeschlossen.







Hier sind die Antworten auf die offenen Fragen aus der Analyse – plus ein Block, den du direkt an Claude schicken kannst.

---

## 1) Sandbox-Ordner

**Ist-Zustand**

* Es gibt aktuell **keinen aktiven `sandbox/`-Ordner im Repo-Root**.
* Sandbox-bezogene Inhalte liegen bereits unter
  `archive/sandbox_backups/` → das ist sauber als Historie gekapselt.

**Vorgabe**

* Kein neuer `sandbox/`-Ordner anlegen.
* `archive/sandbox_backups/` bleibt genau dort, Rolle = **HISTORIE / Backups**, keine weitere Umorganisation nötig.
* In der Doku:

  * „Sandbox“ immer als **vergangene Umgebung** markieren (Backup-/Pre-Cleanroom-Kontext).
  * Keine Formulierungen mehr, die eine aktive Sandbox-Umgebung suggerieren.

---

## 2) Migration-Scripts (`.ps1`, `.sh`)

**Ist-Zustand**

* Es gibt mindestens das Script **`cleanroom_migration_script.ps1`**, referenziert in der EXECUTIVE_SUMMARY.
* Funktion: Migration vom alten Backup-Repo in das Cleanroom-Repo.

**Strategie**

* Rolle ab jetzt: **historisches, wiederverwendbares Template**, nicht mehr „jetzt ausführen, um das Repo in den Cleanroom zu migrieren“.

**Vorgabe**

* Physischer Ort bleibt: **unter `scripts/migration/`** (oder dem bestehenden Pfad).
  → Keine Verschiebung nach `backoffice/templates/`, um bestehende Pfadannahmen und mentale Modelle nicht unnötig zu brechen.
* Anpassungen:

  * Im Script-Kopf klaren Kommentar ergänzen:

    * „Dieses Script dokumentiert die Migration vom Backup-Repo in den Cleanroom-Stand (2025-11-xx) und dient heute primär als Template/Referenz.“
  * In den Migrations-Dokumenten (MIGRATION_READY, MANIFEST, EXECUTIVE_SUMMARY etc.) den Status des Scripts so formulieren:

    * „historisches Migrations-Script / Template“
    * nicht mehr „jetzt ausführen, um in den Cleanroom zu migrieren“.
* Falls zusätzliche `.ps1`/`.sh`-Migrations-Skripte existieren:

  * Gleiche Behandlung: Rolle = **HISTORIE + TEMPLATE**, Pfad bleibt unter `scripts/migration/`.

---

## 3) Alte Dateien im Root (KODEX, DECISION_LOG, etc.)

**Ist-Zustand**

* Im Repo-Root liegen aktuell keine Duplikate wie:

  * `DECISION_LOG.md`
  * `KODEX – Claire de Binaire.md`
* Die „alten“ Varianten sind bereits in den Archivstrukturen (`archive/docs_original/` usw.) geparkt.

**Vorgabe**

* Der **einzige gültige Ort** für diese Dateien bleibt:

  * `backoffice/docs/DECISION_LOG.md`
  * `backoffice/docs/KODEX – Claire de Binare.md` (nach Umbenennung)
* Policy für die Zukunft:

  * Falls solche Dateien doch im Root auftauchen (versehentlich angelegt oder reinkopiert):

    * **nicht** mehr pflegen.
    * Entweder direkt löschen oder nach `archive/docs_original/` verschieben und dort als „deprecated copy“ markieren.
  * In der Doku keine Root-Pfade mehr verwenden, sondern immer auf `backoffice/docs/...` referenzieren.

---




### Block für Claude


Update zu deinen offenen Fragen:
1) Sandbox-Ordner
- Es gibt keinen aktiven `sandbox/`-Ordner im Repo-Root.
- Sandbox-bezogene Inhalte liegen bereits unter `archive/sandbox_backups/`.
- Vorgabe: `archive/sandbox_backups/` bleibt als HISTORIE/Backup bestehen, keine weitere Umstrukturierung. In allen Docs „Sandbox“ nur noch als historische Umgebung (Pre-Cleanroom) formulieren.

2) Migration-Scripts (.ps1 / .sh)
- Es existiert mindestens `cleanroom_migration_script.ps1` (Migration vom Backup-Repo in den Cleanroom).
- Rolle ab jetzt: historisches, wiederverwendbares Template – nicht mehr als auszuführender Schritt für den aktuellen Stand.
- Vorgabe:
  - Scripts bleiben physisch im bestehenden Pfad (z. B. `scripts/migration/`), werden NICHT nach `backoffice/templates/` verschoben.
  - Im Script-Kopf klar markieren, dass es die Migration 2025-11 beschreibt und heute als Template/Referenz dient.
  - In allen Migrations-Dokumenten (MIGRATION_READY, CLEANROOM_MIGRATION_MANIFEST, EXECUTIVE_SUMMARY usw.) das Script als „historisches Migrations-Script / Template“ bezeichnen, nicht mehr als aktive Pflichtaktion.
  - Falls weitere `.ps1`/`.sh`-Migrations-Skripte existieren, gleiche Behandlung.

3) Alte Root-Dateien (KODEX, DECISION_LOG)
- Im Repo-Root sollen KEINE aktiven Fassungen von `DECISION_LOG.md` oder `KODEX – Claire de Binare.md` existieren.
- Gültige, gepflegte Versionen liegen nur unter `backoffice/docs/`.
- Vorgabe:
  - Falls Root-Duplikate existieren oder in Zukunft auftauchen: als „deprecated“ behandeln, entweder löschen oder nach `archive/docs_original/` verschieben.
  - In allen Docs ausschließlich auf die Varianten unter `backoffice/docs/` verweisen.

Bitte setze deine weiteren Änderungen unter diesen Annahmen fort.
```



Du arbeitest im Repository **Claire_de_Binare_Cleanroom** auf meinem System.

## Kontext

- Cleanroom-Nullpunkt ist definiert (ADR-039, CLEANROOM_BASELINE_* und NULLPUNKT_DEFINITION_REPORT.md).
- Der Cleanroom ist die kanonische Codebasis, `backoffice/docs/` ist Single Source of Truth.
- Es gibt drei neue Basis-Dokumente, die du benutzen sollst (nicht überschreiben, nur ergänzen/aktualisieren):

  1. `backoffice/docs/CLEANROOM_ONBOARDING_AND_REPO_NAVIGATION.md`
  2. `backoffice/docs/architecture/STRUCTURE_CLEANUP_PLAN.md`
  3. `backoffice/docs/provenance/BASELINE_COMPLETION_REPORT.md`

Falls eines dieser drei Dokumente noch nicht existiert, lege es neu an und fülle es sinnvoll gemäß Dateiname und Kontext; wenn es existiert, nutze den vorhandenen Inhalt und erweitere ihn nur.

---

## Aufgabe – Phase 1: Naming Normalization (28 Dateien)

Ziel: Alle aktiven Vorkommen von **"Claire de Binaire"** in **aktiver Doku** auf **"Claire de Binare"** bringen – mit den expliziten Ausnahmen aus der BASELINE-Logik (Archive, historisierte Listen, Pipeline-Outputs).

### 1.1 Service-Dokumentation (12 Dateien)

Gehe alle folgenden Dateien durch und ersetze **nur** in aktivem Kontext die Schreibweise:

- `backoffice/docs/services/cdb_advisor.md`  
- `backoffice/docs/services/cdb_execution.md`  
- `backoffice/docs/services/cdb_kubernetes.md`  
- `backoffice/docs/services/cdb_postgres.md`  
- `backoffice/docs/services/cdb_prometheus.md`  
- `backoffice/docs/services/cdb_redis.md`  
- `backoffice/docs/services/cdb_signal.md`  
- `backoffice/docs/services/cdb_ws.md`  
- `backoffice/docs/services/GRAFANA_DASHBOARD_GUIDE.md`  
- `backoffice/docs/services/risk/cdb_risk.md`  
- `backoffice/docs/services/risk/RISK_LOGIC.md`  
- `backoffice/docs/services/SERVICE_DATA_FLOWS.md`  

Für jede Datei:

- Ersetze Text `Claire de Binaire` → `Claire de Binare` (inkl. Titel/Headlines, sofern nicht explizit historisch).
- Achte darauf, keine historischen Zitate/Logabschnitte zu verfälschen, falls vorhanden.
- Trage anschließend in `backoffice/docs/provenance/BASELINE_COMPLETION_REPORT.md` unter **2.1 Service-Dokumentation** ein, dass die Datei erledigt ist (z. B. Häkchen + kurze Notiz).

### 1.2 Schema & Provenance (7 Dateien)

Bearbeite:

- `backoffice/docs/schema/canonical_schema.yaml`  
- `backoffice/docs/schema/canonical_model_overview.md`  
- `backoffice/docs/schema/canonical_readiness_report.md`  
- `backoffice/docs/provenance/CANONICAL_SOURCES.yaml`  
- `backoffice/docs/provenance/FINAL_STATUS.md`  
- `backoffice/docs/provenance/PIPELINE_COMPLETE_SUMMARY.md`  
- `backoffice/docs/provenance/INDEX.md`  

Vorgehen:

- Ersetze aktive Nennungen von „Claire de Binaire“ durch „Claire de Binare“, sofern es nicht bewusst als „historische Schreibweise“ markiert ist.
- Passe ggf. Beschreibungstexte so an, dass sie den Cleanroom-Nullpunkt widerspiegeln.
- Aktualisiere danach den entsprechenden Abschnitt in `BASELINE_COMPLETION_REPORT.md` (2.2).

### 1.3 Architektur & Sonstiges (4 Dateien)

Bearbeite:

- `backoffice/docs/architecture/SYSTEM_FLUSSDIAGRAMM.md`  
- `backoffice/docs/meetings/MEETINGS_SUMMARY.md`  
- `backoffice/docs/infra/repo_map.md`  
- `backoffice/docs/audit/AUDIT_PLAN.md`  

Vorgehen wie oben: aktive Verwendung angleichen, historische Referenzen unverändert lassen. Fortschritt in `BASELINE_COMPLETION_REPORT.md` Abschnitt 2.3 dokumentieren.

### 1.4 Migration Scripts (3 Dateien)

Für alle PowerShell-Skripte unter `scripts/migration/*.ps1`:

- Füge am Anfang folgenden Header ein (falls noch nicht vorhanden):

```powershell
<#
  HISTORICAL TEMPLATE - Documents 2025-11-16 migration
  Repository : Claire_de_Binare_Cleanroom
  Context    : Migration from backup repo into Cleanroom baseline
  Status     : Historical reference only (do not re-run on current baseline)
#>



-----


Kontext:

Du hast Phase 1: Naming Normalization laut deinem eigenen Report bereits abgeschlossen:

- Aktive „Binaire“-Vorkommen in 4 Dateien angepasst
- 3 Migration-Skripte als historische Templates markiert
- CLEANROOM_ONBOARDING_AND_REPO_NAVIGATION.md erstellt
- BASELINE_COMPLETION_REPORT.md um eine Phase-1-Zusammenfassung ergänzt

Ich möchte jetzt, dass du **Phase 2 (Navigation Documents)** und **Phase 3 (Verifikation)** aus meinem BASELINE-Workflow vollständig ausführst und sauber im Repo dokumentierst.

Wichtige Dateien:

- `backoffice/docs/CLEANROOM_ONBOARDING_AND_REPO_NAVIGATION.md`
- `backoffice/docs/architecture/STRUCTURE_CLEANUP_PLAN.md`
- `backoffice/docs/provenance/BASELINE_COMPLETION_REPORT.md`
- `README.md`
- `CLAUDE.md`
- `backoffice/docs/architecture/N1_ARCHITEKTUR.md`
- `backoffice/PROJECT_STATUS.md`

---

## Aufgabe – Phase 2: Navigation Documents FINALISIEREN

1. **CLEANROOM_ONBOARDING_AND_REPO_NAVIGATION.md**

   - Stelle sicher, dass der Inhalt konsistent ist mit:
     - KODEX
     - EXECUTIVE_SUMMARY
     - CLEANROOM_BASELINE_* 
     - N1_ARCHITEKTUR
   - Ergänze bei Bedarf knapp:
     - aktuellen Hinweis auf die N1-Phase,
     - kurze Erklärung, dass dieses Dokument der Startpunkt für neue Contributor und KI-Agents ist.
   - Verlinke dieses Dokument an zwei Stellen:
     - im `README.md` (kurzer Abschnitt „Onboarding / Einstieg“),
     - in `CLAUDE.md` (als zentraler Orientierungspunkt für KI-Agents).
   - Trage den Status in `backoffice/docs/provenance/BASELINE_COMPLETION_REPORT.md` unter **3.1** ein (Checkbox + 1–2 Sätze).

2. **STRUCTURE_CLEANUP_PLAN.md**

   - Stelle sicher, dass die Datei unter `backoffice/docs/architecture/STRUCTURE_CLEANUP_PLAN.md` liegt.
   - Prüfe, ob der Inhalt zur aktuellen `N1_ARCHITEKTUR.md` passt (Module, Phasen, N1-Fokus).
   - Ergänze:
     - einen sehr kurzen Verweis in `N1_ARCHITEKTUR.md` („Details zum Struktur-Refactoring siehe STRUCTURE_CLEANUP_PLAN.md“),
     - optional einen Eintrag in `PROJECT_STATUS.md` („Architecture Refactoring Plan documented“).
   - Aktualisiere in `BASELINE_COMPLETION_REPORT.md` den Abschnitt **3.2** (Checkbox + 1–2 Sätze).

Ändere bitte nichts an ADR-039 oder den Nullpunkt-Dokumenten selbst, sondern nur Verweise und ergänzende Hinweise.

---

## Aufgabe – Phase 3: Verifikation

Ziel: Sicherstellen, dass alle Änderungen konsistent sind und keine unerwünschten „Binaire“-Reste in aktiver Doku übrig sind.

1. **String-Check „Claire de Binaire“**

   - Führe eine Suche nach `"Claire de Binaire"` über `backoffice/docs/` aus, **ohne**:
     - `archive/`
     - explizit historisierte Pipeline-Outputs (`extracted_knowledge.md` usw.)
   - Liste die verbleibenden Treffer mit Pfad + Zeilennummer auf und klassifiziere:
     - „erlaubt“ = bewusst historisch / Audit-Listen,
     - „zu korrigieren“ = noch aktive Doku.
   - Korrigiere nur die „zu korrigieren“-Stellen und dokumentiere das Ergebnis in `BASELINE_COMPLETION_REPORT.md` unter **4.1**.

2. **Link-Check**

   - Prüfe in allen Dateien, die du in Phase 1 und 2 geändert hast:
     - interne Links (Markdown-Links, Pfade) auf Gültigkeit.
   - Falls du kaputte Links findest, korrigiere sie und notiere in **4.2** des BASELINE-Reports:
     - welche Dateien,
     - welche Links korrigiert wurden (kurze Stichpunkte).

3. **Archiv-Check**

   - Bestätige, dass:
     - im `archive/`-Ordner keine Dateien geändert wurden,
     - keine neuen aktiven Dokumente in `archive/` angelegt wurden.
   - Trage eine kurze Bestätigung in **4.3** von `BASELINE_COMPLETION_REPORT.md` ein.

4. **Finale Zusammenfassung in BASELINE_COMPLETION_REPORT.md**

   - Ergänze im Abschnitt **5. Ergebnis & Impact**:
     - ob Phase 2 und 3 vollständig abgeschlossen sind,
     - 2–3 Sätze mit Impact (Naming-Konsistenz, Navigation, Verifikation).
   - Falls noch Restarbeiten übrig sind, trage sie unter **6. Unresolved Items / Next Audit** ein.

---

## Output

Wenn du fertig bist, zeige mir bitte:

1. Die relevanten Auszüge aus `BASELINE_COMPLETION_REPORT.md` (Abschnitte 3, 4, 5, 6).
2. Eine tabellarische Übersicht aller verbliebenen „Binaire“-Vorkommen mit Klassifikation (erlaubt vs. aktiv korrigiert).
3. Eine kurze Liste „Welche Dateien habe ich in Phase 2 und 3 geändert?“ mit Pfad und Art der Änderung (1–2 Stichpunkte je Datei).

