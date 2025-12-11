# TODO - Konsolidiert

**Erstellt**: 2025-12-10
**Zweck**: Single Source of Truth für alle offenen Tasks im CDB-Projekt
**Referenzen**: CDB_MASTER_AGENDA.md (Strategie), PROJECT_STATUS.md (Operativer Status)

---

## P0 - SOFORT (< 1 Woche)

### Root Cleanup & Dokumentation
- [ ] **Root Cleanup abschließen**
  - [x] .gitignore prüfen (bereits vollständig)
  - [ ] Archiv-Struktur erstellen
  - [ ] 5 Dateien archivieren (inkl. TASKS_CODEX.txt)
  - [ ] 2 Dateien löschen (PROMPT_FOR_CLAUDE_CODE.txt, START_PROMPT_CLAUDE_CODE.txt)
  - [ ] 2 Dateien in Kellerkiste (PROMPT_TODO_EXECUTION.md, Arbeitsauftrag an ORCHESTRATOR.md)
  - [ ] ROOT_CLEANUP_LOG.md erstellen
  - Referenz: `.claude/plans/cheerful-sleeping-gray.md`
  - Dauer: ~25 min

### N1-Phase Finalisierung
- [ ] **ENV-Validation ausführen**
  - `backoffice/automation/check_env.ps1` gegen `.env` laufen lassen
  - Ergebnis in PROJECT_STATUS.md dokumentieren
  - Dauer: < 1h

- [ ] **Systemcheck #1 durchführen**
  - Container starten, Health prüfen
  - Status-Tabelle in PROJECT_STATUS.md aktualisieren
  - Details werden durch nächste Prompts geklärt
  - Dauer: < 1h

---

## P1 - KURZFRISTIG (1-2 Wochen)

### Paper-Test Vorbereitung
- [ ] **Portfolio & State Manager implementieren**
  - Portfoliozustand verwalten
  - State-Übergänge zwischen Services
  - Dauer: 2-3 Tage

- [ ] **End-to-End Paper-Test durchführen**
  - Event-Flow: `market_data → signals → orders → order_results`
  - Alle Services im Zusammenspiel testen
  - Dauer: 1 Tag

- [ ] **Logging & Analytics Layer aktivieren**
  - Persistenz aktivieren
  - Einfache Auswertung implementieren
  - Dauer: 2 Tage

---

## P2 - MITTELFRISTIG (1-2 Monate)

### Infrastruktur & Security
- [ ] **Infra-Hardening (SR-004, SR-005)**
  - Redis Security Hardening
  - PostgreSQL Security Hardening
  - Grafana Security Hardening
  - Prometheus Security Hardening
  - Referenz: `backoffice/docs/FINAL_STATUS.md` (Post-Migration TODOs)
  - Dauer: 8-12h

### CI/CD & Qualität
- [ ] **CI/CD Pipeline erweitern**
  - Branch Protection Rules aktivieren
  - Trivy Container Scanning integrieren (CONDITIONAL: CRITICAL blocks, HIGH warns)
  - Conventional Commits enforcement (STRICT)
  - Coverage Threshold: 70% minimum
  - Squash-Merge Strategy aktivieren
  - Referenz: `.claude/plans/wobbly-booping-ladybug.md` (approved plan aus vorheriger Session)
  - Dauer: 5-7h

- [ ] **Labels & Milestones deployen**
  - 20 Labels zu GitHub hinzufügen (pr_labels.json)
  - 9 Milestones zu GitHub hinzufügen (milestones.json)
  - Auto-Labeling aktivieren
  - Dauer: 1-2h

### Monitoring & Observability
- [ ] **Grafana-Dashboards konfigurieren**
  - Equity Dashboard
  - Drawdown Dashboard
  - Alerts einrichten
  - Dauer: 4-6h

- [ ] **PostgreSQL-Backup-Job automatisieren**
  - Backup-Script implementieren (laut Strategie in PROJECT_STATUS.md)
  - Task Scheduler / Cron einrichten
  - Retention: 14 Tage
  - Dauer: 2-3h

---

## P3 - LANGFRISTIG (3+ Monate)

### Security & Secrets Management
- [ ] **HashiCorp Vault Integration**
  - Vault-Instanz aufsetzen
  - Secrets aus .env/.yaml entfernen
  - Services auf Vault umstellen
  - Referenz: CDB_MASTER_AGENDA.md P2.3
  - Priorität: KÖNNTE FRÜHER KOMMEN, falls ENV-Konflikte kritisch werden

### Code-Qualität & Tooling
- [ ] **SonarQube Integration**
  - SonarQube-Instanz aufsetzen (lokal/remote)
  - In CI/CD integrieren
  - Quality Gates definieren
  - Referenz: CDB_MASTER_AGENDA.md P2.2

### Infrastruktur-Erweiterung
- [ ] **MCP Infrastruktur (Toolstack + Inside Stack)**
  - MCP Gateway als Single Entry Point
  - Monitoring-Stack (Grafana, Prometheus, Node Exporter, cAdvisor)
  - Docker-Management (Portainer, Watchtower)
  - Logging (ELK Stack)
  - MCP Inside Stack (agents-sync, cdb-logger)
  - Referenz: CDB_MASTER_AGENDA.md P1
  - Status: "Stark reduziert" - Details später

---

## P4 - DOCUMENTATION (laufend)

### Dokumentations-Bibliothek
- [ ] **CONTRIBUTING.md erstellen**
  - Contribution Guidelines
  - Code Style
  - PR-Prozess
  - Dauer: 2-3h

- [ ] **ARCHITECTURE.md erstellen**
  - System-Übersicht
  - Service-Architektur
  - Datenflüsse
  - Dauer: 4-6h

- [ ] **CHANGELOG.md pflegen**
  - Release Notes
  - Breaking Changes
  - Migration Guides
  - Dauer: laufend

- [ ] **RELEASE_PROCESS.md erstellen**
  - Release-Workflow
  - Versioning Strategy
  - Deployment Checklist
  - Dauer: 2-3h

---

## BACKLOG - Code-Qualität Tools

**Status**: Geparkt bis N1-Phase abgeschlossen
**Quelle**: TASKS_CODEX.txt (archiviert, jetzt in tools/Tool Liste.md)
**Codex-Status**: 22/30 Tools bereits umgesetzt (siehe tools/ich_war_hier.md)

### Verbleibende Tools (TASK 16-45)
- [ ] TASK 16: CDB_Filetype_Inventory
- [ ] TASK 17: CDB_Dead_Comment_Scanner
- [ ] TASK 18: CDB_Duplicate_Code_Detector
- [ ] TASK 19: CDB_Missing_Docstring_Finder
- [ ] TASK 20: CDB_Long_Function_Analyzer
- [ ] TASK 21: CDB_Class_Map_Builder
- [ ] TASK 22: CDB_Function_Map_Builder
- [ ] TASK 23: CDB_Empty_File_Detector
- [ ] ... (weitere 22 Tools, siehe tools/Tool Liste.md für Details)

**Hinweis**: Diese Tools sind für Code-Audits und -Analysen gedacht, nicht für den operativen Betrieb.

---

## WIDERSPRÜCHE & KLÄRUNGEN

### Gelöst
- ✅ **Test-Coverage**: PROJECT_STATUS.md ist aktuell (100% erreicht), FINAL_STATUS.md veraltet
- ✅ **Docker-Hardening**: SR-004 + Docker-Hardening sind EIN Block
- ✅ **WSL2-Migration**: Abgehakt, fertig
- ✅ **MCP-Stack**: Stark reduziert, alles andere später

### Offen
- ⏳ **ENV-Validation**: User erwartet Konflikte, möchte "durchziehen"
- ⏳ **Systemcheck #1**: Details werden durch nächste Prompts geklärt
- ⏳ **Orchestrator**: Aktualität von "Arbeitsauftrag an ORCHESTRATOR.md" unklar (→ Kellerkiste)

---

## ARCHIVIERTE TODO-QUELLEN

**Diese Datei ersetzt**:
- ~~TASKS_CODEX.txt~~ → Archiviert, ersetzt durch tools/Tool Liste.md (2025-12-10)
- Teile aus CDB_MASTER_AGENDA.md → Strategisch-operative Aufgaben hierher konsolidiert
- "NÄCHSTE SCHRITTE" aus PROJECT_STATUS.md → Hierher konsolidiert

**Was bleibt bestehen**:
- **CDB_MASTER_AGENDA.md** (Root) - Strategische Langzeit-Roadmap (P0-P8)
- **PROJECT_STATUS.md** (backoffice/) - Operativer Systemstatus, verweist hierher für TODOs
- **tools/Tool Liste.md** - Codex Tool-Katalog

---

## NOTIZEN

- Diese Datei ist **living document** - wird laufend aktualisiert
- Prioritäten können sich ändern basierend auf User-Feedback
- Zeitschätzungen sind grobe Richtwerte
- Bei Unklarheiten: USER fragen, nicht raten

**Letztes Update**: 2025-12-10 (Initiale Konsolidierung)
