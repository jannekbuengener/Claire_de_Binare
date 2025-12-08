# Kellerkiste Archive - Dezember 2025

> **Anti-Hortkultur Policy**: Dieses Archiv enthält historische Dateien, die nicht mehr aktiv benötigt werden.
> Nach 6 Monaten (Juni 2026) sollten diese Dateien geprüft und ggf. gelöscht werden.

## Archivierungsdatum

**2025-12-08**

---

## Archivierte Kategorien

### ANALYSIS_PHASE1
**Beschreibung**: Analyse-Dokumente aus der Pre-Recovery Phase (Nov 22-24, 2025)

**Dateien** (5):
- `ARCHITECTURAL_CODE_ANALYSIS_REPORT.md` (1,159 Zeilen)
- `ANALYSIS_SUMMARY.md` (320 Zeilen)
- `SYSTEM_STATUS_REPORT.md` (286 Zeilen)
- `SESSION_SUMMARY_2025-11-20.md` (253 Zeilen)
- `E2E_PAPER_TEST_REPORT.md` (256 Zeilen)

**Grund**: Diese Dokumente beschreiben den Systemzustand vor dem System-Recovery am 2025-12-05. Sie sind historisch wertvoll, aber nicht mehr operational relevant. Der aktuelle Status ist in `backoffice/PROJECT_STATUS.md` dokumentiert.

---

### DATABASE_PHASE1
**Beschreibung**: Datenbank-Phase-1-Dokumentation (Pre-Production)

**Dateien** (4):
- `DATABASE_ENHANCEMENT_ROADMAP.md` (406 Zeilen)
- `DATABASE_READINESS_REPORT.md` (364 Zeilen)
- `DATABASE_TRACKING_ANALYSIS.md` (420 Zeilen)
- `DATABASE_PHASE1_CHECKLIST.md` (284 Zeilen)

**Grund**: Phase 1 ist abgeschlossen. Die aktuelle Datenbank-Architektur ist in `backoffice/docs/architecture/` dokumentiert. Diese Dokumente zeigen den Entwicklungsweg, sind aber nicht mehr handlungsrelevant.

---

### GITHUB_AUTOMATION_COMPLETED
**Beschreibung**: GitHub PR/Issue/Milestone Automation (Einmalige Setup-Phase)

**Dateien** (10):
- `PR_LABELING_QUICKSTART.md` (322 Zeilen)
- `PR_LABELS.md` (203 Zeilen)
- `LABEL_STRUCTURE.md` (280 Zeilen)
- `README_PR_LABELING.md` (352 Zeilen)
- `GITHUB_PROJECTS_SETUP.md`
- `MILESTONE_PROGRESS.md`
- `MILESTONES_README.md`
- `label_all_prs.py`
- `label_all_prs.sh`
- `create_milestones.sh`

**Grund**: Diese Automation wurde einmalig ausgeführt, um GitHub Issues/PRs/Milestones zu strukturieren. Die Skripte sind veraltet (Hardcoded-Daten), die Labels sind aktiv in GitHub konfiguriert. Dokumentation ist nicht mehr nötig, da Setup abgeschlossen ist.

---

### LEGACY_DOCS
**Beschreibung**: Superseded Strategic Planning Documents

**Dateien** (2):
- `ROADMAP.md` (716 Zeilen)
- `IMMEDIATE_ACTION_ITEMS.md` (713 Zeilen)

**Grund**: Diese Dokumente wurden durch `CDB_MASTER_AGENDA.md` und `backoffice/PROJECT_STATUS.md` ersetzt. Sie enthalten veraltete Prioritäten aus November 2025.

---

### BACKUPS
**Beschreibung**: Configuration Backups (Pre-Recovery)

**Dateien** (2):
- `.env.backup`
- `CLAUDE.md.corrupted.backup`

**Grund**: Diese Backups stammen aus der Zeit vor dem System-Recovery (2025-12-05). Die aktuelle `.env` und `CLAUDE.md` sind operational. Diese Backups sind Snapshots, die bei Bedarf zur forensischen Analyse herangezogen werden können, aber nicht im aktiven Repo benötigt werden.

---

### ARTIFACTS (Gelöscht)
**Beschreibung**: Temporäre Build-Artifacts

**Dateien** (1, GELÖSCHT):
- `nul` (11 Bytes) - Windows-Artifact, kein Inhalt

**Grund**: Versehentlich erzeugtes leeres File, keine Relevanz.

---

## Lifecycle Policy

**Prüfung**: Juni 2026 (6 Monate nach Archivierung)

**Entscheidungskriterien**:
- Wurden Dateien in den letzten 6 Monaten referenziert? → Behalten
- Sind sie für Audit/Compliance relevant? → Behalten
- Sind sie rein historisch ohne Referenzwert? → Löschen

**Empfehlung** (Stand Dez 2025):
- **ANALYSIS_PHASE1**: Nach 6 Monaten löschen (superseded by current docs)
- **DATABASE_PHASE1**: Nach 6 Monaten löschen (superseded by architecture docs)
- **GITHUB_AUTOMATION_COMPLETED**: Nach 6 Monaten löschen (one-time scripts)
- **LEGACY_DOCS**: Nach 6 Monaten löschen (superseded by CDB_MASTER_AGENDA)
- **BACKUPS**: Behalten bis System stabil läuft ohne Regression-Bedarf (12+ Monate)

---

## Gesamtstatistik

**Archivierte Dateien**: ~35
**Geschätzte Größe**: 5-8 MB
**Reduzierung im Root**: 59 → 24 Files (60%)

---

## Siehe auch

- `CDB_MASTER_AGENDA.md` - Aktuelle Roadmap P0-P8
- `backoffice/PROJECT_STATUS.md` - Aktueller Systemstatus
- `CLAUDE.md` - Operational Protocol (Phase N1)
- `backoffice/docs/architecture/` - Aktuelle Architektur-Dokumentation
