# Agent: compose_auditor
# Scan Date: 2025-12-28
# Scope: Compose/Runtime Konfiguration

---

## Facts (verifiziert)

### Compose Layer Architektur
```
base.yml          -> Infrastruktur (Redis, Postgres, Prometheus, Grafana)
  |
dev.yml           -> Applikations-Services + Port-Bindings
  |
logging.yml       -> Loki + Promtail (optional)
  |
tls.yml           -> TLS Certificates (optional)
  |
healthchecks-strict.yml -> Strikte Health Checks (optional)
  |
network-prod.yml  -> Production Network Isolation (optional)
```

### AKTIVE Services (SOLL = IST)

| Container | Image/Build | Port | Healthcheck |
|-----------|-------------|------|-------------|
| cdb_redis | redis:7-alpine | 127.0.0.1:6379 | redis-cli ping |
| cdb_postgres | postgres:15-alpine | 127.0.0.1:5432 | pg_isready |
| cdb_prometheus | prom/prometheus:v2.51.0 | 127.0.0.1:19090 | wget healthy |
| cdb_grafana | grafana/grafana:11.4.0 | 127.0.0.1:3000 | curl /api/health |
| cdb_ws | build: services/ws/ | 127.0.0.1:8000 | curl /health |
| cdb_signal | build: services/signal/ | 127.0.0.1:8005 | curl /health |
| cdb_risk | build: services/risk/ | 127.0.0.1:8002 | (none) |
| cdb_execution | build: services/execution/ | 127.0.0.1:8003 | (none) |
| cdb_db_writer | build: services/db_writer/ | - | kill -0 1 |
| cdb_paper_runner | build: tools/paper_trading/ | 127.0.0.1:8004 | curl /health |

### OPTIONALE Services (Logging Stack)

| Container | Image | Aktivierung |
|-----------|-------|-------------|
| cdb_loki | grafana/loki:2.9.3 | logging.yml |
| cdb_promtail | grafana/promtail:2.9.3 | logging.yml |

### DEAKTIVIERTE Services (in dev.yml auskommentiert)

| Container | Grund | Code vorhanden |
|-----------|-------|----------------|
| cdb_allocation | Fehlende Env-Vars (ALLOCATION_*) | Ja (378 LOC) |
| cdb_regime | Fehlende Env-Vars (REGIME_*) | Ja (213 LOC) |
| cdb_market | "not implemented" (laut Kommentar) | Ja (82 LOC) |

### Stack Startup Scripts

| Script | Zweck |
|--------|-------|
| `infrastructure/scripts/stack_up.ps1` | Stack starten mit Overlay-Optionen |
| `infrastructure/scripts/stack_verify.ps1` | Automatische Vollstaendigkeitspruefung |

### Stack-Start Parameter (stack_up.ps1)
- `-Rebuild` : Mit --build
- `-Profile dev|prod` : Profil-Auswahl
- `-Logging` : Loki + Promtail aktivieren
- `-StrictHealth` : Strikte Healthchecks
- `-NetworkIsolation` : network-prod.yml
- `-TLS` : TLS fuer Redis + PostgreSQL

---

## Assumptions (zu validieren)

1. **Prod Overlay**: prod.yml definiert Resource Limits und Security Options, aber:
   - Referenziert `cdb_core` statt `cdb_signal` (DRIFT!)
   - Keine Port-Bindings (internal only)

2. **TLS Overlay**: tls.yml referenziert ebenfalls `cdb_core` statt `cdb_signal` (DRIFT!)

3. **Network**: Alle Services nutzen `cdb_network` (Bridge Driver)

---

## Gaps (identifiziert)

1. **prod.yml/tls.yml Naming Drift**: Diese Dateien verwenden noch `cdb_core`, obwohl der Service jetzt `cdb_signal` heisst
   - **Action Required**: Umbenennung in prod.yml und tls.yml

2. **Healthchecks fehlen**: cdb_risk und cdb_execution haben keine expliziten Healthchecks in dev.yml
   - Nur in healthchecks-strict.yml definiert

3. **Port Inconsistency**: CLAUDE.md listet Signal auf Port 8001, tatsaechlich Port 8005

---

## Source Pointers

- `D:\Dev\Workspaces\Repos\Claire_de_Binare\infrastructure\compose\base.yml`
- `D:\Dev\Workspaces\Repos\Claire_de_Binare\infrastructure\compose\dev.yml`
- `D:\Dev\Workspaces\Repos\Claire_de_Binare\infrastructure\compose\prod.yml`
- `D:\Dev\Workspaces\Repos\Claire_de_Binare\infrastructure\compose\tls.yml`
- `D:\Dev\Workspaces\Repos\Claire_de_Binare\infrastructure\compose\logging.yml`
- `D:\Dev\Workspaces\Repos\Claire_de_Binare\infrastructure\scripts\stack_up.ps1`
- `D:\Dev\Workspaces\Repos\Claire_de_Binare\infrastructure\scripts\stack_verify.ps1`
