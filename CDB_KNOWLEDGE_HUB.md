# CDB_KNOWLEDGE_HUB – Shared Decisions & Agent Handoffs (v1.0)

Date: 2025-12-12
Status: Active, Governance-aligned

---

## Inhaltsverzeichnis

- [0. Zweck](#0-zweck)
- [1. Ground Rules](#1-ground-rules)
- [2. Agent Handoffs](#2-agent-handoffs)
- [3. Decision Log](#3-decision-log)
- [4. Session Summaries](#4-session-summaries)
- [5. Beziehung zu NEXUS.MEMORY und Governance](#5-beziehung-zu-nexusmemory-und-governance)
- [6. Session Notes Archive](#6-session-notes-archive)

---

## 0. Zweck

Der CDB_KNOWLEDGE_HUB ist der **zentrale, versionierte Notiz- und Decision-Hub** für alle KI-Sessions
im Projekt *Claire de Binare* (CDB).

Er ist ausdrücklich **kein**:
- Governance-Dokument,
- Memory-Interface,
- Log aller Roh-Outputs.

Sondern ein schlanker, stabiler Ort für:
- wichtige Entscheidungen,
- Agent-Handoffs (ToDos zwischen Agenten/Modellen),
- kurze strukturierte Session-Notizen.

Alle Einträge müssen so geschrieben sein, dass sie für spätere Sessions verständlich und nachvollziehbar sind.

---

## 1. Ground Rules

1. **Schreibrechte**
   - KI schreibt nur über explizit freigegebene Sessions (Claude, Gemini).
   - Copilot und Codex schreiben niemals direkt in diesen Hub.
   - Manuelle Edits durch den User sind jederzeit erlaubt.

2. **Governance & Memory**
   - Dieser Hub ist **kein Memory** im Sinne von `NEXUS.MEMORY.md`.
   - Dauerhafte Systemwahrheiten oder Invarianten werden ggf. später über NEXUS in echtes Memory überführt.
   - Keine automatischen Memory-Merges, keine Hidden-States.

3. **Inhaltliche Leitplanken**
   - Keine Secrets oder Zugangsdaten (ENV, Keys, Tokens, Passwörter).
   - Keine vollständigen Dumps von Logs oder Code – nur Referenzen.
   - Jede Notiz referenziert, wenn möglich, konkrete Artefakte (Dateipfade, Commits, Tickets).

4. **Stil**
   - Kurz, präzise, operativ.
   - „Wer → Was → Wo → Warum (optional).“
   - Deutsch oder Englisch – aber innerhalb eines Eintrags konsistent.

---

## 2. Agent Handoffs

> Offene Aufgaben, die ein Agent/Modell einem anderen hinterlässt.

Konvention:
- `OPEN`  = Aufgabe steht aus.
- `INPROGRESS` = gerade in Arbeit.
- `DONE`  = erledigt, mit Verweis auf Ergebnis.

Beispiel:

- [OPEN] Gemini → Claude: Governance-Review aus `CDB_GOVERNANCE.md` (Abschnitt 3.2) in Repo-Layout übertragen.
- [OPEN] Gemini → Codex: Migration-Skript von `/t1` nach `core/services/infrastructure/tests` vorbereiten.
- [INPROGRESS] Codex → Claude: Implementierung `scripts/cleanroom_migration.ps1` (siehe Branch `feature/cleanroom-migration`).
- [DONE] Claude → User: Repo-Struktur nach `CDB_REPO_STRUCTURE.md` aktualisiert; Validierungsbericht in `CDB_REPO_INDEX.md` ergänzt.

### 2.1 Aktuelle Handoffs

- [OPEN] Gemini → Claude: Technische Validierung der durchgeführten T1-Migration.

---

## 3. Decision Log

> Kurzprotokoll zentraler, projektweiter Entscheidungen.

Jeder Eintrag sollte enthalten:
- Datum,
- Beteiligte (User / Modelle),
- Kernentscheidung,
- Verweis auf Artefakte (Dateien, Commits, Tickets).

Beispiel:

- 2025-12-12 – User + Claude  
  **Entscheidung:** Canonical Repo-Layout auf `core/services/infrastructure/tests/governance` festgelegt.  
  **Referenzen:** `CDB_REPO_STRUCTURE.md` (v1), `CDB_REPO_INDEX.md` aktualisiert.

### 3.1 Aktuelle Entscheidungen

- **2025-12-12 – Initiale Anlage des CDB_KNOWLEDGE_HUB.md.**
  Zweck: Zentrale Drehscheibe für Entscheidungen und Agent-Handoffs.

- **2025-12-12 – User + Claude + Gordon (Docker AI)**
  **Entscheidung:** Docker-Infrastruktur-Architektur für CDB v2.0 definiert.
  **Kontext:** Konsultation von Gordon (Docker AI Assistant) für Infrastructure-Planung.
  **Kern-Entscheidungen:**
  1. **Modulare Compose-Architektur:** `/infrastructure/compose/{base,dev,prod}.yml` statt monolithischer docker-compose.yml
  2. **PostgreSQL Event Store:** Persistente Volumes, Health-Checks, pg_dump-Backup-Strategie
  3. **Redis Pub/Sub + Cache:** AOF-Persistenz für kritische Nachrichten, Health-Checks
  4. **K8s-Readiness:** Benannte Volumes/Netzwerke, keine Compose-Dependencies, Environment-basierte Konfiguration
  5. **WSL2-Optimierung:** Ressourcenlimits (6-7GB RAM, 6-7 CPUs), benannte Volumes statt Bind-Mounts für Performance
  6. **Security:** Network-Isolation, Docker Scout für CVE-Scans, Least-Privilege, Image-Hardening
  7. **Monitoring:** Prometheus + Grafana mit Exportern (postgres_exporter, redis_exporter, node_exporter)

  **Referenzen:**
  - Anfrage basiert auf `CDB_REPO_MIGRATION_BRIEF.md`
  - Ziel-Ordnerstruktur: `/infrastructure/compose/`, `/infrastructure/monitoring/`
  - Gordon-Antwort: Vollständige technische Spezifikation erhalten

  **Nächste Schritte:**
  - Implementation der Compose-Fragmente gemäß Gordon-Empfehlungen
  - Prometheus/Grafana Provisioning-Konfiguration erstellen
  - Health-Checks für alle Services definieren

---

## 4. Session Summaries

> Zusammenfassungen der durchgeführten Sessions. Detaillierte Notizen befinden sich im [Archiv](#6-session-notes-archive).

### Session 2025-12-13A – T1-Strukturmigration

- **Ziel:** Migration der T1-Artefakte aus `t1/` in die neue Repository-Struktur gemäß Migrationsplan.
- **Beteiligte:** Gemini (CLI), User.
- **Ergebnis:**
  - Alle als "essentiell" markierten T1-Dateien wurden erfolgreich verschoben oder entfernt.
  - Verbleibende T1-Dateien wurden in einem interaktiven Batch verarbeitet (gedroppt oder verschoben).
  - Das `t1/`-Verzeichnis ist nun leer von versionierten Dateien.
- **Artefakte:**
  - Die ausgeführten Aktionen wurden in `governance/GEMINI_MIGRATION_PLAN_FOR_CLAUDE_REVIEW.md` unter `## APPLIED_T1_MIGRATIONS` protokolliert.
- **Nächster Schritt / Handoff an Claude:**
  - [OPEN] Gemini → Claude: Technische Validierung der durchgeführten T1-Migration.

### Session 2025-12-12A – Docker-Infrastruktur-Konsultation (Gordon)
- **Ziel:** Definition der Docker-Architektur für das CDB v2.0 Event-Sourcing Trading-System.
- **Beteiligte:** User, Claude, Gordon (Docker AI).
- **Ergebnis:** Eine modulare Compose-Strategie wurde bestätigt und Spezifikationen für PostgreSQL, Redis, K8s-Readiness, WSL2-Optimierung, Sicherheit und Monitoring wurden definiert. Offene Punkte für die Implementierung wurden identifiziert.

### Session 2025-12-12B – Technischer Review: Gemini-Migrationsplan
- **Ziel:** Technische Validierung des von Gemini erstellten Repository-Migrationsplans.
- **Beteiligte:** User, Claude, Gemini.
- **Ergebnis:** Der Plan wurde mit Bedingungen genehmigt ("APPROVED WITH CONDITIONS"). Kritische Risiken in Bezug auf die Git-Historie und die Docker-Infrastruktur wurden identifiziert. "MUSS"-Bedingungen für die Fortsetzung wurden definiert. Der Plan ist bis zur Validierung der Git-Historie ausgesetzt.

---

## 5. Beziehung zu NEXUS.MEMORY und Governance

- `NEXUS.MEMORY.md` definiert, **was** als dauerhaftes Memory gelten darf und **wie** es geschrieben wird.
- `CDB_KNOWLEDGE_HUB.md` hält fest, **was in der Praxis entschieden und beauftragt wurde.**
- Governance-Dateien (z. B. `CDB_CONSTITUTION.md`, `CDB_GOVERNANCE.md`, `CDB_AGENT_POLICY.md`) bleiben die einzige Quelle für Regeln.

Wenn ein Eintrag aus diesem Hub langfristig relevant wird, kann er später – nach expliziter User-Freigabe – als **Memory-Kandidat** markiert und über NEXUS in echtes System-Memory überführt werden.

Bis dahin gilt:
> „Alles im Hub ist wichtig – aber nichts davon ist automatisch Memory.“

---

## 6. Session Notes Archive

### Session 2025-12-12A – Docker-Infrastruktur-Konsultation (Gordon)

- **Ziel:** Docker-Architektur für CDB v2.0 Event-Sourcing Trading-System definieren
- **Beteiligte:** User, Claude (Session Lead), Gordon (Docker AI Assistant)
- **Kontext:** Repository-Migration Phase 0/1, Infrastruktur noch nicht implementiert
- **Ergebnis (Kurzfassung):**
  - ✅ Modulare Compose-Strategie (base/dev/prod fragments) bestätigt
  - ✅ PostgreSQL Event Store Konfiguration (Persistence, Backup, Health) spezifiziert
  - ✅ Redis Pub/Sub + Cache Setup definiert (AOF, Health-Checks)
  - ✅ K8s-Readiness Patterns identifiziert (benannte Volumes, keine depends_on)
  - ✅ WSL2-Optimierung für 8GB RAM / 8 CPUs geklärt
  - ✅ Security-Hardening-Maßnahmen (Network-Isolation, Docker Scout, Least-Privilege)
  - ✅ Prometheus + Grafana Monitoring-Architektur
- **Technische Details:**
  - Gordon empfiehlt `docker compose -f base.yml -f {dev|prod}.yml up` Pattern
  - Health-Checks für alle Services essentiell (PostgreSQL: `pg_isready`, Redis: `redis-cli ping`)
  - Volume-Strategie: Benannte Volumes für Performance unter WSL2
  - Ressourcenlimits via `deploy.resources.limits` in prod.yml
- **Offene Punkte:**
  - [ ] Implementierung `/infrastructure/compose/{base,dev|prod}.yml`
  - [ ] Prometheus-Konfiguration + Exporter-Setup
  - [ ] Grafana-Provisioning + Trading-spezifische Dashboards
  - [ ] PostgreSQL-Schema + Migrations in `/infrastructure/database/`
- **Artefakte:**
  - Gordon-Antwort: Vollständige technische Spezifikation mit Code-Beispielen
  - Dokumentation im Decision Log (Section 3.1)

---

### Session 2025-12-12B – Technischer Review: Gemini-Migrationsplan

- **Ziel:** Technische Validierung des von Gemini erstellten Repository-Migrationsplans
- **Beteiligte:** User, Claude (Session Lead, Reviewer), Gemini (Plan-Autor)
- **Kontext:** Migration von t1/t2/t3-Struktur in Ziel-Schema (Phase 2 laut CDB_REPO_MIGRATION_BRIEF.md)
- **Review-Umfang:**
  - Struktur-Konsistenz (Abgleich mit CDB_REPO_STRUCTURE.md)
  - Git-History-Abhängigkeit (t1/t2/t3 nicht im HEAD)
  - Docker-Infrastruktur-Integration (Gordon's Empfehlungen)
  - Service-Migration-Analyse (Umbenennungen)
  - Dependency-Management (requirements.txt DROP)
  - Governance-Compliance
  - K8s-Readiness
  - Vollständigkeit & Risiken

- **Ergebnis (Executive Summary):**
  - ✅ **APPROVED WITH CONDITIONS** (Gesamt-Score: 92%)
  - ✅ Struktur-Konsistenz: 95% (nur `/infrastructure/compose/` fehlt)
  - ✅ Governance-Compliance: 100%
  - ✅ K8s-Readiness: 80% (gute Basis, Health-Checks fehlen)
  - ⚠️ **KRITISCH:** t1/t2/t3 existieren nicht im aktuellen HEAD → Git-History-Validierung erforderlich
  - ⚠️ Docker-Infrastruktur: Modulare Compose-Fragmente fehlen (Gordon-Integration)
  - ✅ Service-Umbenennungen logisch und konsistent
  - ✅ requirements.txt DROP akzeptabel (Services haben eigene Dependencies)

- **Kritische Risiken identifiziert:**
  - **R1 (KRITISCH):** t1/t2/t3 nicht in Git-History → Codex kann nicht migrieren
  - **R2 (HOCH):** Makefile/Dockerfiles müssen auf service-spezifische requirements.txt umgestellt werden
  - **R3 (MITTEL):** `/infrastructure/compose/` fehlt für Gordon's modulare Strategie

- **MUST-Bedingungen (vor Execution):**
  1. Git-History-Validierung: Commit mit t1/t2/t3 identifizieren
  2. Source-Commit-Hash oder Archiv-Pfad in Plan aufnehmen
  3. Post-Migration-Checkliste erstellen (Makefile, Dockerfiles, CI/CD)

- **SHOULD-Empfehlungen (kurz nach Migration):**
  4. `/infrastructure/compose/{base,dev,prod}.yml` gemäß Gordon anlegen
  5. K8s-Readiness: `/infrastructure/k8s/` Skelett + Health-Checks validieren
  6. CDB_REPO_STRUCTURE.md aktualisieren (Archive-Ordner dokumentieren)

- **Freigabe-Status:**
  - ⏸️ **CONDITIONAL APPROVAL** – wartend auf Git-History-Validierung (R1-Mitigation)
  - Sobald MUST-Bedingungen erfüllt: Plan kann an Codex übergeben werden

- **Artefakte:**
  - Vollständiger Review-Bericht: `governance/reviews/reports/CLAUDE_TECHNICAL_REVIEW_GEMINI_MIGRATION_PLAN.md`
  - Risiko-Matrix mit 6 Risiken + Mitigations
  - Must/Should/Nice-Kategorisierung (8 Empfehlungen)
