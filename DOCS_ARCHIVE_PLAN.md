# Archivierungsplan: Working Repo → Docs Hub
## Date: 2025-12-27
## Purpose: Restrukturierung von 14 Dokumentationsdateien aus dem Working Repo für Docs Hub Archivierung

---

## Executive Summary

**Ziel:** Migration von 14 Working Repo Dokumentationsdateien in die kanonische Docs Hub Struktur.

**Kategorien:** Session Reports (3), Audit Reports (3), Planning (2), Analysis (4), Runbooks (1), Agent Definitions (1)

**Zeitraum:** Alle Dateien aus Dezember 2025 (24.-27.12.2025)

**Docs Hub Zielstruktur:**
- `logs/sessions/` - Session Reports
- `knowledge/reviews/` - Audit Reports
- `knowledge/roadmap/` - Planning Dokumente
- `knowledge/audits/` - Analysen und Statusreports
- `_legacy_quarantine/` - Veraltete/ersetzte Dokumente
- `agents/` - Agent Definitions (kanonisch)

---

## Kategorie 1: Session Reports (3 Dateien)

### 1.1 AUTONOMOUS_EXECUTION_SUMMARY.md

**Kategorie:** Session Report
**Datum:** 2025-12-24
**Größe:** 8.3 KB

**Archivziel:** `logs/sessions/2025-12-24_autonomous_execution_summary.md`

**Begründung:** Dokumentiert autonome Session-Ausführung mit 8 Commits und vollständiger A-G Criteria Compliance; gehört zu Session-basierten Logs, nicht zu permanenter Knowledge Base.

**Referenz:** Ergebnisse sind in DOCKER_STACK_RUNBOOK.md und COMPOSE_LAYERS.md kanonisch erfasst.

---

### 1.2 AUTONOMOUS_WORK_COMPLETE_2025-12-24.md

**Kategorie:** Session Report
**Datum:** 2025-12-24
**Größe:** 16.9 KB

**Archivziel:** `logs/sessions/2025-12-24_autonomous_work_complete.md`

**Begründung:** Umfassender Session-Report (Phase 1-3) mit Commit-Historie und Infrastruktur-Updates; zeitgebundene Arbeitsprotokollierung ohne kanonischen Wissenswert.

**Referenz:** Technische Inhalte (stack_doctor.ps1, rollback.yml) sind in DOCKER_STACK_RUNBOOK.md dokumentiert.

---

### 1.3 FINAL_STATUS_2025-12-24.md

**Kategorie:** Session Report
**Datum:** 2025-12-24
**Größe:** 10.6 KB

**Archivziel:** `logs/sessions/2025-12-24_final_status.md`

**Begründung:** Session-Abschluss-Report mit Code-Fixes (MarketData, Port-Mappings, Dockerfiles); dokumentiert Blocker-Auflösung ohne dauerhafte Relevanz.

**Referenz:** Port-Mapping-Konfiguration kanonisch in `infrastructure/compose/dev.yml`, Dockerfile-Fixes in Repos.

---

## Kategorie 2: Audit Reports (3 Dateien)

### 2.1 DOCKER_HARDENING_REPORT.md

**Kategorie:** Audit Report (Security)
**Datum:** 2025-12-27
**Größe:** 18.0 KB

**Archivziel:** `knowledge/reviews/2025-12-27_docker_hardening_audit.md`

**Begründung:** Umfassender Security Audit (10 Dockerfiles, 13 Compose-Files) mit konkreten Findings (SHA256-Pinning, Root-User, CVE-Mitigations); gehört zu Reviews als permanente Wissensbasis.

**Referenz:** Nachfolge-Audits sollten auf diesen Baseline referenzieren; Issue #122 verlinkt.

---

### 2.2 HARDENING_VERIFICATION.md

**Kategorie:** Audit Report (Compliance)
**Datum:** 2025-12-24
**Größe:** 21.3 KB

**Archivziel:** `knowledge/reviews/2025-12-24_hardening_verification_a-g_criteria.md`

**Begründung:** Verifikations-Audit für A-G Acceptance Criteria (Rollback, Network Isolation, Log Aggregation); dokumentiert Compliance-Status mit Testanweisungen.

**Referenz:** Kanonische Runbook-Inhalte migriert nach DOCKER_STACK_RUNBOOK.md, Audit bleibt als historischer Nachweis.

---

### 2.3 Docker Container & Image Vulnerability Scan Report.md

**Kategorie:** Audit Report (Security)
**Datum:** 2025-12-23
**Größe:** 11.1 KB

**Archivziel:** `knowledge/reviews/2025-12-23_vulnerability_scan_docker_scout.md`

**Begründung:** Docker Scout Scan-Report (9 Images, CVE-Details, Risk-Assessment); gehört zu Security Reviews als Baseline für Folge-Scans.

**Referenz:** Baseline für Security-Monitoring; pip CVE-2025-8869 Mitigation in DOCKER_HARDENING_REPORT.md referenziert.

---

## Kategorie 3: Planning (2 Dateien)

### 3.1 M7_SKELETON.md

**Kategorie:** Planning (Milestone)
**Datum:** 2025-12-27 (letzte Änderung: 06:34)
**Größe:** 20.0 KB

**Archivziel:** `knowledge/roadmap/M7_production_paper_trading_skeleton.md`

**Begründung:** Milestone 7 Planning-Dokument mit 8 Clustern (C1-C8: Data/Feed, Signal, Risk, Execution, PSM, Observability, Reporting, Ops); gehört zu Roadmap-Dokumentation.

**Referenz:** Kanonische Roadmap-Quelle; sollte in ROADMAP.md oder Milestone-Tracking integriert werden.

---

### 3.2 FUTURE_SERVICES.md

**Kategorie:** Planning (Integration Roadmap)
**Datum:** 2025-12-24
**Größe:** 14.9 KB

**Archivziel:** `knowledge/roadmap/future_services_integration.md`

**Begründung:** Orphaned Dockerfiles Tracking (allocation, regime, ws, market, paper_runner); dokumentiert Integrationsstatus und Blocker.

**Referenz:** Wird aktiv gepflegt; sollte als Living Document in Roadmap bleiben, nicht archivieren (ACHTUNG: Diese Datei ist AKTIV).

**Empfehlung:** NICHT archivieren, sondern in `knowledge/roadmap/` verschieben als aktive Roadmap-Komponente.

---

## Kategorie 4: Analysis (4 Dateien)

### 4.1 LEGACY_ANALYSIS.md

**Kategorie:** Analysis (Legacy Extraction)
**Datum:** 2025-12-24
**Größe:** 10.1 KB

**Archivziel:** `_legacy_quarantine/analysis/2025-12-24_legacy_files_tier1_extraction.md`

**Begründung:** Analyse von Legacy-Dateien aus Quarantine (Tier1); dokumentiert Paper Runner Dockerfile-Funde und DB-Schema-Erkenntnisse; gehört zu Legacy-Dokumentation.

**Referenz:** Quell-Dateien in `_legacy_quarantine/files1_Tier1`; Erkenntnisse teilweise in FUTURE_SERVICES.md integriert.

---

### 4.2 LEGACY_FILES.md

**Kategorie:** Analysis (Migration Guide)
**Datum:** 2025-12-24
**Größe:** 8.7 KB

**Archivziel:** `_legacy_quarantine/migration/legacy_compose_files_deprecation_guide.md`

**Begründung:** Deprecation-Guide für Legacy Compose-Files (docker-compose.base.yml, docker-compose.yml); dokumentiert Migration Paths zu kanonischer Struktur.

**Referenz:** Kanonische Compose-Struktur in `infrastructure/compose/`; Guide für Übergangsphase.

---

### 4.3 LOGS_CONCEPT_ANALYSIS.md

**Kategorie:** Analysis (Conceptual)
**Datum:** 2025-12-27
**Größe:** 15.2 KB

**Archivziel:** `knowledge/audits/2025-12-27_logs_concept_working_vs_docs.md`

**Begründung:** Konzeptanalyse logs/ Trennung (Working Repo Runtime Logs vs. Docs Hub Knowledge Artifacts); decision-ready Analysis ohne Entscheidung.

**Referenz:** Issue #124; sollte in Decision Log referenziert werden, wenn Entscheidung getroffen wird.

---

### 4.4 SERVICE_INTEGRATION_STATUS.md

**Kategorie:** Analysis (Status Report)
**Datum:** 2025-12-24
**Größe:** 7.2 KB

**Archivziel:** `logs/sessions/2025-12-24_service_integration_status.md`

**Begründung:** Session-basierter Status-Report (Port-Fixes, Dockerfile-Fixes, Config-Discovery); temporärer Natur wie Session Reports.

**Referenz:** Technische Änderungen in Repos committed; Report dokumentiert Arbeitsstatus ohne permanente Relevanz.

---

## Kategorie 5: Runbooks (1 Datei)

### 5.1 DOCKER_STACK_RUNBOOK.md

**Kategorie:** Operational Runbook
**Datum:** 2025-12-26 (letzte Änderung: 19:35)
**Größe:** 33.4 KB

**Archivziel:** NICHT ARCHIVIEREN - KANONISCHES DOKUMENT

**Begründung:** Aktives Operational Runbook (740+ Zeilen, 9 Failure-Scenarios); kanonische Quelle für Stack-Troubleshooting und Disaster Recovery.

**Empfehlung:** Verbleibt im Working Repo unter `docs/runbook_docker_stack.md` (bereits kanonischer Speicherort).

**Referenz:** Erfüllt Criterion E (Failure Runbook); wird kontinuierlich gepflegt.

---

## Kategorie 6: Agent Definitions (1 Datei)

### 6.1 AGENTS.md

**Kategorie:** Agent Charter (Canonical)
**Datum:** 2025-12-27
**Größe:** 8.2 KB

**Archivziel:** KONFLIKT - DOPPLUNG MIT KANONISCHER QUELLE

**Begründung:** Datei deklariert sich selbst als "Single Source of Truth" mit physischem Speicherort `C:\Users\janne\Documents\GitHub\Workspaces\AGENTS.md` (außerhalb Repos).

**Problem:** Datei im Working Repo dupliziert kanonische Quelle; verstößt gegen eigene Regel "keine Kopien, keine Spiegelungen".

**Empfehlung:**
- **LÖSCHEN** aus Working Repo (Claire_de_Binare/AGENTS.md)
- Kanonische Quelle ist `C:\Users\janne\Documents\GitHub\Workspaces\AGENTS.md`
- Working Repo sollte nur Symlink oder README mit Verweis auf kanonische Quelle enthalten

**Referenz:** Kanonischer Rollenpfad: `C:\Users\janne\Documents\GitHub\Workspaces\.cdb_local\agents\roles`

---

## Migration Summary Table

| # | Datei | Kategorie | Ziel | Aktion |
|---|-------|-----------|------|--------|
| 1 | AUTONOMOUS_EXECUTION_SUMMARY.md | Session Report | logs/sessions/ | Archivieren |
| 2 | AUTONOMOUS_WORK_COMPLETE_2025-12-24.md | Session Report | logs/sessions/ | Archivieren |
| 3 | FINAL_STATUS_2025-12-24.md | Session Report | logs/sessions/ | Archivieren |
| 4 | DOCKER_HARDENING_REPORT.md | Audit Report | knowledge/reviews/ | Archivieren |
| 5 | HARDENING_VERIFICATION.md | Audit Report | knowledge/reviews/ | Archivieren |
| 6 | Docker Container & Image Vulnerability Scan Report.md | Audit Report | knowledge/reviews/ | Archivieren |
| 7 | M7_SKELETON.md | Planning | knowledge/roadmap/ | Archivieren |
| 8 | FUTURE_SERVICES.md | Planning | knowledge/roadmap/ | **VERSCHIEBEN (AKTIV)** |
| 9 | LEGACY_ANALYSIS.md | Analysis | _legacy_quarantine/analysis/ | Archivieren |
| 10 | LEGACY_FILES.md | Analysis | _legacy_quarantine/migration/ | Archivieren |
| 11 | LOGS_CONCEPT_ANALYSIS.md | Analysis | knowledge/audits/ | Archivieren |
| 12 | SERVICE_INTEGRATION_STATUS.md | Analysis | logs/sessions/ | Archivieren |
| 13 | DOCKER_STACK_RUNBOOK.md | Runbook | - | **BEHALTEN (KANONISCH)** |
| 14 | AGENTS.md | Agent Charter | - | **LÖSCHEN (DOPPLUNG)** |

---

## Aktionsplan

### Sofort-Aktionen (Kritisch)

1. **AGENTS.md LÖSCHEN** aus Working Repo
   - Grund: Dupliziert kanonische Quelle außerhalb Repo
   - Ersatz: README mit Verweis auf `C:\Users\janne\Documents\GitHub\Workspaces\AGENTS.md`

2. **FUTURE_SERVICES.md VERSCHIEBEN** (nicht archivieren)
   - Quelle: `Claire_de_Binare/FUTURE_SERVICES.md`
   - Ziel: `Claire_de_Binare_Docs/knowledge/roadmap/future_services_integration.md`
   - Grund: Living Document, wird aktiv gepflegt

### Archivierung (12 Dateien)

#### Session Reports → logs/sessions/ (4 Dateien)
- AUTONOMOUS_EXECUTION_SUMMARY.md → 2025-12-24_autonomous_execution_summary.md
- AUTONOMOUS_WORK_COMPLETE_2025-12-24.md → 2025-12-24_autonomous_work_complete.md
- FINAL_STATUS_2025-12-24.md → 2025-12-24_final_status.md
- SERVICE_INTEGRATION_STATUS.md → 2025-12-24_service_integration_status.md

#### Audit Reports → knowledge/reviews/ (3 Dateien)
- DOCKER_HARDENING_REPORT.md → 2025-12-27_docker_hardening_audit.md
- HARDENING_VERIFICATION.md → 2025-12-24_hardening_verification_a-g_criteria.md
- Docker Container & Image Vulnerability Scan Report.md → 2025-12-23_vulnerability_scan_docker_scout.md

#### Planning → knowledge/roadmap/ (1 Datei)
- M7_SKELETON.md → M7_production_paper_trading_skeleton.md

#### Analysis → _legacy_quarantine/ (2 Dateien)
- LEGACY_ANALYSIS.md → _legacy_quarantine/analysis/2025-12-24_legacy_files_tier1_extraction.md
- LEGACY_FILES.md → _legacy_quarantine/migration/legacy_compose_files_deprecation_guide.md

#### Analysis → knowledge/audits/ (1 Datei)
- LOGS_CONCEPT_ANALYSIS.md → 2025-12-27_logs_concept_working_vs_docs.md

### Keine Aktion (1 Datei)

- **DOCKER_STACK_RUNBOOK.md** - Verbleibt im Working Repo als kanonisches Operational Runbook

---

## Validierung

### Voraussetzungen vor Migration

1. **Zielverzeichnisse prüfen:**
   ```bash
   ls -la Claire_de_Binare_Docs/logs/sessions/
   ls -la Claire_de_Binare_Docs/knowledge/reviews/
   ls -la Claire_de_Binare_Docs/knowledge/roadmap/
   ls -la Claire_de_Binare_Docs/knowledge/audits/
   ls -la Claire_de_Binare_Docs/_legacy_quarantine/analysis/
   ls -la Claire_de_Binare_Docs/_legacy_quarantine/migration/
   ```

2. **Namenskonflikte prüfen:**
   - Keine bestehenden Dateien mit gleichen Namen überschreiben
   - Bei Konflikt: Suffix `_v2` oder `_updated` anhängen

3. **Referenzen aktualisieren:**
   - DOCS_HUB_INDEX.md: Neue Dateien registrieren
   - index.yaml: Metadaten für archivierte Dateien hinzufügen
   - README-Dateien in Zielverzeichnissen: Kurzbeschreibungen ergänzen

### Post-Migration Prüfung

1. **Working Repo Cleanup:**
   ```bash
   # Diese Dateien sollten nach Migration nicht mehr existieren:
   git rm AUTONOMOUS_EXECUTION_SUMMARY.md
   git rm AUTONOMOUS_WORK_COMPLETE_2025-12-24.md
   git rm FINAL_STATUS_2025-12-24.md
   git rm "Docker Container & Image Vulnerability Scan Report.md"
   git rm DOCKER_HARDENING_REPORT.md
   git rm HARDENING_VERIFICATION.md
   git rm M7_SKELETON.md
   git rm FUTURE_SERVICES.md
   git rm LEGACY_ANALYSIS.md
   git rm LEGACY_FILES.md
   git rm LOGS_CONCEPT_ANALYSIS.md
   git rm SERVICE_INTEGRATION_STATUS.md
   git rm AGENTS.md
   ```

2. **Docs Hub Commit:**
   ```bash
   cd Claire_de_Binare_Docs
   git add logs/sessions/* knowledge/reviews/* knowledge/roadmap/* knowledge/audits/* _legacy_quarantine/*
   git commit -m "docs: Archive 12 working repo docs + migrate FUTURE_SERVICES

   Session Reports (4):
   - 2025-12-24 autonomous execution & work complete
   - 2025-12-24 final status & service integration

   Audit Reports (3):
   - 2025-12-27 Docker hardening audit
   - 2025-12-24 A-G criteria verification
   - 2025-12-23 vulnerability scan (Docker Scout)

   Planning (1+1):
   - M7 production paper trading skeleton (archived)
   - FUTURE_SERVICES integration roadmap (migrated to active roadmap)

   Analysis (3):
   - Legacy files extraction & migration guide
   - Logs concept analysis (Working vs. Docs)

   Cleanup:
   - Removed AGENTS.md duplicate from working repo (canon in Workspace root)"
   ```

---

## Begründungen Zusammenfassung

### Warum archivieren?

**Session Reports (4):** Zeitgebundene Arbeitsprotokolle ohne permanenten Wissenswert; technische Inhalte in kanonischen Dokumenten erfasst.

**Audit Reports (3):** Permanente Wissensbasis für Security- und Compliance-Baselines; Referenz für Folge-Audits und Issue-Tracking.

**Planning (1):** Milestone-Dokumentation als historischer Snapshot; sollte in aktive Roadmap-Struktur integriert werden.

**Analysis (3):** Legacy-Dokumentation und konzeptuelle Analysen; teilweise entscheidungsbereit, teilweise historisch.

### Warum NICHT archivieren?

**DOCKER_STACK_RUNBOOK.md:** Aktives Operational Runbook, wird kontinuierlich gepflegt; kanonische Quelle für Stack-Operations.

**FUTURE_SERVICES.md:** Living Document, wird aktiv für Service-Integration verwendet; gehört zu aktiver Roadmap.

**AGENTS.md:** Dopplung der kanonischen Quelle; sollte gelöscht werden, nicht archiviert.

---

## Referenzen

- **Issue #122:** Docker Hardening Audit
- **Issue #124:** Logs Concept Separation
- **Criterion E:** Failure Runbook (DOCKER_STACK_RUNBOOK.md)
- **A-G Criteria:** Stack Hardening Acceptance Criteria
- **Docs Hub Index:** DOCS_HUB_INDEX.md
- **Kanonischer Agent-Pfad:** C:\Users\janne\Documents\GitHub\Workspaces\AGENTS.md

---

**Erstellt:** 2025-12-27
**Agent:** documentation-engineer
**Workflow:** Docs Curator (Docs Upgrader)
