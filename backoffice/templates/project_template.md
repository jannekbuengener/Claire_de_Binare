# Event-Driven Trading System - Project Template

**Version**: 1.0
**Basiert auf**: Claire de Binaire Architecture (abstr ahiert)
**Zielgruppe**: Neue Event-Driven Trading/Financial Systems

---

## Verwendung

Dieses Template bietet Leitplanken für ereignisgesteuerte Trading-Systeme mit Risikomanagement. Ersetze Platzhalter (`{{VARIABLE}}`) mit projektspezifischen Werten.

---

## 1. System-Architektur-Entscheidungen

### 1.1 Messaging-Pattern

**PFLICHT**: Event-Driven Architecture via Message Broker (Pub/Sub)

**Empfohlener Stack**:
- **Message Broker**: Redis Pub/Sub (leichtgewichtig) ODER RabbitMQ/Kafka (hochvolumig)
- **Event-Schema**: JSON Schema als Single Source of Truth
- **Topics-Naming**: `{domain}_{action}` (z.B. `market_data`, `signals`, `orders`)

**Event-Flow-Pattern**:
```
Input-Events → Processing-Service → Output-Events → Execution/Storage
             ↘ Alerts-Topic
```

**Infra-/Runtime-Blueprint**: Siehe [infra_templates.md](./infra_templates.md) für:
- Standard-Dockerfile-Pattern (Non-Root, Health-Checks, Security-Hardening)
- docker-compose-Service-Template (vollständiges Hardening)
- .env.template-Struktur (Dezimal-Konvention, Secret-Management)
- Test-Setup-Template (pytest, Fixtures, Integration-Tests)
- Prometheus-Scrape-Config

**Secret-Management**:
- Alle Secrets in `.env` (gitignored)
- `.env.template` mit Platzhaltern (`<SET_IN_ENV>`) committed
- Passwort-Rotation: Manuelle Änderung + Container-Restart

**Deployment**:
- Production: `docker-compose.yml` (Code eingebrannt, keine Mounts)
- Development: `docker-compose.override.yml` (Code-Mounts für Hot-Reload)

### 1.2 Core Services (Minimum Viable)

| Service-Typ | Funktion | Health-Endpoint | Metrics |
|-------------|----------|-----------------|---------|
| **Data Ingestion** | Externe Datenquellen → `input_topic` | `/health` | Optional |
| **Signal Generator** | `input_topic` → Handelssignale → `signals_topic` | `/health` | Pflicht |
| **Risk Manager** | `signals_topic` → Risk-Checks → `orders_topic` | `/health` | Pflicht |
| **Execution Engine** | `orders_topic` → Order-Platzierung → `results_topic` | `/health` | Pflicht |

**Platzhalter**:
- `{{PROJECT_NAME}}`: z.B. "claire_de_binaire" → Container-Präfix `cdb_`
- `{{EXCHANGE_API}}`: z.B. "MEXC", "Binance", "Interactive Brokers"

### 1.3 Infrastructure Services (Pflicht)

| Service | Funktion | Alternativen |
|---------|----------|--------------|
| Message Broker | Pub/Sub | Redis, RabbitMQ, Kafka |
| Database | Persistenz (Orders, Trades, Risk-Events) | PostgreSQL, TimescaleDB |
| Metrics | Observability | Prometheus + Grafana |
| Logging | Strukturierte Logs | ELK Stack, Loki |

---

## 2. Risk-Engine-Patterns

### 2.1 Pflicht-Schutzschichten (priorisiert)

| Priorität | Check-Typ | ENV-Variable-Pattern | Beispiel-Default | Aktion |
|-----------|-----------|----------------------|------------------|--------|
| 1 | Daily/Period Drawdown | `MAX_{{PERIOD}}_DRAWDOWN_PCT` | 0.05 (5%) | Trading-Stopp |
| 2 | Market Anomalies | `MAX_SLIPPAGE_PCT`, `MAX_SPREAD_MULT` | 0.01, 5.0 | Circuit Breaker |
| 3 | Data Staleness | `DATA_STALE_TIMEOUT_SEC` | 30 | Pause New Orders |
| 4 | Portfolio Exposure | `MAX_EXPOSURE_PCT` | 0.50 (50%) | Block New Orders |
| 5 | Position Size | `MAX_POSITION_PCT` | 0.10 (10%) | Trim or Reject |
| 6 | Per-Trade Stop-Loss | `STOP_LOSS_PCT` | 0.02 (2%) | Auto-Exit |

**Decision-Logic-Template**:
```python
def on_signal(signal):
    # Layer 1: Drawdown Check
    if exceeds_drawdown():
        halt_trading()
        emit_alert("CRITICAL", "DRAWDOWN_LIMIT")
        return Reject("drawdown")

    # Layer 2: Market Anomalies
    if abnormal_market():
        pause_trading()
        emit_alert("WARNING", "CIRCUIT_BREAKER")
        return Reject("market_anomaly")

    # Layer 3: Data Staleness (CHECK before processing)
    if data_is_stale():
        pause_trading()
        emit_alert("WARNING", "DATA_STALE")
        return Reject("stale_data")

    # Layer 4: Exposure Limit
    if portfolio_exposure() >= MAX_EXPOSURE:
        emit_alert("INFO", "EXPOSURE_LIMIT")
        return Reject("exposure")

    # Layer 5: Position Sizing
    allowed_size = min(signal.size, calculate_max_position())
    if allowed_size < signal.size:
        return Approve(size=allowed_size, trimmed=True)

    return Approve(size=signal.size)
```

### 2.2 Alert-Codes (standardisiert)

| Code | Level | Use-Case | Beispiel-Message |
|------|-------|----------|------------------|
| `RISK_LIMIT` | CRITICAL | Hard limits (Drawdown, Exposure >threshold) | "Daily drawdown exceeded: 5.2%" |
| `RISK_LIMIT` | WARNING | Soft limits (Stop-Loss, Trimming) | "Position trimmed: {{SYMBOL}} {{OLD_SIZE}} → {{NEW_SIZE}}" |
| `CIRCUIT_BREAKER` | WARNING | Market anomalies | "High slippage detected: {{PCT}}%" |
| `DATA_STALE` | WARNING | Missing/delayed data | "No data for {{SECONDS}}s" |

---

## 3. Service-Development-Standards

### 3.1 Pflicht-Struktur (jeder Service)

```
{{service_name}}/
├── __init__.py
├── service.py          # Main logic (start, shutdown, event-handlers)
├── models.py           # Data models (Pydantic/dataclass)
├── config.py           # ENV loading + validation
├── Dockerfile          # Multi-stage build, security-hardened
├── README.md           # Service-specific documentation
└── tests/              # Unit + integration tests
    ├── __init__.py
    ├── test_service.py
    └── test_models.py
```

### 3.2 Pflicht-Features (jeder Service)

1. **Health-Endpoint**: `/health` → `{"status": "ok"}` (HTTP 200)
2. **Structured Logging**: JSON format (timestamp, level, message, context)
3. **Graceful Shutdown**: SIGTERM handler, cleanup resources
4. **ENV Validation**: Fail-fast on missing required vars
5. **Metrics** (empfohlen): `/metrics` in Prometheus format

### 3.3 Code-Skeleton (Python-Beispiel)

Siehe separate Datei: `templates/service_skeleton.py` (nicht inline wiederholen - siehe Konflikt-Doku).

**Mindest-Anforderungen**:
- Type annotations
- Docstrings (Google/NumPy style)
- Logger via `logging` (kein `print()`)
- Config-Klasse (dataclass/Pydantic)

---

## 4. Configuration Management

### 4.1 ENV-Variablen-Naming

**Pattern**: `{{PROJECT_PREFIX}}_{{CATEGORY}}_{{NAME}}`

**Beispiel**: `CDB_RISK_MAX_POSITION_PCT`

**Kategorien**:
- `RISK_*`: Risk-Engine-Parameter
- `SIGNAL_*`: Signal-Generator-Konfiguration
- `EXEC_*`: Execution-Engine-Konfiguration
- `INFRA_*`: Infrastruktur (Redis, DB)

**Secrets-Naming**: `{{SERVICE}}_{{TYPE}}` (z.B. `REDIS_PASSWORD`, `POSTGRES_USER`)

### 4.2 Required ENV-Variables (Template)

```bash
# Secrets (NEVER commit)
REDIS_PASSWORD={{GENERATE}}
POSTGRES_USER={{GENERATE}}
POSTGRES_PASSWORD={{GENERATE}}
{{EXCHANGE}}_API_KEY={{GENERATE}}
{{EXCHANGE}}_API_SECRET={{GENERATE}}

# Risk Parameters (Decimal format, 0.10 = 10%)
MAX_POSITION_PCT=0.10           # Min: 0.01, Max: 0.25
MAX_EXPOSURE_PCT=0.50           # Min: 0.10, Max: 1.00
MAX_DAILY_DRAWDOWN_PCT=0.05     # Min: 0.01, Max: 0.20
STOP_LOSS_PCT=0.02              # Min: 0.005, Max: 0.10

# Market Anomalies
MAX_SLIPPAGE_PCT=0.01           # Min: 0.001, Max: 0.05
MAX_SPREAD_MULTIPLIER=5.0       # Min: 2.0, Max: 10.0

# Operational
DATA_STALE_TIMEOUT_SEC=30       # Min: 10, Max: 120
```

### 4.3 Validation-Strategie

**Startup-Check** (config.py):
1. Pflicht-Variablen vorhanden? → Nein: EXIT 1
2. Werte in erlaubtem Range? → Nein: WARN + Fallback auf Default
3. Secrets-Format korrekt? → Nein: EXIT 1 (kein Retry bei Config-Fehlern)

---

## 5. Deployment & Operations

### 5.1 Docker-Compose-Pattern

```yaml
services:
  {{service_name}}:
    container_name: {{prefix}}_{{service}}
    build: ./{{service_path}}
    env_file: .env
    ports:
      - "{{HOST_PORT}}:{{CONTAINER_PORT}}"
    depends_on:
      - {{broker_service}}
      - {{db_service}}
    healthcheck:
      test: ["CMD", "curl", "-fsS", "http://localhost:{{PORT}}/health"]
      interval: 30s
      timeout: 3s
      retries: 3
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    tmpfs:
      - /tmp
    read_only: true  # Wo möglich
    restart: unless-stopped
    networks:
      - {{project}}_network
```

**Security Hardening** (Pflicht):
- `no-new-privileges`, `cap_drop: ALL`
- `read_only` + `tmpfs` für /tmp
- Keine Root-User (USER 1000:1000 im Dockerfile)

### 5.2 Health-Check-Strategie

**Pattern**: `curl -fsS http://localhost:PORT/health`

**Response**: HTTP 200, JSON `{"status": "ok", "service": "{{NAME}}", "timestamp": "{{ISO8601}}"}`

**Startup-Delay**: 10-15 Sekunden nach `docker compose up` warten.

### 5.3 Monitoring-Stack

| Tool | Port | Funktion | Config |
|------|------|----------|--------|
| Prometheus | 19090:9090 | Metrics scraping (15s interval) | `prometheus.yml` |
| Grafana | 3000:3000 | Visualization | Datasource: Prometheus |
| Alert-Manager (optional) | 9093:9093 | Alert routing | `alertmanager.yml` |

---

## 6. Development-Workflow (Leitplanken)

### 6.1 Philosophie

**"Documentation before Code"** - Architektur-Änderungen erst dokumentieren, dann implementieren.

**Kernprinzipien**:
1. **Inkrementell**: Kleine, validierte Schritte statt Big-Bang
2. **Review-Pflicht**: Checkliste vor jedem Merge
3. **Single Source of Truth**: Event-Schema, docker-compose.yml, ENV-Docs
4. **Fehlerkultur**: Incident Reports mit Root Cause + Prevention

### 6.2 Review-Checkliste (Template)

- [ ] Tests laufen (Unit + Integration)
- [ ] `docker compose config --quiet` (keine Fehler)
- [ ] ENV-Validierung (keine Duplikate, alle Pflicht-Variablen)
- [ ] Ports/Topics mit Architektur-Doku abgeglichen
- [ ] ADR erstellt (bei Architektur-Entscheidung)
- [ ] Health-Endpoints funktionieren
- [ ] Logs strukturiert (JSON, kein `print()`)

### 6.3 Branching & Commits

- **Branches**: `feature/*`, `bugfix/*`, `docs/*`, `hotfix/*`
- **Commits**: Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`)

---

## 7. Troubleshooting-Runbook (Pattern)

```bash
# Container crasht
docker compose logs {{service_name}}

# DB-Verbindung prüfen
docker exec {{db_container}} pg_isready -U {{USER}}

# Message-Broker prüfen
docker exec {{broker_container}} redis-cli -a {{PWD}} ping

# Event-Flow debuggen
docker exec {{broker_container}} redis-cli -a {{PWD}} SUBSCRIBE {{topic}}

# Rollback
docker compose down
git checkout {{previous_version}}
docker compose up -d --build
```

---

## 8. Konflikte & TODOs (aus Extraktion)

### Bekannte Konflikte (dokumentieren für neue Projekte)

1. **Service-Naming**: Entscheide EINMAL zwischen technischem Namen (z.B. `core`) und funktionalem Namen (z.B. `signal_engine`). Nicht mischen.
2. **ENV-Präfixe**: Entweder ALLE Variablen mit Projektpräfix (`{{PREFIX}}_*`) ODER keine. Inkonsistenz vermeiden.
3. **Timeout-Suffixe**: Wenn Einheiten in Variablen, dann für ALLE Timeouts (`_SEC`, `_MS`). Oder für keine.

### TODOs (optional, je nach Projekt)

- [ ] Alert-Manager-Integration für CRITICAL-Alerts
- [ ] Admin-Tools für manuelles Risk-Override (z.B. Drawdown-Reset)
- [ ] Minimum Order Size Validation
- [ ] Prometheus-Alerting-Rules definieren

---

## 9. Quellen-Referenzen (Basis-Projekt)

- `ARCHITEKTUR.md`: System-Architektur, Event-Flow
- `Risikomanagement-Logik.md`: Risk-Engine-Logik, Schutzschichten
- `SERVICE_TEMPLATE.md`: Code-Patterns, Struktur
- `DEVELOPMENT.md`: Workflow, Qualität
- `docker-compose.yml`: Deployment, Security
- `copilot-instructions.md`: Entwicklungs-Leitplanken

**Pipeline**: Extrahiert via Multi-Agenten-Pipeline 2 (claire-architect, software-jochen, agata-van-data, devops-infrastructure-architect, claire-risk-engine-guardian)

---

**Version History**:
- v1.0 (2025-11-14): Initiale Template-Generierung aus Claire de Binaire

**Next Steps**: Template in neuem Projekt anwenden, Platzhalter ersetzen, projektspezifische Anpassungen dokumentieren.
