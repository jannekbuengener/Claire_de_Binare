# Infra-Knowledge - Strukturierte Service-Extraktion

**Erstellt von**: software-jochen
**Datum**: 2025-11-16
**Quelle**: docker-compose.yml, prometheus.yml
**Sicherheits-Referenz**: Siehe sandbox/output.md (Security-Risk-Register SR-001…), falls vorhanden

## Services (docker-compose.yml)

### cdb_redis (Message Bus)

| Attribut | Wert |
|----------|------|
| **Image** | `redis:7-alpine` |
| **Container-Name** | `cdb_redis` |
| **Ports (Host→Container)** | `6379→6379` |
| **Volumes** | `redis_data:/data` |
| **Netzwerk** | `cdb_network` |
| **Restart-Policy** | `unless-stopped` |
| **Health-Check** | `redis-cli -a ${REDIS_PASSWORD} ping` (Intervall: 10s, Timeout: 3s, Retries: 3) |
| **ENV-Variablen** | `REDIS_PASSWORD` (Pflicht, `?`-Check) |
| **Command** | `redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru --requirepass $$REDIS_PASSWORD` |
| **Security-Flags** | ❌ Keine (standard Redis-Image) |

**Besonderheiten**:
- `--requirepass`: Auth **Pflicht**
- `--maxmemory 256mb`: Memory-Limit hardcoded
- `--maxmemory-policy allkeys-lru`: Eviction-Policy LRU
- `--appendonly yes`: Persistenz aktiviert

### cdb_postgres (Database)

| Attribut | Wert |
|----------|------|
| **Image** | `postgres:15-alpine` |
| **Container-Name** | `cdb_postgres` |
| **Ports (Host→Container)** | `5432→5432` |
| **Volumes** | `postgres_data:/var/lib/postgresql/data`, `./backoffice/docs/DATABASE_SCHEMA.sql:/docker-entrypoint-initdb.d/01-schema.sql:ro` |
| **Netzwerk** | `cdb_network` |
| **Restart-Policy** | `unless-stopped` |
| **Health-Check** | `pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}` (Intervall: 10s, Timeout: 3s, Retries: 3) |
| **ENV-Variablen** | `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` (alle Pflicht, `?`-Check) |
| **Security-Flags** | ❌ Keine |

**Besonderheiten**:
- Schema-Init via `/docker-entrypoint-initdb.d/01-schema.sql` (read-only mount)
- DB-Name: `claire_de_binare` (ohne `database_`-Präfix)

### cdb_prometheus (Monitoring)

| Attribut | Wert |
|----------|------|
| **Image** | `prom/prometheus:latest` |
| **Container-Name** | `cdb_prometheus` |
| **Ports (Host→Container)** | `19090→9090` |
| **Volumes** | `./prometheus.yml:/etc/prometheus/prometheus.yml:ro`, `prom_data:/prometheus` |
| **Netzwerk** | `cdb_network` |
| **Restart-Policy** | `unless-stopped` |
| **Health-Check** | `wget -qO- http://localhost:9090/-/healthy` (Intervall: 30s, Timeout: 10s, Retries: 3) |
| **Command** | `--config.file=/etc/prometheus/prometheus.yml --storage.tsdb.path=/prometheus` |
| **Security-Flags** | ❌ Keine |

**Besonderheiten**:
- Host-Port `19090` → Container-Port `9090` (nicht Standard-9090 auf Host wegen Konflikt-Vermeidung?)
- Scrape-Intervall: 15s (aus prometheus.yml)
- Scrape-Jobs: `prometheus`, `execution_service`, `signal_engine`, `risk_manager`

### cdb_grafana (Visualisierung)

| Attribut | Wert |
|----------|------|
| **Image** | `grafana/grafana:latest` |
| **Container-Name** | `cdb_grafana` |
| **Ports (Host→Container)** | `3000→3000` |
| **Volumes** | `grafana_data:/var/lib/grafana` |
| **Netzwerk** | `cdb_network` |
| **Restart-Policy** | `unless-stopped` |
| **Health-Check** | `curl -fsS http://localhost:3000/api/health` (Intervall: 30s, Timeout: 10s, Retries: 3) |
| **ENV-Variablen** | `GF_SECURITY_ADMIN_USER=admin`, `GF_SECURITY_ADMIN_PASSWORD` (Pflicht, `?`-Check), `GF_USERS_ALLOW_SIGN_UP=false` |
| **Depends-On** | `cdb_prometheus` |
| **Security-Flags** | ❌ Keine |

**Besonderheiten**:
- User-Registrierung deaktiviert (`ALLOW_SIGN_UP=false`)
- Admin-User hardcoded als `admin`

### cdb_ws (WebSocket Screener)

| Attribut | Wert |
|----------|------|
| **Build-Context** | `.` (Root) |
| **Dockerfile** | `Dockerfile` (mit ARG `SCRIPT_NAME=mexc_top5_ws.py`) |
| **Container-Name** | `cdb_ws` |
| **Ports (Host→Container)** | `8000→8000` |
| **Volumes** | `./logs:/app/logs` |
| **Netzwerk** | `cdb_network` |
| **Restart-Policy** | `unless-stopped` |
| **Health-Check** | `curl -fsS http://localhost:8000/health` (Intervall: 30s, Timeout: 5s, Retries: 3) |
| **ENV-File** | `.env` |
| **Depends-On** | `cdb_redis` |
| **Security-Flags** | ✅ `no-new-privileges:true`, `cap_drop: ALL`, `tmpfs: /tmp`, `read_only: true` |

**Besonderheiten**:
- Nutzt generisches Dockerfile mit ARG für Script-Name
- **Hardening**: Read-only FS, keine Capabilities, non-root (implizit via tmpfs)

### cdb_rest (REST Screener)

| Attribut | Wert |
|----------|------|
| **Build-Context** | `.` (Root) |
| **Dockerfile** | `Dockerfile` (mit ARG `SCRIPT_NAME=mexc_top_movers.py`) |
| **Container-Name** | `cdb_rest` |
| **Ports (Host→Container)** | `8080→8080` |
| **Volumes** | `./logs:/app/logs` |
| **Netzwerk** | `cdb_network` |
| **Restart-Policy** | `unless-stopped` |
| **Health-Check** | `true` (Override: kein HTTP-Server, läuft in Loop) |
| **Command** | Periodic Loop: `python app.py; sleep 300` (5min Intervall) |
| **ENV-File** | `.env` |
| **Depends-On** | `cdb_redis` |
| **Security-Flags** | ✅ `no-new-privileges:true`, `cap_drop: ALL`, `tmpfs: /tmp` (kein `read_only`) |

**Besonderheiten**:
- Health-Check überschrieben auf `true` (kein echter Check, da kein HTTP-Server)
- Läuft als periodischer Job, nicht als Daemon
- **Kein read-only FS** (im Gegensatz zu cdb_ws)

### cdb_core (Signal Engine)

| Attribut | Wert |
|----------|------|
| **Build-Context** | `./backoffice/services/signal_engine` |
| **Dockerfile** | `./backoffice/services/signal_engine/Dockerfile` |
| **Container-Name** | `cdb_core` |
| **Ports (Host→Container)** | `8001→8001` |
| **Volumes** | `./backoffice/services/signal_engine:/app`, `signal_data:/data` |
| **Netzwerk** | `cdb_network` (Alias: `signal_engine`) |
| **Restart-Policy** | `unless-stopped` |
| **Health-Check** | `curl -fsS http://localhost:8001/health` (Intervall: 30s, Timeout: 3s, Retries: 3) |
| **ENV-File** | `.env` |
| **Depends-On** | `cdb_redis`, `cdb_ws` |
| **Security-Flags** | ✅ `no-new-privileges:true`, `cap_drop: ALL`, `tmpfs: /tmp`, `read_only: true` |

**Besonderheiten**:
- Volume-Mount: Source-Code gemountet (`./backoffice/services/signal_engine:/app`) → **Development-Mode**
- Netzwerk-Alias: `signal_engine` (für prometheus.yml Scraping)

### cdb_risk (Risk Manager)

| Attribut | Wert |
|----------|------|
| **Build-Context** | `./backoffice/services/risk_manager` |
| **Dockerfile** | `./backoffice/services/risk_manager/Dockerfile` |
| **Container-Name** | `cdb_risk` |
| **Ports (Host→Container)** | `8002→8002` |
| **Volumes** | `./backoffice/services/risk_manager:/app`, `risk_logs:/logs` |
| **Netzwerk** | `cdb_network` (Alias: `risk_manager`) |
| **Restart-Policy** | `unless-stopped` |
| **Health-Check** | `curl -fsS http://localhost:8002/health` (Intervall: 30s, Timeout: 3s, Retries: 3) |
| **ENV-File** | `.env` |
| **Depends-On** | `cdb_redis`, `cdb_core` |
| **Security-Flags** | ✅ `no-new-privileges:true`, `cap_drop: ALL`, `tmpfs: /tmp`, `read_only: true` |

**Besonderheiten**:
- Volume-Mount: Source-Code gemountet → **Development-Mode**
- Separates Volume für Logs (`risk_logs:/logs`)

### cdb_execution (Execution Service)

| Attribut | Wert |
|----------|------|
| **Build-Context** | `./backoffice/services/execution_service` |
| **Dockerfile** | `./backoffice/services/execution_service/Dockerfile` |
| **Container-Name** | `cdb_execution` |
| **Ports (Host→Container)** | `8003→8003` |
| **Volumes** | `./backoffice/services/execution_service:/app` |
| **Netzwerk** | `cdb_network` (Alias: `execution_service`) |
| **Restart-Policy** | `unless-stopped` |
| **Health-Check** | `curl -fsS http://localhost:8003/health` (Intervall: 30s, Timeout: 3s, Retries: 3) |
| **User** | `1000:1000` (Non-root) |
| **ENV-File** | `.env` |
| **Depends-On** | `cdb_redis`, `cdb_risk`, `cdb_postgres` |
| **Security-Flags** | ✅ `no-new-privileges:true`, `cap_drop: ALL`, `tmpfs: /tmp`, `read_only: true` |

**Besonderheiten**:
- **Expliziter User**: `1000:1000` (Non-root erzwungen)
- Volume-Mount: Source-Code gemountet → **Development-Mode**
- Abhängig von PostgreSQL (persistiert Order-Results)

### cdb_signal_gen (Signal Generator?)

| Attribut | Wert |
|----------|------|
| **Build-Context** | `.` (Root) |
| **Dockerfile** | `Dockerfile.signal_gen` |
| **Container-Name** | `cdb_signal_gen` |
| **Ports** | ❌ Keine |
| **Netzwerk** | `cdb_network` |
| **Restart-Policy** | `unless-stopped` |
| **ENV-Variablen** | `REDIS_HOST=cdb_redis`, `REDIS_PORT=6379`, `REDIS_PASSWORD`, `REDIS_DB=0` |
| **Depends-On** | `cdb_redis` |
| **Security-Flags** | ❌ Keine |

**Besonderheiten**:
- Kein Health-Check definiert
- Keine Ports exponiert
- Dockerfile.signal_gen nicht gefunden in File-Index → **Potenziell Legacy/Gelöscht?**
- **⚠️ UNKLAR**: Rolle dieses Services (duplicate zu cdb_core?)

## Netzwerke

| Name | Driver | Verwendung |
|------|--------|------------|
| `cdb_network` | `bridge` | Alle Services |

**Service-Aliases** (für interne DNS-Auflösung):
- `signal_engine` → `cdb_core:8001`
- `risk_manager` → `cdb_risk:8002`
- `execution_service` → `cdb_execution:8003`

## Volumes (Persistent)

| Name | Driver | Verwendung |
|------|--------|------------|
| `redis_data` | `local` | Redis AOF-Daten |
| `postgres_data` | `local` | PostgreSQL-Datenbank |
| `prom_data` | `local` | Prometheus TSDB |
| `grafana_data` | `local` | Grafana-Dashboards/-Config |
| `signal_data` | `local` | Signal Engine Daten |
| `risk_logs` | `local` | Risk Manager Logs |

## ENV-Variablen → Service-Mapping

| ENV-Variable | Services |
|--------------|----------|
| `REDIS_PASSWORD` | `cdb_redis` (Server), `cdb_signal_gen` (Client), implizit alle anderen via `.env` |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | `cdb_postgres`, `cdb_execution` (Client via `DATABASE_URL`) |
| `GRAFANA_PASSWORD` (alias `GF_SECURITY_ADMIN_PASSWORD`) | `cdb_grafana` |
| `WS_PORT`, `SIGNAL_PORT`, `RISK_PORT`, `EXEC_PORT` | Wahrscheinlich in `.env` für Services, aber **nicht in docker-compose.yml referenziert** (Ports hardcoded) |

## Security-Hardening Übersicht

| Service | no-new-privileges | cap_drop: ALL | tmpfs | read_only | Explicit User |
|---------|-------------------|---------------|-------|-----------|---------------|
| `cdb_redis` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `cdb_postgres` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `cdb_prometheus` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `cdb_grafana` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `cdb_ws` | ✅ | ✅ | ✅ | ✅ | ❌ |
| `cdb_rest` | ✅ | ✅ | ✅ | ❌ | ❌ |
| `cdb_core` | ✅ | ✅ | ✅ | ✅ | ❌ |
| `cdb_risk` | ✅ | ✅ | ✅ | ✅ | ❌ |
| `cdb_execution` | ✅ | ✅ | ✅ | ✅ | ✅ (1000:1000) |
| `cdb_signal_gen` | ❌ | ❌ | ❌ | ❌ | ❌ |

**Analyse**:
- **MVP-Services** (`cdb_ws`, `cdb_core`, `cdb_risk`, `cdb_execution`): Vollständiges Hardening
- **cdb_rest**: Fast vollständig, aber **kein read_only** (warum?)
- **Infra-Services** (`redis`, `postgres`, `prometheus`, `grafana`): **Kein Hardening** (Standard-Images)
- **cdb_signal_gen**: Kein Hardening (Legacy?)

## Prometheus Scrape-Konfiguration

**Quelle**: prometheus.yml

| Job | Target | Metrics-Path | Labels |
|-----|--------|--------------|--------|
| `prometheus` | `localhost:9090` | `/metrics` | `instance=prometheus, service=monitoring` |
| `execution_service` | `execution_service:8003` | `/metrics` | `instance=execution_service, service=trading` |
| `signal_engine` | `signal_engine:8001` | `/metrics` | `instance=signal_engine, service=analysis` |
| `risk_manager` | `risk_manager:8002` | `/metrics` | `instance=risk_manager, service=risk` |

**Scrape-Intervall**: 15s (global)

**Fehlende Services**: `cdb_ws`, `cdb_rest` haben keine `/metrics` Endpoints in prometheus.yml konfiguriert.

## Kritische Findings

1. **cdb_signal_gen**: Service in docker-compose.yml, aber Dockerfile.signal_gen fehlt im File-Index → **Build wird fehlschlagen**!
2. **Hardening-Inkonsistenz**: Infra-Services (Redis, Postgres, Prometheus, Grafana) haben **kein Security-Hardening** → **Potenzielles Risiko**
3. **read_only FS**: cdb_rest hat **kein** `read_only: true`, alle anderen MVP-Services schon → **Inkonsistenz**
4. **Development-Mounts**: cdb_core, cdb_risk, cdb_execution mounten Source-Code als Volume → **Nicht produktionsreif** (Code-Changes ohne Rebuild)
5. **Port-ENV-Mismatch**: Service-Ports in docker-compose.yml hardcoded, aber ENV-Variablen (`WS_PORT`, etc.) in ` - Kopie.env` → **Werden nicht genutzt?**
6. **Health-Check-Lücke**: cdb_signal_gen hat **keinen** Health-Check
7. **cdb_rest Health-Check**: Override auf `true` → **Kein echter Health-Status**
