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

- [DONE] Codex → Claude: P1-Tools implementiert (2025-12-14, Session 2025-12-14A)
- [OPEN] Claude → Service-Refactoring: `get_secret()` statt `os.getenv()` (P2)

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

- **2025-12-14 – User + Claude + Codex**
  **Entscheidung:** P1 Developer-Tools erfolgreich implementiert und validiert.
  **Referenzen:** `tools/cdb-stack-doctor.ps1`, `tools/cdb-service-logs.ps1`, `tools/cdb-secrets-sync.ps1`
  **Status:** Produktionsreif, alle Tests bestanden.

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

### Session 2025-12-14A – Codex P1-Tools Delivery & Validation

- **Ziel:** Validierung der von Codex implementierten P1 Developer-Tools
- **Beteiligte:** User (Jannek), Claude (Session Lead), Codex (Implementation)
- **Kontext:** Developer-Tools-Suite aus Session 2025-12-13B, Specs von Claude erstellt
- **Ergebnis:**
  - ✅ `cdb-stack-doctor.ps1` implementiert und getestet (9/9 Services healthy)
  - ✅ `cdb-service-logs.ps1` implementiert und getestet (Log-Retrieval funktional)
  - ✅ `cdb-secrets-sync.ps1` bereits vorhanden aus Session 2025-12-13B
  - ✅ Alle Tools folgen PowerShell Best Practices
  - ✅ Governance-Compliance: nur `/tools/` modifiziert
- **Technische Validierung:**
  - `cdb-stack-doctor.ps1`: Docker-Check, Compose/Secrets-Validation, Health-Status, Exit-Code-Logik ✅
  - `cdb-service-logs.ps1`: Log-Retrieval (10 Lines), Follow-Mode verfügbar, Farbcodierung ✅
- **Artefakte:**
  - `/tools/cdb-stack-doctor.ps1` (Production-ready)
  - `/tools/cdb-service-logs.ps1` (Production-ready)
  - Knowledge Hub aktualisiert
- **Handoffs:**
  - [DONE] Codex → Claude: P1-Tools erfolgreich geliefert
  - [OPEN] Claude → P2-Refactoring: Service-Level `get_secret()` Migration
- **Nächste Schritte:**
  - P2-Tools optional (cdb-event-replay, cdb-health-monitor)
  - Service-Refactoring für Secrets-Management

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

---

### Session 2025-12-13B – Docker-Diagnose & Golden Stack Boot

- **Ziel:** Docker-Instabilität beheben, reproduzierbaren Stack-Boot etablieren, P1 Developer-Tools starten
- **Beteiligte:** User (Jannek), Claude (Session Lead, Docker/Ops-Architekt)
- **Kontext:** Docker-Stack instabil (7/9 healthy), Root unaufgeräumt, Developer-Tools fehlten

**Durchgeführt:**
1. **Docker-Diagnose (P0):**
   - Root Cause: Secrets fehlten, Services ohne `get_secret()` nutzten ENV
   - Fix: `.secrets/` von `.cdb_local/` kopiert, ENV-Variablen ergänzt
   - Ergebnis: ✅ 9/9 Services healthy (cdb_paper_runner deaktiviert)

2. **Root-Cleanup:**
   - Gelöscht: `docker-compose.yml.backup`, `.pytest_cache/`
   - `.gitignore` erweitert: `.secrets/`, `.pytest_cache/`, `__pycache__/`

3. **Golden Stack Boot:**
   - Erstellt: `stack_boot.ps1` (reproduzierbar, Health-Checks, 5-Phasen-Boot)

4. **Developer-Tools (Specs + Start):**
   - 8 Tools spezifiziert (cdb-stack-doctor, cdb-secrets-sync, cdb-service-logs, etc.)
   - Implementiert: `tools/cdb-secrets-sync.ps1` (P1)

**Artefakte:**
- `stack_boot.ps1`, `tools/cdb-secrets-sync.ps1`
- Plan: `C:\Users\janne\.claude\plans\starry-skipping-pond.md`

**Handoffs:**
- [OPEN] Codex → Implementiere `cdb-stack-doctor.ps1` (P1)
- [OPEN] Codex → Implementiere `cdb-service-logs.ps1` (P1)
- [OPEN] Claude → Refactor Services: `get_secret()` statt `os.getenv()` (P2)

**Entscheidungen:**
- Golden Source: `docker-compose.yml` (Root) = Single Source of Truth
- Secrets-Flow: `.cdb_local/.secrets/` → `.secrets/` → `.env` (Workaround)

---

## NEU

Neuer Auftrag für dich als Session Lead:

Ziel:
Definiere eine kleine Suite von Developer-Tools, die Codex später für dich umsetzt, damit du smarter und schneller mit dem Repo arbeiten kannst.

Rahmen:
- OS: Windows 10
- Shell: PowerShell
- Stack: Docker Desktop, aktueller Claire-de-Binare-Stack
- Codex ist der einzige, der später den Code für diese Tools schreibt.

Bitte liefere NUR Spezifikationen, KEINEN Code.

Struktur deiner Antwort:

## TOOL OVERVIEW
Liste 5–8 Tools mit kurzem Einzeiler, z.B.:
- `cdb-stack-doctor` – schneller Health-/Log-Check für den Docker-Stack
- `cdb-scan-governance` – prüft Write-Zonen / Policy-Compliance
- usw.

## TOOL SPECS
Für jedes Tool:
- Name:
- Ziel:
- Aufruf (PowerShell-Beispiel):
- Inputs:
- Outputs (z.B. Exit-Codes, kurze Reports, JSON):
- Kontext (wann nutze ich das konkret?):
- Anforderungen an Codex (was genau gebaut werden soll, z.B. Python-Script, PowerShell, Kombination mit docker compose).

## HANDOFF AN CODEX
Kurze Liste: „Diese Specs sind ready für Codex“, inkl. Priorität (P1–P3).

Wichtig:
- Kein Code, nur klare, umsetzbare Spezifikationen.
- Fokus auf: weniger Handarbeit, reproduzierbare Checks, schnelle Statusbilder für dich.


Kontext:
- OS: Windows 10
- Shell: PowerShell 5.1+
- Stack: Docker Desktop, docker-compose.yml im Repo-Root
- Ich habe von Claude Spezifikationen für mehrere Tools bekommen (siehe CDB_KNOWLEDGE_HUB.md / letzten Run).

Ziel:
Implementiere ZUERST die P1-Tools als PowerShell-Skripte im Ordner `tools/`:

1. cdb-secrets-sync.ps1
2. cdb-stack-doctor.ps1
3. cdb-service-logs.ps1

Vorgaben:
- Halte dich so nah wie möglich an die Spezifikationen von Claude
  (Name, Ziel, Aufruf, Inputs, Outputs, Verhalten).
- Reine PowerShell, keine zusätzlichen Abhängigkeiten.
- Scripts sollen im Ordner `tools/` liegen (anlegen falls nicht existiert).
- Sauberes Error-Handling (Exit-Codes wie beschrieben).
- Hilfetext mit `.SYNOPSIS` / `.DESCRIPTION` / `.EXAMPLE`.

Bitte:
1. Lege/aktualisiere die drei `.ps1`-Dateien.
2. Zeig mir danach den vollständigen Inhalt aller drei Dateien,
   damit ich sie kontrollieren und commiten kann.
3. Nimm KEINE Änderungen an Governance/Policies vor, nur im `tools/`-Bereich + ggf. .gitignore-Eintrag für `tools/*.log` o.Ä., falls sinnvoll.


- [OPEN] Copilot → Claude: P2 get_secret() Migration – Analyse & Plan (Security)

  Kontext:
  Copilot hat Repo-Scan durchgeführt und direkte os.getenv() Secret-Reads identifiziert.
  Ziel: Migration auf core/domain/secrets.py:get_secret() + Reduktion von Duplicate-Secrets-Implementierungen.

  MUST (sicherheitskritisch – direkt umsetzen)
  1) services/execution/config.py
     - MEXC_API_KEY + MEXC_API_SECRET → get_secret()
     - REDIS_PASSWORD → get_secret()
     - POSTGRES_PASSWORD → get_secret()
     - Import: from core.domain.secrets import get_secret

  2) tools/paper_trading/service.py
     - REDIS_PASSWORD → get_secret("redis_password", "REDIS_PASSWORD")
     - POSTGRES_PASSWORD → get_secret("postgres_password", "POSTGRES_PASSWORD", default="")

  3) tools/paper_trading/email_alerter.py
     - ALERT_EMAIL_PASSWORD → get_secret("alert_email_password", "ALERT_EMAIL_PASSWORD")

  SHOULD (Konsistenz & Wartbarkeit)
  - 4 Duplikate von core/domain/secrets.py existieren in service-spezifischen Pfaden:
    - services/db_writer/core/domain/secrets.py
    - services/execution/core/domain/secrets.py
    - services/risk/core/domain/secrets.py
    - services/signal/core/domain/secrets.py
  - Empfehlung: auf canonical core/domain/secrets.py konsolidieren, aber erst Import-/Container-Pfade validieren.

  NICE
  - Unit-Tests für get_secret(): secrets-path, ENV-fallback, default-handling
  - Optional: Logging bei ENV-fallback (Debug/Prod Transparency)

  Offene Prüfpunkte für Claude
  - Läuft jeder Service in eigenem Container mit eigenem Build-Kontext?
  - Ist core/ als Python-Package erreichbar (PYTHONPATH/packaging)?
  - Entscheidung: infra/scripts ebenfalls migrieren oder als Host-Skripte belassen?

  - [OPEN] Copilot → Claude: P2 get_secret() Migration + Duplicate-Core Fix (LOW RISK, HIGH VALUE)

  Finding (Root Cause):
  Service-lokale `services/<svc>/core/` Duplikate überschreiben beim Docker-Build den kanonischen Repo-Root `/core`:
  - COPY core /app/core
  - COPY services/<svc>/ /app   → überschreibt /app/core mit service-lokalem core/

  MUST (Fix now)
  1) Entferne service-lokale core-Duplikate (Overshadowing Fix):
     - services/execution/core/domain/secrets.py
     - services/risk/core/domain/secrets.py
     - services/signal/core/domain/secrets.py
     - services/db_writer/core/domain/secrets.py
     (ggf. kompletten Ordner services/<svc>/core/ löschen, falls nur Duplikat-Inhalt)

  2) Migriere direkte Credential os.getenv() Reads auf get_secret():
     - services/execution/config.py: MEXC_API_KEY, MEXC_API_SECRET, REDIS_PASSWORD, POSTGRES_PASSWORD
     - tools/paper_trading/service.py: REDIS_PASSWORD, POSTGRES_PASSWORD
     - tools/paper_trading/email_alerter.py: ALERT_EMAIL_PASSWORD
     Import: from core.domain.secrets import get_secret

  SHOULD (Verification)
  - docker compose up --build
  - Smoke: keine ImportErrors, Services starten, Config lädt

  NICE (Prevent Recurrence)
  - CI-Check/Repo-Guard: blockiert jede neue `services/**/core/**` Struktur (oder explizit `services/**/core/domain/secrets.py`)

- [OPEN] Copilot → Claude: Hygiene & Quality Pack (A2/B1/B2/C1 + Quick D1/D2) — 2025-12-14

  Kontext:
  Copilot hat mehrere governance-safe Analyseblöcke durchgeführt (keine Writes/Commits).
  Ziel: Claude bekommt klar geschnittene PR-Kandidaten + vorbereitende Test-/CI-Artefakte.

  A2 — Logging-Leak-Check (Status: GRÜN)
  - Ergebnis: Keine direkten Secret-Leaks gefunden.
  - Hinweis: Ein Log in services/db_writer/db_writer.py loggt nur boolean ("Redis password loaded: Yes/No") → akzeptabel.
  - Präventive Patterns (optional):
    - mask_secret(value), allowlist logging, sanitize_for_debug()

  B1 — CI-Guard gegen service-lokale core/ Duplikate (DELIVERY-READY)
  - Script-Vorschlag: scripts/check_core_duplicates.py
  - Prüft/failt bei:
    - services/*/core/domain/**
    - services/*/core/utils/**
    - services/*/core/config/**
    - zusätzliche secrets.py außerhalb canonical core/domain/secrets.py
  - GH Actions Snippet vorhanden.

  B2 — Dead-Files & Leichen (konservativ)
  MUST (safe deletes):
  - services/signal/models.py.backup (Backup im Repo → raus, via Git-History abgedeckt)
  - tests/unit/test_smoke_repo.py.skip (referenziert alte Struktur src/backoffice)
  - Duplikat-Struktur-Teile im Rahmen der core-Duplikat-Elimination:
    - services/*/core/**/__init__.py (wenn services/*/core/ gelöscht wird)
  SHOULD (Review, nicht blind löschen):
  - core/__init__.py: NICHT als safe delete behandeln (Package-Erkennung); erst nach Testlauf entscheiden.
  - services/db_writer/__init__.py, services/signal/__init__.py: Review (Metadaten/Packaging)
  - tests/integration/, tests/replay/: leer → entweder .gitkeep oder bewusst entfernen
  - Makefile: Pfade backoffice/scripts/* sind ungültig → müssen auf infrastructure/scripts/* zeigen (Bugfix)

  C1 — Unit-Test-Skeletons (5 Dateien, 19 Tests + pytest.ini Vorschlag)
  - tests/unit/services/test_execution_imports.py
  - tests/unit/services/test_risk_imports.py
  - tests/unit/services/test_signal_imports.py
  - tests/unit/services/test_config_loading.py (ENV monkeypatch)
  - tests/unit/core/test_secrets.py (get_secret docker-secrets + env fallback + defaults)
  Hinweis:
  - Importpfade ggf. an reale Package-Struktur anpassen (Skeleton only).
  - pytest.ini Marker Vorschlag (unit/integration/e2e/slow) optional.

  D1 — Makefile Quick-Check (Bug + Targets)
  - Bug: Targets referenzieren backoffice/scripts/* → korrigieren auf infrastructure/scripts/*
  - Targets fehlen: build (MUST), lint/format/smoke (SHOULD), type-check (NICE)

  D2 — Compose Quick-Check (Dev vs Prod Risiko)
  - HIGH: Bind-Mounts ./services/* → /app sind für Prod riskant (shadowing / source-of-truth)
  - CONFLICT: read_only + bind-mount in dev (dev sollte i.d.R. read_only=false)
  - MED: Ports 8000-8003 in Prod besser intern / Reverse Proxy
  - Redis/Postgres secret-file patterns wirken korrekt.

  Empfohlene PR-Schnitte (Claude)
  PR1 (MUST): CI-Guard (B1)
  PR2 (MUST): Safe deletes (models.py.backup, smoke_repo.py.skip) + .gitignore optional (*.backup)
  PR3 (MUST/SHOULD): Makefile Pfad-Bugfix (backoffice → infrastructure)
  PR4 (SHOULD): Unit-Test-Skeletons einchecken + minimaler CI unit-run
  PR5 (SHOULD): Compose dev/prod split (wenn gewünscht, separater Track)

  Offene Entscheidungen für Claude
  - CI Zielsystem: GitHub Actions vs GitLab CI (aktuell Snippet für GH Actions vorhanden)
  - Test-Importpfade finalisieren (abhängig von Packaging/PYTHONPATH)
  - Compose-Strategie: dev/prod split jetzt oder später (kein Blocker)

- [OPEN] Copilot → Claude: C2 Replay-Test-Checkliste (Blueprint + Risiken) — 2025-12-14

  Kontext:
  Ziel ist ein deterministischer Replay-Test (Event-Aufzeichnung → Wiedereinspielung → identische Outputs).
  Copilot hat Event-Flows, Redis Topics, DB-Sinks und Determinismus-Killer identifiziert.

  Event-/Message Pipeline (4-stufig)
  - Signal → Order → OrderResult → Persistence (DBWriter/Execution DB)

  Redis Topics (Pub/Sub)
  - market_events: Producer unklar/extern → Consumer: Signal (MarketData)
  - signals: Producer Signal → Consumer Risk (Signal)
  - orders: Producer Risk → Consumer Execution (Order)
  - order_results: Producer Execution → Consumer Risk + DBWriter (OrderResult)
  - alerts: Producer Risk → Consumer DBWriter (Alert, implizit)
  - portfolio_snapshots: Producer nicht gefunden → Consumer DBWriter (PortfolioSnapshot)

  Event-Inventar (Auszug; Payload nur Feldnamen)
  - Signal (services/signal/service.py publish_signal): symbol, side, confidence, reason, timestamp, price, pct_change, type → Redis signals
  - Order (services/risk/service.py send_order): symbol, side, quantity, stop_loss_pct, signal_id, reason, timestamp, client_id, type → Redis orders
  - Alert (services/risk/service.py send_alert): level, code, message, context, timestamp → Redis alerts
  - OrderResult (services/execution/service.py process_order): order_id, status, symbol, side, quantity, filled_quantity, timestamp, price, client_id, error_message, type → Redis order_results
  - DB Persistence (services/db_writer/*): signals/orders/trades/portfolio_snapshots → PostgreSQL tables

  Determinismus-Risiken (kritischer Pfad)
  HIGH:
  - time.time()/int(time.time()) timestamps in signal/risk/execution/core models
  - random.* und uuid.uuid4() in execution/mock_executor.py (Latency/Success/Slippage/Order IDs)
  MED:
  - datetime.now().isoformat() (Stats timestamps)
  External nondeterminism:
  - Redis Pub/Sub timing/order (Medium) → record+replay statt live
  - Market data extern (High) → record raw market events

  Replay-Test-Blueprint (ohne Code, aber umsetzungsfähig)
  Phase 1 Recording (Prereq)
  - Fixture: tests/replay/fixtures/market_events_<date>.jsonl
  - Baseline State: Postgres dump + Redis baseline

  Phase 2 Replay Execution (Run)
  - Clean state: docker compose up -d; Postgres restore; Redis FLUSHALL
  - Replay overrides (ENV): REPLAY_MODE=true; REPLAY_CLOCK_START=<unix>; REPLAY_RANDOM_SEED=42
  - Inject events: stream JSONL → Redis market_events (playback rate configurable)
  - Collect artifacts: pg_export (signals/orders/trades/portfolio_snapshots) + docker logs

  Phase 3 Assertions (Invariants)
  - Counts (signals/orders/trades)
  - Risk rejections deterministisch
  - Order IDs + timestamps identisch zwischen Run1 vs Run2
  - Diff validation: dump Run1 vs Run2 → diff must be identical

  Phase 4 Cleanup
  - docker compose down; archive results

  Claude-Umsetzung (Must/Should/Nice)
  MUST
  - Clock Injection (statt time.time): zentraler Clock/Now-Provider (replay aware)
  - Random seed control (MockExecutor) via REPLAY_RANDOM_SEED
  - Deterministic UUID/OrderID im Replay-Mode (counter-based o.Ä.)
  - Recording Tool (TODO Implement): record Redis topic → JSONL
  - Playback Tool (TODO Implement): JSONL → Redis topic

  SHOULD
  - DB snapshot tooling (pg_dump/pg_restore wrapper, ggf. PowerShell)
  - verify_replay.py (PASS/FAIL + diff report)
  - .env.replay + compose --env-file

  NICE
  - Makefile target test-replay
  - Nightly replay in CI (fixture-based)
  - Replay metrics dashboard

  Pipeline-Schnitt
  - Minimal: Signal + Risk + Execution (Output: orders/trades)
  - Full: + DBWriter (+Market optional/ersetzt durch recorded events)

---

- [OPEN] Copilot → Claude: D3 Compose-Härtung (Dev/Prod Split + Risk Map) — 2025-12-14

  Kontext:
  Ziel ist ein prod-sicheres Compose-Base + Dev Overrides, um Bind-Mount/Ports/Hardening sauber zu trennen.

  Current State (Highlights)
  - DEV-Bind-Mounts: ./services/*:/app bei signal/risk/execution/db_writer (shadowing Image)
  - read_only=true aktiv bei ws/core/risk/execution (Konflikte mit Bind-Mounts + Logs)
  - Ports aktuell offen: 8000-8004, 5432, 6379, 3000, 19090
  - Secrets: Redis/Postgres/Grafana via Docker Secrets vorhanden (✅)

  Risiko-Map (Top Findings)
  HIGH (DEV):
  - Bind-Mounts überschreiben Image / Source-of-Truth unklar (ok für dev, toxisch für prod)
  - read_only=true + Bind-Mounts/Logs → Schreibkonflikte (Crash-Risiko)
  MED (PROD):
  - Service-Ports + Redis/Postgres Ports offen (Surface Area)
  - db_writer & paper_runner ohne Hardening im Vergleich zu anderen
  LOW:
  - Prometheus/Grafana Bind-Mounts (Config Drift / Missing file risk)

  Option A (empfohlen, ohne Entscheidung):
  - docker-compose.yml = Base (prod-safe defaults: keine ports, keine bind-mounts)
  - docker-compose.dev.yml = Dev overrides (ports + bind-mounts + read_only=false)
  - docker-compose.prod.yml = Prod hardening (minimal exposure, hardening flags)

  MUST (Claude Umsetzungsvorschlag)
  - Base: Ports entfernen (nur dev.yml exposen)
  - Base: Bind-Mounts entfernen (nur dev.yml bind-mount)
  - Dev: read_only=false für services mit bind-mount (ws/core/risk/execution)
  - Prod: db_writer + paper_runner hardening angleichen (read_only/tmpfs/cap_drop/no-new-privileges)
  - Prod: Ports nur über bewusstes Entry (ggf. später Reverse Proxy)

  SHOULD / NICE
  - Healthcheck/depends_on auf service_healthy (stabiler Boot)
  - Makefile Targets dev-up/prod-up
  - CI-Compose validation/lint

  Offene Entscheidungen (Claude)
  - Network isolation: internal Netz vs egress (Prod benötigt ggf. outbound APIs → nicht blind internal:true für alles)
  - Reverse Proxy: welche Endpoints müssen extern erreichbar sein (Grafana only vs APIs)
  - Resource limits: compose limits vs swarm deploy (Umsetzung abhängig von Run-Mode)

---

Claude Tasklist – Delivery Plan (CDB)
Ziel

Stabile, sichere Basis schaffen ohne Architektur-Neubau.
Reihenfolge ist bewusst gewählt: früher Value, wenig Risiko, klare Stopps.

PR-01 — CI-Guard: Service-lokale Core-Duplikate verhindern (MUST)

Input: B1
Warum zuerst: Verhindert sofort zukünftigen Schaden.

Tasks

scripts/check_core_duplicates.py anlegen

CI einhängen (GitHub Actions oder GitLab CI)

Fail bei:

services/*/core/**

zusätzlichen secrets.py

Akzeptanz

CI schlägt fehl bei absichtlichem Duplikat

CI grün im aktuellen Repo

Stop wenn

CI greift fälschlich auf erlaubte Pfade zu

PR-02 — Safe Deletes & Repo-Hygiene (MUST)

Input: B2
Warum: Risikoarm, reduziert Noise.

Tasks

Löschen:

services/signal/models.py.backup

tests/unit/test_smoke_repo.py.skip

KEIN Löschen von core/__init__.py (bewusst behalten)

Akzeptanz

Repo läuft unverändert

Keine Importfehler

Stop wenn

Unerwartete Imports brechen

PR-03 — Makefile Bugfix (Pfadkorrektur) (MUST)

Input: B2 / D1
Warum: Aktuell broken, low effort fix.

Tasks

backoffice/scripts/* → infrastructure/scripts/*

Nur Pfade fixen, keine neuen Targets

Akzeptanz

Makefile-Targets laufen wieder

Keine neuen Abhängigkeiten

PR-04 — Unit-Test-Skeletons + Import-Stabilisierung (SHOULD)

Input: C1 + C1.5
Warum: Basis-Absicherung, aber mit Import-Realismus.

Tasks

Test-Skeletons anlegen (5 Dateien)

Import-Strategie festlegen:

Entweder conftest.py (sys.path)

Oder Tests klar als „Host-only“ dokumentieren

test_secrets.py vollständig aktiv

Akzeptanz

pytest tests/unit läuft lokal grün

Keine echten Secrets nötig

Stop wenn

Imports nur mit Hacks funktionieren

Container-/Host-Kontext vermischt wird

PR-05 — Compose Base/Dev Split (Härtung light) (SHOULD)

Input: D3
Warum: Größter Stabilitätsgewinn ohne Funktionsänderung.

Tasks

Base (docker-compose.yml)

keine Ports

keine Bind-Mounts

Dev Override (docker-compose.dev.yml)

Bind-Mounts erlaubt

read_only: false wo nötig

Ports offen

db_writer & paper_runner security angleichen

Akzeptanz

Dev: Live-Reload funktioniert

Base/Prod: kein Bind-Mount, minimale Exposure

Stop wenn

Externe APIs nicht mehr erreichbar sind (Network-Thema → Entscheidung nötig)

PR-06 — Replay-Vorbereitung (Determinismus-Hooks) (SHOULD, isoliert)

Input: C2
Warum: Strategischer Hebel, aber sauber kapseln.

Tasks

Clock-Abstraktion (zentral, replay-fähig)

Random-Seed + deterministische UUID im MockExecutor

KEIN vollständiger Replay-Runner (nur Enabler)

Akzeptanz

Normalbetrieb unverändert

Replay-Mode via ENV aktivierbar

Stop wenn

Business-Logik angefasst werden muss

PR-07 — Logging-Hygiene (optional) (NICE)

Input: A2
Warum: Prävention, kein Blocker.

Tasks

mask_secret() Helper

Optional sanitize_for_debug()

KEINE Refactors bestehender Logs nötig

Entscheidungs-Backlog (nicht blockierend)

Reverse Proxy (Nginx): welche APIs extern?

Network Isolation: internes Netz vs egress

Replay-CI (nightly vs manuell)

Meta-Regel für Claude

Kein PR > 300 LOC ohne Rückfrage

Ein PR = ein Thema

Wenn Unsicherheit → stoppen und fragen

---

Claude – Abnahme-Checkliste pro PR

Allgemein:
- Scope eingehalten? (Ja/Nein)
- Keine Architektur-Änderung? (Ja/Nein)
- LOC < 300? (Ja/Nein)
- Tests/CI grün? (Ja/Nein)

PR-01 (CI-Guard):
- Greift Regel korrekt?
- Keine False Positives?
- CI verständliche Fehlermeldung?

PR-02 (Deletes):
- Keine Imports gebrochen?
- Nur vereinbarte Files gelöscht?

PR-03 (Makefile):
- Pfade korrekt?
- Keine neuen Targets?

PR-04 (Tests):
- pytest lokal grün?
- Keine Secrets nötig?
- Import-Strategie konsistent?

PR-05 (Compose):
- Base ohne Bind-Mounts?
- Dev mit Live-Reload?
- Keine Port-Exposure in Base?

Entscheidung:
- GO
- GO WITH FIX (konkret benennen)
- NO-GO (Begründung, 1 Satz)

---

# Claude Delegationsanweisung – Multi-Agent Execution Mode

## Zweck
Diese Anweisung definiert, **wann und wie Claude Aufgaben delegiert**, um:
- Nutzungslimits einzuhalten,
- Durchsatz zu maximieren,
- Governance-Risiken zu minimieren,
- operative Arbeit effizient auszulagern.

Claude agiert primär als **Orchestrator & Entscheider**, nicht als Vollstrecker.

---

## Rollenmodell (verbindlich)

### Claude (Lead / Orchestrator)
- Trifft Architektur-, Governance- und Freigabeentscheidungen
- Zerlegt Arbeit in delegierbare Tasks
- Konsolidiert Ergebnisse
- Entscheidet FINAL (Merge / Reject / Rework)

Claude **implementiert nicht**, wenn Delegation möglich ist.

---

### Copilot (Executor)
**Zuständig für:**
- Konkrete Code-Arbeit
- Scans, Audits, Skeletons, CI-Skripte
- Kleine, klar abgegrenzte PRs

**Regeln für Copilot:**
- Keine Architekturentscheidungen
- Kein Schreiben ins Knowledge Hub
- Kein Refactoring ohne expliziten Auftrag
- Output: Code, Tabellen, Snippets

Copilot arbeitet **immer task-listenbasiert** (Ultrakurzform).

---

### Gemini (Reviewer / Auditor)
**Zuständig für:**
- Reviews
- Konsistenz-Checks
- Risiko-Markierungen
- Governance-Abgleich

**Regeln für Gemini:**
- Keine neuen Vorschläge außerhalb des Scopes
- Kein Redesign
- Keine Implementierung
- Kein Schreiben von Code

Gemini arbeitet **ausschließlich mit Review-Checklisten**.

---

## Delegationsregeln (MUST)

Claude **MUSS delegieren**, wenn mindestens eines zutrifft:

- Task ist operativ / repetitiv
- Task erzeugt >20 Zeilen Code
- Task ist Scan, Audit, Liste, Skeleton
- Task kann in ≤1 PR isoliert werden
- Claude-Kontingent >70 % genutzt

---

## Standard-Delegationspfade

### Pfad A – Umsetzung
1. Claude definiert Scope + Akzeptanzkriterien
2. Claude erstellt **Copilot-Tasklist (5–10 Punkte)**
3. Copilot liefert PR-fähiges Ergebnis
4. Claude prüft & entscheidet

---

### Pfad B – Review
1. Claude definiert Review-Ziel
2. Claude verweist auf **Gemini-Review-Checkliste**
3. Gemini liefert Findings (MUST / SHOULD / NICE)
4. Claude entscheidet über Umsetzung oder Ablehnung

---

## Output-Formate (verbindlich)

### Copilot liefert:
- Tabellen
- Code-Snippets
- PR-Tasks
- Audit-Listen

### Gemini liefert:
- Review-Tabellen
- Risiko-Einstufungen
- Konsistenz-Markierungen
- Keine Lösungsdesigns

---

## Eskalationsregel

Claude **zieht keinen Agenten zurück**, um Zeit zu sparen.  
Delegation hat Vorrang vor Eigenarbeit.

Nur Claude darf:
- zusammenführen
- priorisieren
- verwerfen
- final freigeben

---

## Zielzustand

- Claude = Steuerungsebene
- Copilot = Produktionsmaschine
- Gemini = Qualitätssicherung

Kontingent wird geschont, System bleibt kontrollierbar.

**Diese Anweisung ist verbindlich.**
---

# Claude Delegationsanweisung – Multi-Agent Execution Mode

## Zweck
Diese Anweisung regelt verbindlich, **wie Claude Aufgaben delegiert**, um:
- Kontingente effizient zu nutzen,
- Durchsatz zu maximieren,
- Governance-Risiken zu minimieren,
- operative Arbeit konsequent auszulagern.

Claude agiert primär als **Orchestrator & Entscheider**, nicht als Umsetzer.

---

## Rollenmodell (verbindlich)

### Claude — Lead / Orchestrator
**Aufgaben**
- Architektur-, Governance- und Freigabeentscheidungen
- Zerlegung von Arbeit in delegierbare Pakete
- Priorisierung und Abnahme
- Finale Entscheidung: GO / GO WITH FIX / NO-GO

**Regel**
Claude implementiert **keinen umfangreichen Code**, wenn Delegation möglich ist.

---

### Copilot — Executor (Implementierung)
**Zuständig für**
- Konkrete Code-Änderungen
- CI-Skripte, Compose-Dateien
- Tests, Skeletons, Refactorings im definierten Scope
- Umsetzung klar abgegrenzter PRs

**Regeln**
- Keine Architektur- oder Governance-Entscheidungen
- Kein Schreiben ins Knowledge Hub
- Keine eigenständige Scope-Erweiterung
- Output: Code, Diffs, Tabellen, Snippets

Copilot arbeitet **ausschließlich tasklistenbasiert** (ultrakurz, PR-fokussiert).

---

### Codex — Executor (Code-nah, analytisch)
**Zuständig für**
- Code-Analysen
- gezielte Refactor-Vorschläge
- Performance- oder Struktur-Verbesserungen
- Alternativ-Implementierungen innerhalb eines vorgegebenen Rahmens

**Regeln**
- Keine Produkt- oder Architekturentscheidungen
- Kein Schreiben ins Knowledge Hub
- Liefert **Vorschläge oder umsetzbaren Code**, aber merged nichts

Codex wird eingesetzt, wenn **tieferes Code-Verständnis** oder **Variantenvergleich** nötig ist.

---

### Gemini — Reviewer / Auditor
**Zuständig für**
- Reviews
- Konsistenz- und Risiko-Checks
- Governance-Abgleich
- Zweitmeinungen

**Regeln**
- Kein Redesign
- Keine Implementierung
- Kein Schreiben von Code
- Keine Scope-Erweiterung

Gemini arbeitet **ausschließlich mit Review-Checklisten**.

---

## Delegationsregeln (MUST)

Claude **MUSS delegieren**, wenn mindestens eines zutrifft:

- Task ist operativ oder repetitiv
- Task erzeugt >20 Zeilen Code
- Task ist Scan, Audit, Liste, Skeleton
- Task kann in ≤1 PR isoliert werden
- Claude-Kontingent >70 %

---

## Standard-Delegationspfade

### Pfad A — Umsetzung (Copilot / Codex)
1. Claude definiert Scope + Akzeptanzkriterien
2. Claude erstellt eine **ultraknappe Tasklist**
3. Claude weist zu:
   - **Copilot**, wenn Umsetzung direkt klar ist
   - **Codex**, wenn Analyse / Varianten nötig sind
4. Executor liefert Ergebnis
5. Claude entscheidet final

---

### Pfad B — Review (Gemini)
1. Claude definiert Review-Ziel
2. Claude verweist auf Review-Checkliste
3. Gemini liefert Findings (MUST / SHOULD / NICE)
4. Claude entscheidet über Umsetzung oder Ablehnung

---

## Output-Formate (verbindlich)

### Copilot / Codex liefern:
- Code
- Diffs / Snippets
- Tabellen
- Kurzbegründungen

### Gemini liefert:
- Review-Summary
- Risiko-Einstufung
- Abweichungen von Policies

---

## Eskalationsregel

Claude zieht **keinen Executor zurück**, um Zeit zu sparen.  
Delegation hat Vorrang vor Eigenarbeit.

Nur Claude darf:
- zusammenführen
- priorisieren
- verwerfen
- final freigeben

---

## Zielzustand

- Claude = Steuerungsebene
- Copilot & Codex = Produktions-Layer
- Gemini = Qualitätssicherung

Kontingente bleiben stabil, Delivery bleibt kontrolliert.

**Diese Anweisung ist verbindlich.**

---


## Bitte anlegen:
COPILOT_TASKLIST.md liegt im root.

/knowledge/
  ├── OPERATING_RULES/
  │     └── CLAUDE_DELEGATION_POLICY.md   ← diese Datei
  ├── TASKLISTS/
  │     └── COPILOT_TASKLIST.md
  └── REVIEW_CHECKLISTS/
        └── GEMINI_REVIEW_CHECKLIST.md
