# Lokale-Only Tests - Claire de Binaire

> **Erweiterte Test-Suite für lokale Validierung mit Docker-Containern**
> Erstellt: 2025-11-20

---

## 📁 Struktur

```
tests/local/
├── conftest.py           # Fixtures (Redis, PostgreSQL, Docker, Test-Data)
├── service/              # Service-spezifische Tests (37 Tests)
│   ├── test_risk_manager_service.py      (15 Tests)
│   ├── test_signal_engine_service.py     (11 Tests)
│   └── test_execution_service.py         (11 Tests)
└── integration/          # Service-Integration-Tests (8 Tests)
    └── test_full_pipeline_integration.py (8 Tests)
```

---

## 🚀 Schnellstart

### Voraussetzungen

1. **Docker Compose starten**:
   ```bash
   docker compose up -d
   ```

2. **Dependencies installieren** (falls nicht vorhanden):
   ```bash
   pip install redis psycopg2-binary
   ```

### Tests ausführen

```bash
# Service-Tests (Risk Manager, Signal Engine, Execution)
make test-services
# oder: pytest -v -m local_only tests/local/service/

# Integration-Tests (Multi-Service-Flows)
make test-integration-local
# oder: pytest -v -m local_only tests/local/integration/

# Alle lokalen Tests (E2E + Services + Integration)
make test-all-local
# oder: pytest -v -m local_only tests/e2e/ tests/local/
```

---

## 📊 Test-Übersicht

### Service-Tests (37 Tests)

#### Risk Manager (15 Tests)
- **Layer 1-7**: Alle Risk-Validierungs-Layer
- **Service**: Health-Endpoint, Stats, Alerts

#### Signal Engine (11 Tests)
- **Momentum-Strategie**: BUY/SELL/Sideways-Signals
- **Service**: Health-Endpoint, Stats
- **Pub/Sub**: market_data → signals

#### Execution Service (11 Tests)
- **Order-Execution**: BUY/SELL, Slippage
- **Database**: PostgreSQL-Persistierung
- **Pub/Sub**: orders → order_results

### Integration-Tests (8 Tests)

#### Full Pipeline (8 Tests)
- **End-to-End**: market_data → signals → orders → execution_results → DB
- **Multi-Service**: Alle 3 Services zusammen
- **Error-Propagation**: Fehlerbehandlung über Services hinweg

---

## 🎯 Was wird getestet?

### ✅ Service-Funktionalität

- **Health-Endpoints**: `/health`, `/status`
- **Redis Pub/Sub**: Event-Publishing & -Subscribing
- **Business-Logik**:
  - Risk Manager: 7-Layer-Validierung
  - Signal Engine: Momentum-Strategie
  - Execution Service: Paper-Trading

### ✅ Service-Integration

- **Signal → Risk**: Signals werden validiert
- **Risk → Execution**: Orders werden ausgeführt
- **Execution → DB**: Trades werden persistiert
- **Full Pipeline**: Kompletter Event-Flow

### ✅ Error-Handling

- Malformed messages
- Stale data
- Invalid prices
- Service-Ausfälle (graceful degradation)

---

## 🔧 Fixtures

### Redis
- `redis_client` - Verbindung zu cdb_redis
- `redis_pubsub` - Pub/Sub client

### PostgreSQL
- `postgres_connection` - Verbindung zu cdb_postgres
- `postgres_cursor` - Query-Cursor
- `clean_database` - Cleanup vor/nach Tests

### Service Health
- `check_service_health` - HTTP Health-Check

### Test Data
- `sample_market_data`
- `sample_signal_event`
- `sample_order_event`
- `sample_execution_result`

---

## ⚠️ Wichtige Hinweise

### Services müssen laufen

Alle Tests setzen voraus, dass Docker Compose läuft:

```bash
docker compose ps
# Erwartete Services: cdb_redis, cdb_postgres, cdb_core, cdb_risk, cdb_execution
```

Bei gestoppten Services:
- Tests werden `SKIPPED` (kein Fehler)
- Beispiel: `pytest.skip("Risk Manager not running")`

### Dependency-Installation

Falls pytest nicht `redis` findet:

```bash
# Im pytest-Environment
pip install redis psycopg2-binary
```

### Test-Timing

Einige Tests haben `time.sleep()` für Message-Propagation:
- Bei langsamen Systemen: Timeouts evtl. anpassen
- Empfohlen: Mindestens 2 CPU-Kerne für Docker

---

## 📚 Weitere Dokumentation

- **Design-Doc**: `backoffice/docs/testing/LOCAL_ONLY_TEST_DESIGN.md`
- **Ausführliche Anleitung**: `backoffice/docs/testing/LOCAL_E2E_TESTS.md`
- **Abschlussbericht**: `LOCAL_TEST_ORCHESTRATOR_REPORT.md`

---

## 🐛 Troubleshooting

### Problem: "ModuleNotFoundError: No module named 'redis'"

**Lösung**:
```bash
pip install redis psycopg2-binary
```

### Problem: Tests werden alle geskippt

**Ursache**: Docker Compose nicht gestartet

**Lösung**:
```bash
docker compose up -d
docker compose ps  # Prüfen, ob Services running
```

### Problem: Tests hängen bei Redis Pub/Sub

**Ursache**: Timeout zu kurz für langsames System

**Lösung**: In Test-Dateien `timeout` erhöhen:
```python
for message in pubsub.listen():
    if time.time() - start_time > 30:  # 10 → 30 Sekunden
        break
```

---

**Version**: 1.0
**Maintainer**: Claire de Binaire Team
