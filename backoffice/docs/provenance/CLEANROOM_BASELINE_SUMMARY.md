# Cleanroom Baseline Summary

**Datum**: 2025-01-17
**Phase**: Nullpunkt-Definition abgeschlossen
**Status**: ✅ **CLEANROOM ETABLIERT**
**ADR**: ADR-039 (Cleanroom-Repository als kanonische Codebasis)

---

## 1. Executive Summary

Das **Cleanroom-Repository (`Claire_de_Binare_Cleanroom`)** ist ab 2025-01-17 der offizielle, kanonische Stand des Projekts **Claire de Binare**.

**Was wurde erreicht:**
- ✅ Namenskonvention von "Claire de Binaire" auf "Claire de Binare" normalisiert
- ✅ Cleanroom-Repository als aktueller Ist-Zustand etabliert (nicht mehr "Ziel-Repo")
- ✅ Migration vom 2025-11-16 als abgeschlossen historisiert
- ✅ N1-Phase (Paper-Test) als nächstes Ziel definiert
- ✅ ADR-039 erstellt und in DECISION_LOG integriert

---

## 2. Single Source of Truth

### Kanonische Referenzdokumente

| Dokument | Pfad | Rolle |
|----------|------|-------|
| **KODEX** | `backoffice/docs/KODEX – Claire de Binare.md` | Projektgrundsätze, Architekturprinzipien |
| **N1-Architektur** | `backoffice/docs/architecture/N1_ARCHITEKTUR.md` | Systemarchitektur für Paper-Test-Phase |
| **Kanonisches Schema** | `backoffice/docs/schema/canonical_schema.yaml` | Datenmodell & Service-Definitionen |
| **DECISION_LOG** | `backoffice/docs/DECISION_LOG.md` | Architektur-Entscheidungen (ADR-001 bis ADR-039) |
| **PROJECT_STATUS** | `backoffice/PROJECT_STATUS.md` | Aktueller Projektstatus & Nächste Schritte |
| **EXECUTIVE_SUMMARY** | `backoffice/docs/provenance/EXECUTIVE_SUMMARY.md` | Kanonisierungs-Historie (2025-11-16) |

**Wichtig**: Nur Dokumente unter `backoffice/docs/` sind gültig. Root-Duplikate sind deprecated und müssen nach `archive/docs_original/` verschoben werden.

---

## 3. Wichtige Änderungen

### 3.1 Namens-Normalisierung (Binaire → Binare)

| Datei | Änderungstyp | Änderung |
|-------|--------------|----------|
| `KODEX – Claire de Binaire.md` | **UMBENENNEN** | → `KODEX – Claire de Binare.md` |
| `KODEX – Claire de Binare.md` (Inhalt) | **CONTENT_UPDATE** | Alle "Claire de Binaire" → "Claire de Binare" |
| `KODEX – Claire de Binare.md` (Hinweis) | **CONTENT_UPDATE** | Hinweis ergänzt: Frühere Schreibweise "Binaire" gilt als historisch |
| `N1_ARCHITEKTUR.md` | **CONTENT_UPDATE** | Zeile 11: "Claire de Binaire" → "Claire de Binare" |
| `EXECUTIVE_SUMMARY.md` | **CONTENT_UPDATE** | Titel & Zeile 3: "Binare" statt "Binaire" |

**Hinweis**: Weitere 25+ Dateien enthalten noch "Claire de Binaire" und müssen in Phase 3 aktualisiert werden (siehe ADR-039, Nächste Schritte).

---

### 3.2 Status-Bereinigung (Cleanroom als Ist-Zustand)

| Datei | Änderungstyp | Änderung |
|-------|--------------|----------|
| `PROJECT_STATUS.md` | **STATUS_BEREINIGT** | Phase: "95% CLEANROOM MIGRATION" → "100% CLEANROOM ETABLIERT - N1 PHASE AKTIV" |
| `PROJECT_STATUS.md` | **STATUS_BEREINIGT** | Nächste Schritte: Fokus auf N1 (Paper-Test), nicht mehr auf Migration |
| `PROJECT_STATUS.md` | **STATUS_BEREINIGT** | Letzte Erfolge: Migration als abgeschlossen markiert (2025-11-16) |
| `EXECUTIVE_SUMMARY.md` | **STATUS_BEREINIGT** | Status: "migrations-bereit" → "ABGESCHLOSSEN - CLEANROOM AKTIV" |
| `EXECUTIVE_SUMMARY.md` | **CONTENT_UPDATE** | Historischer Kontext ergänzt: Migration vom 2025-11-16 ist erfolgt |

---

### 3.3 Decision Log / ADR

| Datei | Änderungstyp | Änderung |
|-------|--------------|----------|
| `DECISION_LOG.md` | **ADDED_ADR** | ADR-039 erstellt: "Cleanroom-Repository als kanonische Codebasis etabliert" |

**ADR-039 Details**:
- **Datum**: 2025-01-17
- **Problem**: Ambivalente Dokumentation (Cleanroom als "Ziel" vs. Ist-Zustand)
- **Entscheidung**: Cleanroom ist ab sofort die einzige kanonische Codebasis
- **Konsequenzen**: Eindeutige Single Source of Truth, vereinfachtes Onboarding

---

## 4. Archiv-Struktur & Historisierung

### 4.1 Was bleibt unverändert (Archiv)

| Ordner | Rolle | Behandlung |
|--------|-------|------------|
| `archive/sandbox_backups/` | Historische Sandbox-Umgebung (Pre-Cleanroom) | **KEINE ÄNDERUNGEN** - bleibt als Backup |
| `archive/docs_original/` | Alte Root-Dateien (deprecated) | **KEINE ÄNDERUNGEN** - enthält alte Versionen |
| `archive/backoffice_original/` | Backup-Repo-Stand vor Migration | **KEINE ÄNDERUNGEN** |
| `archive/meeting_archive/` | Alte Meeting-Memos | **KEINE ÄNDERUNGEN** |

**Policy**: Historische Dokumente im Archiv behalten bewusst die alte Schreibweise "Binaire" - keine retroaktive Änderung.

---

### 4.2 Migrations-Dokumente (jetzt historisch)

| Dokument | Status | Behandlung |
|----------|--------|------------|
| `runbooks/MIGRATION_READY.md` | Historisch | Als "Historische Migration 2025-11-16" kennzeichnen |
| `runbooks/PRE_MIGRATION_README.md` | Historisch | Als "Historische Migration" kennzeichnen |
| `runbooks/PRE_MIGRATION_EXECUTION_REPORT.md` | Historisch | Als "Historische Migration" kennzeichnen |
| `runbooks/pre_migration_checklist.md` | Historisch | Als "Historische Migration" kennzeichnen |
| `provenance/CLEANROOM_MIGRATION_MANIFEST.md` | Historisch/Template | Als Template für zukünftige Migrationen kennzeichnen |
| `scripts/migration/cleanroom_migration_script.ps1` | Template | Skript-Kopf: "Dokumentiert Migration 2025-11-16, dient als Template" |

**Wichtig**: Diese Dokumente werden **NICHT gelöscht**, da sie wertvolle Templates für zukünftige Migrationen darstellen.

---

## 5. N1-Phase: Nächste Schritte

Gemäß `backoffice/docs/architecture/N1_ARCHITEKTUR.md` ist die **Paper-Test-Phase** das aktuelle Ziel:

### 5.1 Sofort (< 1h)
- [ ] Test-Infrastruktur aufsetzen (pytest, coverage)
- [ ] Risk-Manager Unit-Tests implementieren (Ziel: 80% Coverage)

### 5.2 Heute (< 4h)
- [ ] Market Data Ingestion (MDI) für historische Daten vorbereiten
- [ ] Strategy Engine Interface definieren
- [ ] Execution Simulator Grundstruktur erstellen

### 5.3 Diese Woche
- [ ] Portfolio & State Manager implementieren
- [ ] End-to-End Paper-Test durchführen
- [ ] Logging & Analytics Layer aktivieren

### 5.4 Post-N1 (Produktionsvorbereitung)
- [ ] Infra-Hardening (SR-004, SR-005)
- [ ] CI/CD Pipeline aufsetzen
- [ ] Grafana-Dashboard konfigurieren

---

## 6. Checkliste für zukünftige Contributors

### Wenn du Architektur änderst:
1. **KODEX prüfen** (`backoffice/docs/KODEX – Claire de Binare.md`)
   → Verstößt deine Änderung gegen Prinzipien 1-5?
2. **ADR erstellen** (`backoffice/docs/DECISION_LOG.md`)
   → Dokumentiere die Entscheidung als ADR-040, ADR-041, etc.
3. **N1-Architektur aktualisieren** (`backoffice/docs/architecture/N1_ARCHITEKTUR.md`)
   → Falls Module oder Event-Flows betroffen sind

### Wenn du Risk-Parameter änderst:
1. **Kanonisches Schema prüfen** (`backoffice/docs/schema/canonical_schema.yaml`)
   → Sind alle Risk-Parameter dokumentiert?
2. **ENV-Konvention beachten** (siehe ADR-035)
   → Dezimal-Format: `MAX_DAILY_DRAWDOWN_PCT=0.05` (nicht `5.0`)
3. **KODEX Risk-Kodex** (Kapitel 4)
   → Schutzschichten-Reihenfolge einhalten

### Wenn du Dokumentation änderst:
1. **Single Source of Truth** (`backoffice/docs/`)
   → Nur hier pflegen, **NICHT** im Root
2. **Namenskonvention** verwenden
   → "Claire de Binare" (nicht "Binaire")
3. **Provenance pflegen** (`backoffice/docs/provenance/`)
   → Bei größeren Änderungen: Eintrag in `audit_log.md`

### Wenn du Migration durchführst:
1. **Migrations-Templates nutzen**
   → `runbooks/CLEANROOM_MIGRATION_MANIFEST.md` als Vorlage
   → `scripts/migration/cleanroom_migration_script.ps1` als Basis
2. **Neue ADR erstellen**
   → Beschreibe Grund, Entscheidung, Konsequenzen
3. **Provenance dokumentieren**
   → Erstelle neue EXECUTIVE_SUMMARY für die Migration

---

## 7. Verbleibende Aufgaben (aus ADR-039)

### Phase 3: Namens-Fix für verbleibende Dateien

**Noch zu aktualisieren** (28 Dateien mit "Binaire"):

#### Service-Dokumentation (12 Dateien):
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

#### Schema & Provenance (5 Dateien):
- `backoffice/docs/schema/canonical_schema.yaml`
- `backoffice/docs/schema/canonical_model_overview.md`
- `backoffice/docs/schema/canonical_readiness_report.md`
- `backoffice/docs/provenance/CANONICAL_SOURCES.yaml`
- `backoffice/docs/provenance/FINAL_STATUS.md`
- `backoffice/docs/provenance/PIPELINE_COMPLETE_SUMMARY.md`
- `backoffice/docs/provenance/INDEX.md`

#### Weitere Dokumente (11 Dateien):
- `backoffice/docs/audit/AUDIT_CLEANROOM.md`
- `backoffice/docs/audit/AUDIT_PLAN.md`
- `backoffice/docs/meetings/MEETINGS_SUMMARY.md`
- `backoffice/docs/architecture/SYSTEM_FLUSSDIAGRAMM.md`
- `backoffice/docs/infra/repo_map.md`
- `backoffice/docs/knowledge/extracted_knowledge.md`
- u.a.

**Handlungsbedarf**: Bulk-Edit mit "Claire de Binaire" → "Claire de Binare" für alle oben genannten Dateien.

---

## 8. Zusammenfassung

### Was ist jetzt anders?

**Vorher (2025-01-16)**:
- ❌ Cleanroom als "Ziel-Repo" oder "migrations-bereit" beschrieben
- ❌ Unklar, ob Migration abgeschlossen ist
- ❌ 28 Dateien mit inkonsistenter Namensgebung ("Binaire")
- ❌ Nächste Schritte fokussieren auf "Migration ausführen"

**Nachher (2025-01-17)**:
- ✅ Cleanroom ist **aktueller, kanonischer Stand** (100%)
- ✅ Migration als **abgeschlossen** historisiert (2025-11-16)
- ✅ **Namenskonvention etabliert**: "Claire de Binare" verbindlich
- ✅ Nächste Schritte fokussieren auf **N1-Phase** (Paper-Test)
- ✅ **ADR-039** dokumentiert alle Änderungen
- ✅ **Single Source of Truth** klar definiert: `backoffice/docs/`

### Definierter Nullpunkt

**Datum**: 2025-01-17
**Repository**: `Claire_de_Binare_Cleanroom`
**Branch**: `main`
**Commit**: (wird erstellt nach Fertigstellung aller Änderungen)
**Tag**: `v1.0.1-cleanroom-baseline` (geplant)

**Kanonische Dokumentation**:
- Alle Dokumente unter `backoffice/docs/`
- Projektname: "Claire de Binare"
- Technische IDs: `claire_de_binare`

**Nächste Phase**: N1 - Paper-Test-Vorbereitung
**Referenz**: `backoffice/docs/architecture/N1_ARCHITEKTUR.md`

---

**Ende des Cleanroom Baseline Summary**

*Dieses Dokument ist die offizielle Zusammenfassung der Nullpunkt-Definition vom 2025-01-17.*
*Bei Fragen oder Unklarheiten: Siehe ADR-039 in `backoffice/docs/DECISION_LOG.md`.*
