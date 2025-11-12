# Migration Map – Cleanroom

## Zielstruktur (Docs)
- docs/architecture/: ARCHITEKTUR.md, SYSTEM_FLUSSDIAGRAMM.md, Service-Kommunikation & Datenflüsse.md, DATABASE_SCHEMA.sql
- docs/security/: SECURITY.md, SECURITY_FIX_PLAN.md, SECURITY_RISK_REPORT.md, Risikomanagement-Logik.md
- docs/ops/: BACKUP_STRATEGY.md, DEPLOYMENT_CHECKLIST.md, RUNBOOK_DOCKER_OPERATIONS.md, BACKUP_ANLEITUNG.md
- docs/meetings/: SESSION_MEMO_*.md (konsolidiert, Duplikate entfernt)
- docs/reports/: FINAL_STATUS.md, TEST_RERUN_EVIDENCE_*, E2E_TEST_REPORT_*, SCAN_REPORT.md
- docs/research/: RESEARCH_*.md, semantic_index.json, knowledge_inventory.json
- docs/quickstart/: archive/legacy_quickstart Inhalte, README_GUIDE.md
- docs/tooling/: README_TOOLS.md, docker/docker.instructions.md, scripts/powershell.instructions.md

## Migrationsliste
| Quelle | Ziel | Priorität | Grund |
|--------|------|-----------|-------|
| archive/legacy_quickstart/QUICK_START.md | docs/quickstart/QUICK_START.md | P2 | Vereinheitlichung der Onboarding-Guides (Inventur archive/legacy_quickstart) |
| archive/legacy_quickstart/DOCKER_QUICKSTART.md | docs/quickstart/DOCKER_QUICKSTART.md | P2 | Historische Docker-Anleitung in Hauptdoku überführen |
| archive/docs/7D_PAPER_TRADING_TEST.md | docs/reports/7D_PAPER_TRADING_TEST.md | P2 | Testbericht in Reports bündeln |
| backoffice/docs/DECISION_LOG.md | docs/DECISION_LOG.md | P1 | Architekturentscheidungen sollen im Root dokumentiert bleiben |
| backoffice/docs/ARCHITEKTUR.md | docs/architecture/ARCHITEKTUR.md | P1 | Architekturkapitel zentralisieren |
| backoffice/docs/SYSTEM_FLUSSDIAGRAMM.md | docs/architecture/SYSTEM_FLUSSDIAGRAMM.md | P1 | Systemübersicht neben Architektur darstellen |
| backoffice/docs/Service-Kommunikation & Datenflüsse.md | docs/architecture/SERVICE_DATA_FLOWS.md | P1 | Service-Kommunikation mit Architektur verknüpfen |
| backoffice/docs/Risikomanagement-Logik.md | docs/security/RISK_LOGIC.md | P1 | Sicherheits-/Risk-Thema in Security-Bereich schieben |
| backoffice/docs/SECURITY.md | docs/security/SECURITY.md | P1 | Security-Grundsatzdoku konsolidieren |
| backoffice/docs/SECURITY_FIX_PLAN.md | docs/security/SECURITY_FIX_PLAN.md | P1 | Sicherheitsmaßnahmen referenzierbar halten |
| backoffice/docs/SECURITY_RISK_REPORT.md | docs/security/SECURITY_RISK_REPORT.md | P1 | Risk-Report zentralisieren |
| backoffice/docs/BACKUP_STRATEGY.md | docs/ops/BACKUP_STRATEGY.md | P2 | Operations-Guides bündeln |
| operations/backup/BACKUP_ANLEITUNG.md | docs/ops/BACKUP_ANLEITUNG.md | P2 | Backup-Inhalte in neue Ops-Struktur einpassen |
| backoffice/automation/RUNBOOK_DOCKER_OPERATIONS.md | docs/ops/RUNBOOK_DOCKER_OPERATIONS.md | P2 | Runbooks in Ops-Sektion vereinheitlichen |
| backoffice/docs/TEST_RUNBOOK.md | docs/ops/TEST_RUNBOOK.md | P2 | Testbetrieb dokumentiert halten |
| backoffice/docs/SESSION_MEMO_* | docs/meetings/SESSION_MEMO_*.md (kuratierte Sammel-Doku) | P3 | Sitzungsprotokolle nach Themen bündeln, Redundanzen vermeiden |
| evidence/TEST_RERUN_EVIDENCE_* | docs/reports/TEST_RERUN_EVIDENCE_* | P2 | Testevidenz dauerhaft verfügbar machen |
| backoffice/docs/reports/* | docs/reports/* | P2 | Reports in eigenen Bereich legen |
| backoffice/docs/research/* | docs/research/* | P3 | Forschungsnotizen thematisch gruppieren |
| dashboard/docs/DASHBOARD_README.md | docs/tooling/DASHBOARD_README.md | P3 | Tool-spezifische Doku zentralisieren |
| docker/docker.instructions.md | docs/tooling/DOCKER_TOOLKIT.md | P3 | Docker-Toolkit-Guide in Tooling-Bereich |
| scripts/powershell.instructions.md | docs/tooling/POWERSHELL_GUIDE.md | P3 | Skript-Doku zusammenführen |

## Verlinkungen aktualisieren (Hinweise)
- README.md → Links auf neue `docs/architecture/` und `docs/ops/` Pfade anpassen.
- SERVICE_TEMPLATE.md → Verweise auf Architektur-Dokumente aktualisieren.
- backoffice/services/**/README.md → interne Referenzen auf neue docs/ Pfade prüfen.
- Docker-Playbooks (docker/mcp/README.md) → Quickstart-Links anpassen.
- scripts/generate_data_flow.py → Falls Pfade hart codiert sind, nachziehen.

## Akzeptanzkriterien
- Jeder Migrationseintrag führt Quelle → Ziel mit Priorität und Grund.
- Keine Dateioperationen durch diesen Plan.
- Zielstruktur deckt alle identifizierten Doc-Gruppen aus Inventur ab.
- Technische Hinweise listen betroffene Dateien zur späteren Aktualisierung.
