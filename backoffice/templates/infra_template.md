# Infra-Templates - Wiederverwendbare Patterns

**Erstellt von**: devops-infrastructure-architect
**Datum**: 2025-11-16
**Zweck**: Generische Blueprints für Docker, Compose, ENV, Tests

---

## 1. Standard-Dockerfile (MVP-Service)

**Anwendungsfall**: Python-basierte Microservices mit FastAPI/Flask

```dockerfile
# syntax=docker/dockerfile:1
FROM python:3.11-slim

# Non-Root-User erstellen
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Arbeitsverzeichnis
WORKDIR /app

# Dependencies installieren (Layer-Caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Source-Code kopieren
COPY . .

# Ownership setzen
RUN chown -R appuser:appuser /app

# Non-Root-User wechseln
USER appuser

# Health-Check definieren
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD curl -fsS http://localhost:${SERVICE_PORT}/health || exit 1

# Exponierter Port (via ARG/ENV)
EXPOSE ${SERVICE_PORT}

# Startup-Command
CMD ["python", "-u", "service.py"]
```

**Hinweise**:
- `python:3.11-slim`: Minimales Image, reduzierte Angriffsfläche
- Non-Root-User: Security Best Practice
- `--no-cache-dir`: Speicher sparen
- `-u` Flag: Unbuffered Output für Docker Logs
- Health-Check: In Dockerfile oder docker-compose.yml (Flexibilität)

---

## 2. Standard-docker-compose-Service

**Anwendungsfall**: MVP-Service mit vollständigem Hardening

```yaml
services:
  {{SERVICE_NAME}}:
    build:
      context: ./backoffice/services/{{SERVICE_NAME}}
      dockerfile: Dockerfile
    container_name: cdb_{{SERVICE_NAME}}
    restart: unless-stopped
    env_file: .env
    ports:
      - "{{HOST_PORT}}:{{CONTAINER_PORT}}"
    volumes:
      # Production: Nur Daten-Volumes, kein Code-Mount
      - {{SERVICE_NAME}}_data:/data
      # Development (optional): Code-Mount für Hot-Reload
      # - ./backoffice/services/{{SERVICE_NAME}}:/app
    depends_on:
      - cdb_redis
      # Weitere Dependencies hier
    healthcheck:
      test: ["CMD", "curl", "-fsS", "http://localhost:{{CONTAINER_PORT}}/health"]
      interval: 30s
      timeout: 3s
      retries: 3
    user: "1000:1000"  # Non-Root erzwingen
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    tmpfs:
      - /tmp
    read_only: true
    networks:
      cdb_network:
        aliases:
          - {{SERVICE_NAME}}
```

**Platzhalter-Ersetzung**:
- `{{SERVICE_NAME}}`: z.B. `risk_manager`, `signal_engine`
- `{{HOST_PORT}}`: z.B. `8002`
- `{{CONTAINER_PORT}}`: meist identisch mit HOST_PORT

**Hinweise**:
- **Development vs. Production**: Code-Mount via `docker-compose.override.yml` steuern
- **read_only**: Falls Service Schreibzugriff braucht → `tmpfs` für `/tmp` oder `/app/cache`
- **user**: UID:GID explizit setzen (1000:1000 für Development, anpassbar für Production)

---

## 3. Standard-.env.template

**Anwendungsfall**: ENV-Template für neue Projekte

```env
# ==============================================================================
# {{PROJECT_NAME}} - Environment Configuration
# ==============================================================================
# WICHTIG: Diese Datei nach .env kopieren und anpassen!
# ⚠️ NIEMALS .env ins Git committen (enthält Secrets)!

# ==============================================================================
# DATABASE (PostgreSQL)
# ==============================================================================
POSTGRES_DB={{PROJECT_NAME}}_db
POSTGRES_USER={{PROJECT_NAME}}_user
POSTGRES_PASSWORD=<SET_IN_ENV>  # ⚠️ SECRET
DATABASE_URL=postgresql://{{PROJECT_NAME}}_user:<PASSWORD>@cdb_postgres:5432/{{PROJECT_NAME}}_db

# ==============================================================================
# MESSAGE BUS (Redis)
# ==============================================================================
REDIS_HOST=cdb_redis
REDIS_PORT=6379
REDIS_PASSWORD=<SET_IN_ENV>  # ⚠️ SECRET
REDIS_DB=0

# ==============================================================================
# SERVICE PORTS (Internal Container Ports)
# ==============================================================================
# Hinweis: Host-Port-Mappings werden in docker-compose.yml definiert
{{SERVICE_NAME}}_PORT={{PORT}}
# Beispiel: SIGNAL_ENGINE_PORT=8001

# ==============================================================================
# RISK MANAGEMENT (Defaults - Dezimal-Konvention)
# ==============================================================================
# Format: Dezimalwerte (0.05 = 5%)
MAX_DAILY_DRAWDOWN_PCT=0.05      # Min: 0.01, Max: 0.20
MAX_POSITION_PCT=0.10            # Min: 0.01, Max: 0.25
MAX_EXPOSURE_PCT=0.50            # Min: 0.10, Max: 1.00
STOP_LOSS_PCT=0.02               # Min: 0.005, Max: 0.10
MAX_SLIPPAGE_PCT=0.01            # Min: 0.001, Max: 0.05
MAX_SPREAD_MULTIPLIER=5.0        # Min: 2.0, Max: 10.0
DATA_STALE_TIMEOUT_SEC=30        # Min: 10, Max: 120
INITIAL_CAPITAL=1000             # Startkapital (Paper Trading)

# ==============================================================================
# EXTERNAL APIs (Secrets - NIEMALS committen!)
# ==============================================================================
{{EXCHANGE}}_API_KEY=<SET_IN_ENV>      # ⚠️ SECRET
{{EXCHANGE}}_API_SECRET=<SET_IN_ENV>   # ⚠️ SECRET
# Beispiel: MEXC_API_KEY, BINANCE_API_KEY

# ==============================================================================
# MONITORING (Prometheus/Grafana)
# ==============================================================================
GF_SECURITY_ADMIN_USER=admin
GF_SECURITY_ADMIN_PASSWORD=<SET_IN_ENV>  # ⚠️ SECRET
GF_USERS_ALLOW_SIGN_UP=false

# ==============================================================================
# FEATURE FLAGS (Optional)
# ==============================================================================
ENABLE_PAPER_TRADING=true
ENABLE_LIVE_MODE=false  # ⚠️ CRITICAL: Nur nach expliziter Freigabe aktivieren
DEBUG_MODE=false
```

**Hinweise**:
- **Namenskonvention**: `{{PROJECT_NAME}}_` Präfix für Eindeutigkeit
- **Secrets-Platzhalter**: `<SET_IN_ENV>`, `<REQUIRED>`, oder `<CHANGE_ME>`
- **Kommentare**: Min/Max-Ranges dokumentieren
- **Dezimal-Konvention**: Konsistenz mit Trading-Code (siehe SR-002)

---

## 4. Test-Setup-Struktur

**Anwendungsfall**: Pytest-basierte Tests für MVP-Services

### Verzeichnisstruktur

```
tests/
├── conftest.py                 # Fixtures (Redis-Mock, DB-Mock, etc.)
├── unit/
│   ├── test_smoke_repo.py      # Repository-Smoke-Tests
│   ├── test_{{service}}_logic.py
│   └── test_risk_engine.py
├── integration/
│   ├── test_compose_smoke.py   # Docker Compose Health-Checks
│   ├── test_redis_pubsub.py    # Event-Bus-Integration
│   └── test_{{service}}_e2e.py
└── fixtures/
    ├── sample_market_data.json
    ├── sample_signals.json
    └── sample_env.py
```

### conftest.py (Fixture-Template)

```python
import pytest
import redis
from unittest.mock import MagicMock

@pytest.fixture
def mock_redis():
    """Mock Redis-Client für Unit-Tests"""
    mock = MagicMock(spec=redis.Redis)
    mock.ping.return_value = True
    return mock

@pytest.fixture
def mock_env(monkeypatch):
    """Mock ENV-Variablen für Tests"""
    env_vars = {
        "REDIS_HOST": "localhost",
        "REDIS_PORT": "6379",
        "REDIS_PASSWORD": "test_password",
        "MAX_DAILY_DRAWDOWN_PCT": "0.05",
        "MAX_POSITION_PCT": "0.10",
        # ... weitere ENV
    }
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    return env_vars

@pytest.fixture
def sample_market_data():
    """Sample Market Data für Tests"""
    return {
        "symbol": "BTC_USDT",
        "price": 50000.0,
        "volume": 1000000.0,
        "timestamp": 1736600000,
        "pct_change": 5.0
    }
```

### test_compose_smoke.py (Integration-Test-Template)

```python
import subprocess
import time
import requests

def test_all_services_healthy():
    """Prüft, ob alle Services in docker-compose.yml healthy sind"""
    services = [
        ("cdb_redis", "6379"),
        ("cdb_postgres", "5432"),
        ("cdb_ws", "8000"),
        ("cdb_core", "8001"),
        ("cdb_risk", "8002"),
        ("cdb_execution", "8003"),
    ]

    for service_name, port in services:
        # Health-Check (HTTP)
        if port in ["8000", "8001", "8002", "8003"]:
            resp = requests.get(f"http://localhost:{port}/health", timeout=5)
            assert resp.status_code == 200
            assert resp.json().get("status") in ["healthy", "ok"]

        # Container-Status prüfen
        result = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Health.Status}}", service_name],
            capture_output=True,
            text=True
        )
        assert "healthy" in result.stdout.lower() or "none" in result.stdout.lower()
```

**Hinweise**:
- **Fixtures**: Wiederverwendbare Test-Daten zentral in `conftest.py`
- **Mocks**: Redis/DB-Mocks für schnelle Unit-Tests ohne Abhängigkeiten
- **Integration-Tests**: Docker-basiert, prüfen echte Service-Interaktionen

---

## 5. prometheus.yml (Scrape-Config-Template)

**Anwendungsfall**: Prometheus-Scraping für MVP-Services

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  # Prometheus selbst
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
        labels:
          instance: 'prometheus'
          service: 'monitoring'

  # MVP-Services (Template)
  - job_name: '{{SERVICE_NAME}}'
    static_configs:
      - targets: ['{{SERVICE_ALIAS}}:{{PORT}}']
        labels:
          instance: '{{SERVICE_NAME}}'
          service: '{{SERVICE_CATEGORY}}'  # z.B. 'trading', 'analysis', 'risk'
    metrics_path: '/metrics'
    # Optional: Basic Auth, wenn Services geschützt
    # basic_auth:
    #   username: 'prometheus'
    #   password: '${PROMETHEUS_PASSWORD}'
```

**Platzhalter**:
- `{{SERVICE_NAME}}`: z.B. `signal_engine`
- `{{SERVICE_ALIAS}}`: Docker-Network-Alias (z.B. `signal_engine`, nicht `cdb_core`)
- `{{PORT}}`: Container-Port (z.B. `8001`)
- `{{SERVICE_CATEGORY}}`: Logische Gruppierung (`trading`, `analysis`, `risk`, `monitoring`)

---

## 6. Repo-Struktur-Empfehlungen

### Für neue Projekte (Claire-de-Binare-inspiriert)

```
{{PROJECT_NAME}}/
├── backoffice/
│   ├── services/               # MVP-Services
│   │   ├── {{service_1}}/
│   │   │   ├── Dockerfile
│   │   │   ├── service.py
│   │   │   ├── models.py
│   │   │   ├── config.py
│   │   │   ├── requirements.txt
│   │   │   └── README.md
│   │   ├── {{service_2}}/
│   │   └── ...
│   ├── docs/                   # Architektur-/Risk-Doku
│   │   ├── ARCHITEKTUR.md
│   │   ├── DECISION_LOG.md
│   │   ├── Risikomanagement-Logik.md
│   │   ├── EVENT_SCHEMA.json
│   │   └── DATABASE_SCHEMA.sql
│   └── automation/             # DevOps-Skripte
│       ├── check_env.ps1
│       └── backup_db.sh
├── tests/                      # Tests (siehe Template oben)
│   ├── conftest.py
│   ├── unit/
│   └── integration/
├── sandbox/                    # Playground / Experiments
├── logs/                       # Laufzeit-Logs (gitignored)
├── docker-compose.yml          # Production-Setup
├── docker-compose.override.yml # Development-Overrides (optional)
├── prometheus.yml
├── .env.template               # ENV-Template (committed)
├── .env                        # Echte Secrets (gitignored!)
├── .gitignore
├── requirements.txt            # Root-Dependencies (falls vorhanden)
├── README.md
└── CLAUDE.md                   # Projekt-Instruktionen für Claude Code
```

**Best Practices**:
- **backoffice/services/**: Ein Verzeichnis pro Service (self-contained)
- **backoffice/docs/**: Zentrale Doku, **Single Source of Truth**
- **docker-compose.override.yml**: Development-Mounts, Debug-Flags (nicht committed)
- **.env.template**: Vollständige ENV-Liste mit Platzhaltern (committed)
- **.env**: Echte Secrets, **NIEMALS committen** (`.gitignore`!)

---

## 7. Cleanup-Plan-Template

**Anwendungsfall**: Legacy-Files identifizieren und bereinigen

### Kategorien

| Kategorie | Aktion | Beispiel |
|-----------|--------|----------|
| **Duplikat** | Diff prüfen → Falls identisch: Löschen | `Dockerfile - Kopie` |
| **Legacy** | Umbenennen zu `.bak` oder in `archive/` verschieben | `old_config.yml` |
| **Unklar** | In `TODO.md` dokumentieren, Team fragen | `query_service/` (nicht in Compose) |
| **Redundant** | Single Source of Truth definieren, andere entfernen | `compose.yml` vs. `docker-compose.yml` |

### Prozess

1. **Inventarisieren**: Alle Files in `file_index.md` (wie in Pipeline 3)
2. **Kategorisieren**: Status: `kandidat_relevant`, `legacy`, `unklar`
3. **Diff-Check**: Duplikate vergleichen (`diff`, `git diff --no-index`)
4. **Entscheidung dokumentieren**: In `DECISION_LOG.md` (ADR-Format)
5. **Archivieren statt Löschen**: Erst in `archive/`, nach 30 Tagen löschen

---

## 8. Single Source of Truth (SSOT) Empfehlungen

Basierend auf Claire-de-Binare-Analyse:

### Files, die SSOT sein sollten

| File | Rolle | Begründung |
|------|-------|------------|
| `docker-compose.yml` | Haupt-Deployment-Definition | Aktiv genutzt, vollständig |
| `.env.template` | ENV-Referenz | Kommittierbar, Platzhalter statt Secrets |
| `backoffice/docs/ARCHITEKTUR.md` | System-Architektur | Zentrale Referenz |
| `backoffice/docs/EVENT_SCHEMA.json` | Event-Schemas | Versioniert, maschinenlesbar |
| `prometheus.yml` | Monitoring-Config | Aktiv genutzt |

### Files, die entfernt/archiviert werden sollten

| File | Status | Empfehlung |
|------|--------|------------|
| `Dockerfile - Kopie` | Duplikat? | Diff prüfen, ggf. löschen |
| `compose.yml` | Duplikat von docker-compose.yml? | Diff prüfen, eine behalten |
| `cdb_signal_gen` (in compose) | Fehlende Dockerfile, unklar | Service entfernen oder reparieren |

---

## Integration mit project_template.md

Falls `sandbox/project_template.md` aus Pipeline 2 existiert:

**Ergänzung in project_template.md**:

```markdown
## Infra-/Runtime-Blueprint

Siehe [infra_templates.md](./infra_templates.md) für:
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
```

---

## Zusammenfassung

Diese Templates bieten:
1. **Wiederverwendbare Patterns**: Copy-Paste-ready für neue Services
2. **Security-Hardening**: Best Practices eingebaut (Non-Root, read-only, cap_drop)
3. **Konsistenz**: Einheitliche Struktur über alle Services
4. **Dokumentation**: Inline-Kommentare erklären Zweck und Optionen

**Nächste Schritte**:
- Templates in `backoffice/templates/` (oder ähnlich) im Haupt-Repo ablegen
- Bei neuen Services: Template kopieren, Platzhalter ersetzen, anpassen
- Bei Änderungen: Templates aktualisieren (Living Documentation)
