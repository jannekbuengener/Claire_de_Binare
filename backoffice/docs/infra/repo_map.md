# Repository-Map - Claire de Binare (Cleanroom)

**Erstellt von**: claire-architect
**Datum**: 2025-11-16
**Scope**: Infrastruktur- und Runtime-relevante Verzeichnisse

## Verzeichnisstruktur

### Root-Ebene

| Verzeichnis/Datei | Rolle | Relevanz |
|-------------------|-------|----------|
| `/` (Root) | Projekt-Basis, Docker-Entry-Point | ⭐ HOCH |
| `backoffice/` | Services, Docs, Automation | ⭐ HOCH |
| `tests/` | Unit- & Integration-Tests | ⭐ HOCH |
| `sandbox/` | Dokumenten-Transfer-Pipeline, Wissensextraktion | ⭐ HOCH |
| `logs/` | Runtime-Logs (gemountet in Container) | MITTEL |

### Backoffice-Struktur

| Verzeichnis | Rolle | Services/Inhalte |
|-------------|-------|------------------|
| `backoffice/services/` | MVP-Services (Signal Engine, Risk Manager, Execution) | ⭐ HOCH |
| `backoffice/docs/` | Architektur-, Risk-, Event-Dokumentation | ⭐ HOCH |
| `backoffice/automation/` | PowerShell-Skripte (ENV-Check, Backups, etc.) | MITTEL |

### Service-Verzeichnisse (backoffice/services/)

Identifizierte Services (basierend auf docker-compose.yml und Dateisystem-Scan):

| Service-Ordner | Container-Name | Port | Status |
|----------------|----------------|------|--------|
| `signal_engine/` | `cdb_core` | 8001 | MVP |
| `risk_manager/` | `cdb_risk` | 8002 | MVP |
| `execution_service/` | `cdb_execution` | 8003 | MVP |
| `query_service/` | (nicht in compose) | — | Entwicklung? |

**Hinweis**: WebSocket/REST Screeners (`cdb_ws`, `cdb_rest`) nutzen Root-Dockerfiles, nicht backoffice/services/.

### Test-Struktur

| Verzeichnis | Typ | Inhalt |
|-------------|-----|--------|
| `tests/unit/` | Unit-Tests | `test_smoke_repo.py` |
| `tests/integration/` | Integration-Tests | `test_compose_smoke.py` |

### Infra-/Config-Dateien (Root)

| Datei | Rolle | Format |
|-------|-------|--------|
| `docker-compose.yml` | Haupt-Deployment-Definition | YAML |
| `Dockerfile` | Screener-Services (WS/REST) | Dockerfile |
| `Dockerfile.test` | Test-Setup | Dockerfile |
| `prometheus.yml` | Prometheus-Scrape-Config | YAML |
| ` - Kopie.env` | ENV-Template (mit Secrets-Platzhaltern) | ENV |
| `.gitignore`, `.gitattributes` | Git-Config | Text |

### Ausgeschlossene Bereiche

Ordner mit Punkt-Präfix (`.git/`, `.vscode/`, `.github/`, `.claude/`) sind gemäß Pipeline-Regeln ausgeschlossen.

## Relevanz-Kategorien

### ⭐ HOCH (kritisch für Infra/Runtime)

- `docker-compose.yml`, `prometheus.yml`
- `backoffice/services/` (alle Service-Dockerfiles)
- ` - Kopie.env` (ENV-Template)
- `backoffice/docs/` (Architektur-/Risk-Referenzen)

### MITTEL (supportiv, aber nicht blockierend)

- `tests/`
- `backoffice/automation/` (Skripte)
- `logs/` (Laufzeit-Daten)

### NIEDRIG/LEGACY (potenziell veraltet, zu prüfen)

- `Dockerfile - Kopie`, `Dockerfile - Kopie.test` (Duplikate?)
- Ungenutzte Scripts/Configs

## Bekannte Datenquellen

Basierend auf bereits durchgeführten Pipelines (Pipeline 1 & 2):

- `sandbox/output.md` - Konsolidierte Architektur-/Risk-Referenz
- `sandbox/audit_log.md` - Audit-Protokoll der Dokumenten-Transfer-Pipeline
- `sandbox/extracted_knowledge.md`, `sandbox/conflicts.md` (aus Pipeline 2, sofern vorhanden)

## Nächste Schritte (für software-jochen)

1. **File-Index**: Alle relevanten Files (Docker, Compose, Scripts, Tests, Configs) tabellarisch erfassen
2. **ENV-Index**: Alle ENV-Namen aus ` - Kopie.env`, `docker-compose.yml` und Service-Configs extrahieren (ohne Secrets!)
3. **Infra-Knowledge**: Services, Ports, Volumes, Netzwerke, Health-Checks aus docker-compose.yml strukturiert dokumentieren
