# Archivierungsplan - Executive Summary

## Quick Reference: 14 Dateien → 3 Aktionen

### ✅ Archivieren (12 Dateien)

#### logs/sessions/ (4 Dateien)
- `AUTONOMOUS_EXECUTION_SUMMARY.md` → `2025-12-24_autonomous_execution_summary.md`
- `AUTONOMOUS_WORK_COMPLETE_2025-12-24.md` → `2025-12-24_autonomous_work_complete.md`
- `FINAL_STATUS_2025-12-24.md` → `2025-12-24_final_status.md`
- `SERVICE_INTEGRATION_STATUS.md` → `2025-12-24_service_integration_status.md`

#### knowledge/reviews/ (3 Dateien)
- `DOCKER_HARDENING_REPORT.md` → `2025-12-27_docker_hardening_audit.md`
- `HARDENING_VERIFICATION.md` → `2025-12-24_hardening_verification_a-g_criteria.md`
- `Docker Container & Image Vulnerability Scan Report.md` → `2025-12-23_vulnerability_scan_docker_scout.md`

#### knowledge/roadmap/ (1 Datei)
- `M7_SKELETON.md` → `M7_production_paper_trading_skeleton.md`

#### knowledge/audits/ (1 Datei)
- `LOGS_CONCEPT_ANALYSIS.md` → `2025-12-27_logs_concept_working_vs_docs.md`

#### _legacy_quarantine/analysis/ (1 Datei)
- `LEGACY_ANALYSIS.md` → `2025-12-24_legacy_files_tier1_extraction.md`

#### _legacy_quarantine/migration/ (1 Datei)
- `LEGACY_FILES.md` → `legacy_compose_files_deprecation_guide.md`

---

### 🔄 Verschieben (1 Datei - AKTIV)

- `FUTURE_SERVICES.md` → `knowledge/roadmap/future_services_integration.md`
  - **Grund:** Living Document, wird aktiv gepflegt
  - **NICHT archivieren** - bleibt aktive Roadmap-Komponente

---

### ⚠️ Löschen (1 Datei - DOPPLUNG)

- `AGENTS.md`
  - **Grund:** Dupliziert kanonische Quelle in `C:\Users\janne\Documents\GitHub\Workspaces\AGENTS.md`
  - **Ersatz:** README mit Verweis auf kanonische Quelle

---

### 🛡️ Behalten (1 Datei - KANONISCH)

- `DOCKER_STACK_RUNBOOK.md`
  - **Grund:** Aktives Operational Runbook (Criterion E)
  - **Verbleibt:** Working Repo als kanonisches Dokument

---

## Schnellstart-Migration

```bash
# 1. Zielverzeichnisse vorbereiten (falls nicht vorhanden)
cd Claire_de_Binare_Docs
mkdir -p logs/sessions knowledge/reviews knowledge/roadmap knowledge/audits
mkdir -p _legacy_quarantine/analysis _legacy_quarantine/migration

# 2. Session Reports kopieren
cp ../Claire_de_Binare/AUTONOMOUS_EXECUTION_SUMMARY.md logs/sessions/2025-12-24_autonomous_execution_summary.md
cp ../Claire_de_Binare/AUTONOMOUS_WORK_COMPLETE_2025-12-24.md logs/sessions/2025-12-24_autonomous_work_complete.md
cp ../Claire_de_Binare/FINAL_STATUS_2025-12-24.md logs/sessions/2025-12-24_final_status.md
cp ../Claire_de_Binare/SERVICE_INTEGRATION_STATUS.md logs/sessions/2025-12-24_service_integration_status.md

# 3. Audit Reports kopieren
cp ../Claire_de_Binare/DOCKER_HARDENING_REPORT.md knowledge/reviews/2025-12-27_docker_hardening_audit.md
cp ../Claire_de_Binare/HARDENING_VERIFICATION.md knowledge/reviews/2025-12-24_hardening_verification_a-g_criteria.md
cp "../Claire_de_Binare/Docker Container & Image Vulnerability Scan Report.md" knowledge/reviews/2025-12-23_vulnerability_scan_docker_scout.md

# 4. Planning kopieren
cp ../Claire_de_Binare/M7_SKELETON.md knowledge/roadmap/M7_production_paper_trading_skeleton.md
cp ../Claire_de_Binare/FUTURE_SERVICES.md knowledge/roadmap/future_services_integration.md

# 5. Analysis kopieren
cp ../Claire_de_Binare/LOGS_CONCEPT_ANALYSIS.md knowledge/audits/2025-12-27_logs_concept_working_vs_docs.md
cp ../Claire_de_Binare/LEGACY_ANALYSIS.md _legacy_quarantine/analysis/2025-12-24_legacy_files_tier1_extraction.md
cp ../Claire_de_Binare/LEGACY_FILES.md _legacy_quarantine/migration/legacy_compose_files_deprecation_guide.md

# 6. Docs Hub commit
git add logs/ knowledge/ _legacy_quarantine/
git commit -m "docs: Archive 12 working repo docs + migrate FUTURE_SERVICES"

# 7. Working Repo cleanup
cd ../Claire_de_Binare
git rm AUTONOMOUS_EXECUTION_SUMMARY.md AUTONOMOUS_WORK_COMPLETE_2025-12-24.md
git rm FINAL_STATUS_2025-12-24.md SERVICE_INTEGRATION_STATUS.md
git rm DOCKER_HARDENING_REPORT.md HARDENING_VERIFICATION.md
git rm "Docker Container & Image Vulnerability Scan Report.md"
git rm M7_SKELETON.md FUTURE_SERVICES.md
git rm LEGACY_ANALYSIS.md LEGACY_FILES.md LOGS_CONCEPT_ANALYSIS.md
git rm AGENTS.md
git commit -m "docs: Move docs to canonical Docs Hub, remove duplicates"
```

---

## Kategorisierung Logik

| Kategorie | Ziel | Kriterium |
|-----------|------|-----------|
| **Session Report** | logs/sessions/ | Zeitgebundene Arbeitsprotokolle, keine permanente Relevanz |
| **Audit Report** | knowledge/reviews/ | Security/Compliance Baselines, permanente Wissensbasis |
| **Planning** | knowledge/roadmap/ | Milestone-Dokumentation, Integrations-Roadmaps |
| **Analysis** | knowledge/audits/ oder _legacy_quarantine/ | Konzept-Analysen (audits) oder Legacy-Dokumentation (quarantine) |
| **Runbook** | BEHALTEN im Working Repo | Aktive Operational Runbooks (kanonisch) |
| **Agent Definition** | LÖSCHEN (Dopplung) | Kanonische Quelle außerhalb Repo |

---

**Details:** Siehe DOCS_ARCHIVE_PLAN.md
