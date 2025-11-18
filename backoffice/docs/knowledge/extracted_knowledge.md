# Konsolidiertes Wissen - Claire de Binaire

**Extrahiert von**: software-jochen
**Datum**: 2025-11-14
**Quellen**: ARCHITEKTUR.md, Risikomanagement-Logik.md, SERVICE_TEMPLATE.md, DEVELOPMENT.md, docker-compose.yml, copilot-instructions.md

---

## 1. Systemarchitektur

### 1.1 Core Services

| Service | Container-Name | Port (Host:Container) | Funktion | Health-Endpoint |
|---------|----------------|----------------------|----------|-----------------|
| Bot WS Screener | `cdb_ws` | 8000:8000 | Marktdaten-Ingestion (WebSocket) | `/health` |
| Bot REST Screener | `cdb_rest` | 8080:8080 | Marktdaten-Ingestion (REST/Polling) | `/health` |
| Signal Engine | `cdb_core` | 8001:8001 | Momentum-Signal-Generierung | `/health`, `/metrics` |
| Risk Manager | `cdb_risk` | 8002:8002 | Mehrlagiges Risikomanagement | `/health`, `/metrics` |
| Execution Service | `cdb_execution` | 8003:8003 | Order-Ausführung (Paper Trading) | `/health`, `/metrics` |

### 1.2 Infrastructure Services

| Service | Container-Name | Port (Host:Container) | Funktion |
|---------|----------------|----------------------|----------|
| Redis | `cdb_redis` | 6379:6379 | Message Broker (Pub/Sub) |
| PostgreSQL | `cdb_postgres` | 5432:5432 | Persistenz (Orders, Trades, Risk Events) |
| Prometheus | `cdb_prometheus` | 19090:9090 | Metrics Collection (Scrape: 15s) |
| Grafana | `cdb_grafana` | 3000:3000 | Visualization & Dashboards |

**Port-Mapping-Regel**: Prometheus Host-Port 19090 → Container-Port 9090 (Standard).

### 1.3 Event-Flow (Pub/Sub Topics)

```
market_data → signals → orders → order_results
                             ↘
                              alerts
```

| Topic | Producer | Consumer | Payload-Elemente | Schema-Quelle |
|-------|----------|----------|------------------|---------------|
| `market_data` | Bot Screener (WS/REST) | Signal Engine | `symbol`, `price`, `volume`, `timestamp`, `pct_change` | `EVENT_SCHEMA.json` |
| `signals` | Signal Engine | Risk Manager | `symbol`, `direction`, `size`, `signal_strength`, `timestamp` | `EVENT_SCHEMA.json` |
| `orders` | Risk Manager | Execution Service | `symbol`, `side`, `size`, `approved_by`, `risk_checks`, `timestamp` | `EVENT_SCHEMA.json` |
| `order_results` | Execution Service | Risk Manager, Dashboard, PostgreSQL | `order_id`, `status`, `fill_price`, `fees`, `timestamp` | `EVENT_SCHEMA.json` |
| `alerts` | Risk Manager, Execution Service | Dashboard, Logs | `code`, `level`, `message`, `timestamp` | `EVENT_SCHEMA.json` |

**Single Source of Truth**: `backoffice/docs/EVENT_SCHEMA.json`

### 1.4 Container-Konventionen

**Naming**: Alle Container mit `cdb_` Präfix (Claire de Binaire).

**Security Hardening** (docker-compose.yml):
- `security_opt: [no-new-privileges:true]`
- `cap_drop: [ALL]`
- `tmpfs: [/tmp]`
- `read_only: true` (wo möglich)
- `restart: unless-stopped`

**Networking**: Alle Services in `cdb_network` (Bridge-Driver).

**Volumes** (persistent):
- `redis_data`, `postgres_data`
- `prom_data`, `grafana_data`
- `signal_data`, `risk_logs`

---

## 2. Risk-Engine-Logik

### 2.1 Schutzschichten (Priorität absteigend)

| Priorität | Check | ENV-Variablen | Default | Aktion bei Verletzung |
|-----------|-------|---------------|---------|----------------------|
| 1 | Daily Drawdown | `MAX_DAILY_DRAWDOWN_PCT` | 0.05 (5%) | Trading-Stopp, manuelle Freigabe |
| 2 | Marktanomalien | `MAX_SLIPPAGE_PCT`, `MAX_SPREAD_MULTIPLIER` | 0.01, 5.0 | Circuit Breaker, Pause |
| 3 | Datenstille | `DATA_STALE_TIMEOUT_SEC` | 30 | Neue Orders pausieren |
| 4 | Portfolio Exposure | `MAX_EXPOSURE_PCT` | 0.50 (50%) | Neue Orders blockieren |
| 5 | Einzelposition | `MAX_POSITION_PCT` | 0.10 (10%) | Order trimmen auf Limit |
| 6 | Stop-Loss | `STOP_LOSS_PCT` | 0.02 (2%) | Automatischer Exit |

### 2.2 Alert-Codes & Levels

| Code | Level | Trigger | Aktion |
|------|-------|---------|--------|
| `RISK_LIMIT` | CRITICAL | Daily Drawdown, Exposure >80% | Trading-Stopp |
| `RISK_LIMIT` | WARNING | Stop-Loss, Position getrimmt | Alert + Log |
| `CIRCUIT_BREAKER` | WARNING | Slippage >1%, Spread >5x | Pause, Retry |
| `DATA_STALE` | WARNING | Keine Daten >30s | Pause |

### 2.3 Entscheidungslogik (Pseudocode-Pattern)

```python
def on_signal(signal):
    if exceeds_drawdown():
        emit_alert("RISK_LIMIT", "CRITICAL")
        halt_trading()
        return Reject("drawdown")

    if abnormal_market():
        emit_alert("CIRCUIT_BREAKER", "WARNING")
        pause_trading()
        return Reject("environment")

    if total_exposure() >= MAX_EXPOSURE_PCT:
        emit_alert("RISK_LIMIT", "INFO")
        return Reject("exposure")

    allowed_size = min(signal.size, max_position_size())
    if allowed_size < signal.size:
        return Approve(size=allowed_size, trimmed=True)

    return Approve(size=signal.size)
```

### 2.4 Recovery-Verhalten

- **Daily Drawdown**: Reset um 00:00 UTC, manuelle Freigabe erforderlich
- **Marktanomalien**: Auto-Retry alle 60s, max. 10 Versuche
- **Datenstille**: Auto-Wiederaufnahme bei neuem `market_data` Event

---

## 3. Service-Development-Patterns

### 3.1 Pflicht-Struktur (jeder Service)

```
service_name/
├── __init__.py
├── service.py          # Hauptlogik
├── models.py           # Datenklassen (Pydantic/dataclass)
├── config.py           # ENV-Variablen laden
├── Dockerfile
└── README.md           # Service-Doku
```

### 3.2 Pflicht-Features

1. **Health-Endpoint**: `/health` → JSON `{"status": "ok"}` (HTTP 200)
2. **Structured Logging**: JSON via `backoffice/logging_config.json` (KEIN `print()`)
3. **Graceful Shutdown**: Signal-Handler für SIGTERM
4. **ENV-Validierung**: Startup-Check, Crash bei fehlenden Pflicht-Variablen
5. **Metrics** (optional): `/metrics` in Prometheus-Format

### 3.3 Code-Skeleton (Minimal-Template)

```python
import os, logging, signal, sys
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ServiceConfig:
    env: str = os.getenv("ENV", "dev")
    # Weitere Configs...

class MyService:
    def __init__(self, config: ServiceConfig):
        self.config = config
        self._running = False

    def start(self):
        signal.signal(signal.SIGTERM, self._shutdown)
        logger.info("Service starting", extra={"env": self.config.env})
        self._running = True
        # Hauptlogik...

    def _shutdown(self, signum, frame):
        logger.warning("Shutdown signal received")
        self._running = False
        sys.exit(0)

if __name__ == "__main__":
    config = ServiceConfig()
    service = MyService(config)
    service.start()
```

---

## 4. Entwicklungs-Workflow & Qualität

### 4.1 Philosophie (aus DEVELOPMENT.md)

**Qualität vor Geschwindigkeit** - bewusst langsamer arbeiten für Stabilität.

**Kernprinzipien**:
1. **Dokumentation vor Code**: Änderungen erst dokumentieren, dann implementieren
2. **Schrittweise Umsetzung**: Keine "Big Bang"-Deployments, nach jedem Schritt validieren
3. **Ordnung als Priorität**: Keine temporären Workarounds in Produktion
4. **Mandatory Review**: Vor jedem Commit Review-Checkliste durchgehen
5. **Fehlerkultur**: Fehler sind Lernchancen, Incident Reports mit Root Cause

### 4.2 Code-Style

- Python 3.11+, PEP 8, Type-Annotations verpflichtend
- Docstrings: Google-Format
- Max. Zeilenlänge: 100 Zeichen (Code), 80 Zeichen (Markdown)
- Imports: Stdlib → Third-Party → Lokal

### 4.3 Branch & Commit

- **Branches**: `feature/*`, `bugfix/*`, `docs/*`, `hotfix/*`
- **Commits**: Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`)
- **PR**: Template aus `backoffice/audits/PR_BESCHREIBUNG.md`

### 4.4 Review-Checkliste (vor Merge)

- [ ] Tests laufen (`pytest`, Docker Health-Checks)
- [ ] `docker compose config --quiet` (keine Fehler)
- [ ] `.env` validiert (`backoffice/automation/check_env.ps1`)
- [ ] Ports/Topics/ENV mit `ARCHITEKTUR.md` abgeglichen
- [ ] ADR in `DECISION_LOG.md` (bei Architektur-Entscheidung)

---

## 5. ENV-Variablen & Configuration

### 5.1 Secrets (Pflicht, niemals committen)

- `REDIS_PASSWORD`
- `POSTGRES_USER`, `POSTGRES_PASSWORD`
- `MEXC_API_KEY`, `MEXC_API_SECRET`
- `GRAFANA_PASSWORD`

**Secret-Rotation**: Manuell, `.env` aktualisieren + Container restart.

### 5.2 Risk-Parameter (mit Ranges)

| Variable | Default | Min | Max | Format | Beschreibung |
|----------|---------|-----|-----|--------|--------------|
| `MAX_POSITION_PCT` | 0.10 | 0.01 | 0.25 | Dezimal | Positionsgröße |
| `MAX_EXPOSURE_PCT` | 0.50 | 0.10 | 1.00 | Dezimal | Gesamt-Exposure |
| `MAX_DAILY_DRAWDOWN_PCT` | 0.05 | 0.01 | 0.20 | Dezimal | Tagesverlust-Limit |
| `STOP_LOSS_PCT` | 0.02 | 0.005 | 0.10 | Dezimal | Stop-Loss pro Trade |
| `MAX_SLIPPAGE_PCT` | 0.01 | 0.001 | 0.05 | Dezimal | Slippage-Limit |
| `MAX_SPREAD_MULTIPLIER` | 5.0 | 2.0 | 10.0 | Float | Spread-Multiplikator |
| `DATA_STALE_TIMEOUT_SEC` | 30 | 10 | 120 | Integer | Datenstille-Timeout |

**Format-Regel**: Prozente als Dezimal (0.10 = 10%).

**Validierung**:
- Pflicht-Check beim Start (fehlt → Crash mit Exit Code 1)
- Range-Check beim Start (außerhalb → WARN-Log, Fallback auf Default)

**Laufzeit**: Parameter nur beim Start geladen, keine Laufzeit-Änderung.

### 5.3 Signal-Engine Parameter

| Variable | Default | Beschreibung |
|----------|---------|--------------|
| `SYMBOL_WHITELIST` | `.env` | Kommagetrennte Handelspaare |
| `LOOKBACK_MINUTES` | 15 | Momentum-Analysefenster |
| `INTERVAL` | `.env` | Candle-Intervall |
| `TOP_N` | `.env` | Top-N Mover filtern |

---

## 6. Entwicklungs-Leitplanken (aus copilot-instructions.md)

### 6.1 Sprache & Stil

**PFLICHT**: Antworten immer auf Deutsch. Keine Mischsprachen. Kurz, faktenbasiert.

### 6.2 Session-Start-Routine

1. Container-Status prüfen: `docker ps --filter "name=cdb_"`
2. Falls gestoppt: `docker compose up -d`
3. Warte ~10s, prüfe Health-Checks
4. Lies `backoffice/PROJECT_STATUS.md`

### 6.3 Sicherheits-Regeln

- Niemals Secrets, ENV-Inhalte oder Zugangsdaten ausgeben
- Platzhalter verwenden (`<API_KEY>`, `<REDIS_PASSWORD>`)
- Logs/Doku ohne reale Secrets

### 6.4 Agent-Rollen (MCP)

- **Coding-Agent**: Implementierung → gpt-5-codex
- **Umsetzungs-Agent**: Mehrstufig → Claude Sonnet 4.5
- **Analyse-Agent**: Logs/Risk → Gemini 1.5 Pro
- **Review-Agent**: Issues/PR → Mistral Large

### 6.5 Mandatory Practices

- **Logging**: Über `backoffice/logging_config.json`, keine Inline-Logger
- **Dokumentation**: Sofort nach Handlung, nicht erst am Ende
- **Event-Schema**: `EVENT_SCHEMA.json` ist Single Source of Truth
- **Docker/ENV-Änderungen**: Validieren gegen `docker-compose.yml`

### 6.6 Verboten (Don'ts)

- Keine direkten Änderungen an Secrets/ENV ohne `/plan` + Freigabe
- Keine Shell-Befehle mit Datenzerstörung (`rm -rf`, `DROP TABLE`)
- Kein Rate-Verhalten bei unbekannten Anforderungen

---

## 7. Monitoring & Observability

### 7.1 Health-Checks (Compose)

**Pattern**: `curl -fsS http://localhost:PORT/health`

**Response**: HTTP 200, JSON `{"status": "ok"}`

### 7.2 Prometheus Scraping

- **Intervall**: 15 Sekunden
- **Targets**: Signal Engine, Risk Manager, Execution Service, Prometheus selbst
- **Format**: `/metrics` Endpoint (Prometheus Text-Format)

### 7.3 Logs (Structured JSON)

**Config**: `backoffice/logging_config.json`

**Format**: JSON-Zeilen mit `timestamp`, `level`, `message`, `extra`

**Zentral**: Alle Services nutzen zentrale Logging-Config

### 7.4 Alerts (Dashboard Integration)

- **Topic**: `alerts` (Redis Pub/Sub)
- **Display**: Grafana Dashboard Statusleiste + Notifications
- **Retention**: Alerts in PostgreSQL loggen für Audit

---

## 8. Deployment & Operations

### 8.1 Standard-Deployment

```bash
docker compose pull
docker compose up -d
docker compose ps
```

**Health-Check-Wait**: 10-15 Sekunden nach Start.

### 8.2 Validation

```bash
docker compose config --quiet                   # Syntax-Check
pwsh backoffice/automation/check_env.ps1        # ENV-Duplikate
curl http://localhost:8001/health               # Service-Health
```

### 8.3 Troubleshooting-Pattern

1. **Container crasht**: `docker compose logs <service>`
2. **DB-Verbindung**: `docker exec cdb_postgres pg_isready -U <USER>`
3. **Redis-Verbindung**: `docker exec cdb_redis redis-cli -a <PWD> ping`
4. **Event-Flow**: `docker exec cdb_redis redis-cli -a <PWD> SUBSCRIBE <topic>`

### 8.4 Rollback

```bash
docker compose down
git checkout <alte_version>
docker compose up -d --build
```

**Achtung**: `docker compose down -v` löscht alle Daten (Volumes)!

---

## Quellen-Referenzen

- **ARCHITEKTUR.md**: Abschnitte 1, 2, 3
- **Risikomanagement-Logik.md**: Abschnitte 1-6
- **SERVICE_TEMPLATE.md**: Gesamtes Dokument
- **DEVELOPMENT.md**: Abschnitte 0-6
- **docker-compose.yml**: Services, Networks, Volumes, Security
- **copilot-instructions.md**: Abschnitte 1-11

**Nächster Schritt**: agata-van-data identifiziert Konflikte zwischen diesen Quellen.
