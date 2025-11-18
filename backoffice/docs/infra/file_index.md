# File-Index - Infrastruktur & Runtime Files

**Erstellt von**: software-jochen
**Datum**: 2025-11-16
**Scope**: Docker, Compose, Scripts, Tests, Configs

## Legende

- **Typ**: dockerfile, compose, script, test, config, env
- **Rolle**: runtime (produktiv), infra (Deployment), migration, deployment, monitoring, test
- **Status**: kandidat_relevant, legacy, unklar

## Haupt-Deployment & Orchestrierung

| Pfad | Typ | Rolle | Status | Bemerkungen |
|------|-----|-------|--------|-------------|
| `docker-compose.yml` | compose | infra | ⭐ kandidat_relevant | Haupt-Deployment: 8 Services (Redis, Postgres, Prometheus, Grafana, WS, REST, Core, Risk, Execution, Signal-Gen) |
| `compose.yml` | compose | infra | unklar | Möglicherweise Duplikat oder Alt-Version von docker-compose.yml |

## Dockerfiles (Root-Ebene)

| Pfad | Typ | Rolle | Status | Bemerkungen |
|------|-----|-------|--------|-------------|
| `Dockerfile` | dockerfile | runtime | ⭐ kandidat_relevant | Screener-Services (WS/REST), verwendet ARG SCRIPT_NAME |
| `Dockerfile.test` | dockerfile | test | kandidat_relevant | Test-Setup |
| `Dockerfile - Kopie` | dockerfile | runtime | legacy | Duplikat von Dockerfile? |
| `Dockerfile - Kopie.test` | dockerfile | test | legacy | Duplikat von Dockerfile.test? |

## Dockerfiles (Services)

| Pfad | Typ | Rolle | Status | Bemerkungen |
|------|-----|-------|--------|-------------|
| `backoffice/services/signal_engine/Dockerfile` | dockerfile | runtime | ⭐ kandidat_relevant | Signal Engine (cdb_core) |
| `backoffice/services/risk_manager/Dockerfile` | dockerfile | runtime | ⭐ kandidat_relevant | Risk Manager (cdb_risk) |
| `backoffice/services/execution_service/Dockerfile` | dockerfile | runtime | ⭐ kandidat_relevant | Execution Service (cdb_execution) |

## Config-Dateien (Monitoring/Infra)

| Pfad | Typ | Rolle | Status | Bemerkungen |
|------|-----|-------|--------|-------------|
| `prometheus.yml` | config | monitoring | ⭐ kandidat_relevant | Prometheus Scrape-Config: 4 Jobs (prometheus, execution_service, signal_engine, risk_manager) |

## ENV-Templates

| Pfad | Typ | Rolle | Status | Bemerkungen |
|------|-----|-------|--------|-------------|
| ` - Kopie.env` | env | infra | ⭐ kandidat_relevant | ENV-Template mit Platzhaltern (⚠️ enthält aktuell echte Secrets, darf NICHT committet werden!) |

## PowerShell-Skripte (Automation)

| Pfad | Typ | Rolle | Status | Bemerkungen |
|------|-----|-------|--------|-------------|
| `backoffice/automation/check_env.ps1` | script | deployment | kandidat_relevant | ENV-Validierung: Duplikate, fehlende Variablen |

## Tests

| Pfad | Typ | Rolle | Status | Bemerkungen |
|------|-----|-------|--------|-------------|
| `tests/unit/test_smoke_repo.py` | test | test | kandidat_relevant | Unit-Tests: Repository-Smoke-Tests |
| `tests/integration/test_compose_smoke.py` | test | test | kandidat_relevant | Integration-Tests: Docker Compose Smoke-Tests |
| `backoffice/services/query_service/test_service.py` | test | test | unklar | Service-Test für query_service (Service nicht in docker-compose.yml!) |

## Zusammenfassung

### Nach Typ

| Typ | Anzahl | Kandidat_Relevant | Legacy/Unklar |
|-----|--------|-------------------|---------------|
| compose | 2 | 1 | 1 |
| dockerfile | 7 | 4 | 2 |
| config | 1 | 1 | 0 |
| env | 1 | 1 | 0 |
| script | 1 | 1 | 0 |
| test | 3 | 2 | 1 |
| **TOTAL** | **15** | **10** | **4** |

### Nach Rolle

| Rolle | Anzahl |
|-------|--------|
| runtime | 5 |
| infra | 3 |
| monitoring | 1 |
| deployment | 1 |
| test | 5 |

### Kritische Findings

1. **Duplikate**: `Dockerfile - Kopie`, `Dockerfile - Kopie.test` sind potenzielle Legacy-Files
2. **compose.yml vs. docker-compose.yml**: Unklar, ob beide aktiv genutzt werden
3. **query_service**: Test vorhanden, aber Service nicht in docker-compose.yml definiert
4. **Secrets in ENV**: ` - Kopie.env` enthält aktuell echte Secrets (POSTGRES_PASSWORD) - MUSS bereinigt werden vor Commit!
