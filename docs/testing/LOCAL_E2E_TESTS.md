# Local E2E Tests - Claire de Binaire
**Vollständige lokale Test-Suite mit Docker Compose**

---

## 📋 Inhaltsverzeichnis

1. [Übersicht](#übersicht)
2. [Test-Kategorien](#test-kategorien)
3. [Setup & Voraussetzungen](#setup--voraussetzungen)
4. [Ausführung](#ausführung)
5. [Test-Szenarien](#test-szenarien)
6. [Troubleshooting](#troubleshooting)
7. [CI vs. Lokal](#ci-vs-lokal)

---

## 1. Übersicht

Die lokale E2E-Test-Suite testet das **vollständige Claire de Binaire System** mit **echten Docker-Containern**, realistischen Event-Flows und Performance unter Last.

### Warum lokale-only Tests?

Diese Tests sind **bewusst NICHT in CI**:
- ✅ **Ressourcenintensiv**: 9 Docker-Container, Redis, PostgreSQL
- ✅ **Zeitintensiv**: 60+ Sekunden pro Test-Suite
- ✅ **Destruktiv**: Stoppen/Starten von Containern
- ✅ **Realistisch**: Echte Datenbank, echte Message-Bus, echte Services

### Test-Struktur

```
tests/
├── e2e/                        # E2E-Tests (Docker erforderlich)
│   ├── test_docker_compose_full_stack.py
│   ├── test_event_flow_pipeline.py
│   └── test_redis_postgres_integration.py
│
├── local/                      # Lokale-only Tests (NEU!)
│   ├── test_full_system_stress.py
│   ├── test_analytics_performance.py
│   └── test_docker_lifecycle.py
│
├── unit/                       # Unit-Tests (CI)
├── integration/                # Integration-Tests mit Mocks (CI)
└── conftest.py
```

---

## 2. Test-Kategorien

### 2.1 E2E-Tests (`@pytest.mark.e2e`)
**18 Tests** - Basis End-to-End mit Docker Compose

| Test-Datei | Tests | Beschreibung |
|-----------|-------|--------------|
| `test_docker_compose_full_stack.py` | 5 | Container Health, HTTP-Endpoints |
| `test_event_flow_pipeline.py` | 5 | Market-Data → Signal → Risk → Order |
| `test_redis_postgres_integration.py` | 8 | Redis Pub/Sub, PostgreSQL CRUD |

**Ausführung**:
```bash
pytest -v -m e2e
# oder
make test-e2e
```

**Voraussetzung**: Docker Compose Stack läuft (`docker compose up -d`)

---

### 2.2 Local-Only Tests (`@pytest.mark.local_only`)
**12+ Tests** - Erweiterte System-Tests

#### A) Stress-Tests (`test_full_system_stress.py`)
**4 Tests** - System unter hoher Last

| Test | Events | Duration | Validiert |
|------|--------|----------|-----------|
| `test_stress_100_market_data_events` | 100 | ~15s | Redis Throughput, DB Writer |
| `test_stress_concurrent_signal_and_order_flow` | 125 | ~10s | Concurrency, Multi-Channel |
| `test_stress_portfolio_snapshot_frequency` | 20 | ~30s | DB Write Performance |
| `test_all_docker_services_under_load` | 20 | ~10s | Service Stability |

**Ausführung**:
```bash
pytest -v -m "local_only and slow" tests/local/test_full_system_stress.py
# oder
make test-local-stress
```

---

#### B) Performance-Tests (`test_analytics_performance.py`)
**6 Tests** - Query-Performance mit realen Daten

| Test | Query-Type | Max-Duration | Validiert |
|------|-----------|--------------|-----------|
| `test_query_performance_signals_aggregation` | GROUP BY | 500ms | Index-Nutzung |
| `test_query_performance_portfolio_snapshots_timeseries` | Time-Series | 1s | Timestamp-Index |
| `test_query_performance_trades_join_orders` | JOIN | 1.5s | FK-Index |
| `test_query_performance_full_text_search` | JSONB | 2s | JSONB-Queries |
| `test_database_index_effectiveness` | EXPLAIN | - | Index-Check |
| `test_analytics_query_tool_integration` | CLI-Tool | 10s | query_analytics.py |

**Ausführung**:
```bash
pytest -v -m local_only tests/local/test_analytics_performance.py
# oder
make test-local-performance
```

---

#### C) Docker Lifecycle-Tests (`test_docker_lifecycle.py`)
**7 Tests** - Container-Lifecycle & Recovery

⚠️ **DESTRUKTIV**: Diese Tests starten Container neu!

| Test | Aktion | Destruktiv? | Validiert |
|------|--------|-------------|-----------|
| `test_docker_compose_stop_start_cycle` | Stop → Start | ⚠️ Ja | Service-Recovery |
| `test_docker_compose_restart_individual_service` | Restart cdb_core | ⚠️ Ja | Einzelner Service |
| `test_docker_compose_recreate_service` | Force-Recreate | ⚠️ Ja | Container-Erstellung |
| `test_docker_compose_down_up_full_cycle` | Down → Up | ⚠️⚠️ Sehr | Vollständiger Cycle |
| `test_docker_compose_logs_no_errors` | Log-Check | Nein | Error-Monitoring |
| `test_docker_compose_volume_persistence` | Restart → Check Data | ⚠️ Ja | Volume-Persistenz |

**Ausführung**:
```bash
pytest -v -m local_only tests/local/test_docker_lifecycle.py -s
# oder
make test-local-lifecycle
```

⚠️ **Warnung**: Diese Tests können laufende Container unterbrechen!

---

## 3. Setup & Voraussetzungen

### 3.1 System-Requirements

- **Docker Desktop** (oder Docker Engine + Docker Compose)
- **Python 3.11+**
- **8GB RAM minimum** (16GB empfohlen)
- **10GB freier Speicher**

### 3.2 Installation

```bash
# 1. Repository klonen
cd Claire_de_Binare_Cleanroom

# 2. Dependencies installieren
pip install -r requirements-dev.txt

# 3. ENV-Datei prüfen
cat .env  # Sollte POSTGRES_PASSWORD, REDIS_PASSWORD enthalten

# 4. Docker Compose Stack starten
docker compose up -d

# 5. Warten bis alle Services healthy sind
docker compose ps

# Erwartete Ausgabe:
# cdb_postgres     healthy
# cdb_redis        healthy
# cdb_core         healthy
# cdb_risk         healthy
# cdb_execution    healthy
# cdb_db_writer    healthy (oder starting)
# ... (9 Services total)
```

### 3.3 ENV-Variablen

Wichtig für lokale Tests:

```bash
# PostgreSQL
POSTGRES_HOST=localhost      # Für Host-Maschine
POSTGRES_PORT=5432
POSTGRES_DB=claire_de_binaire
POSTGRES_USER=claire_user
POSTGRES_PASSWORD=claire_db_secret_2024

# Redis
REDIS_HOST=localhost        # Für Host-Maschine
REDIS_PORT=6379
REDIS_PASSWORD=claire_redis_secret_2024
```

**Hinweis**: In Docker-Containern sind Hostnames `cdb_postgres` / `cdb_redis`.

---

## 4. Ausführung

### 4.1 Quick Start

```bash
# 1. Docker starten (falls nicht läuft)
docker compose up -d

# 2. Alle lokalen Tests ausführen
pytest -v -m local_only
```

### 4.2 Makefile-Targets

```bash
# Übersicht
make help

# E2E-Tests (18 Tests, ~10s)
make test-e2e

# Alle lokalen Tests (~60s)
make test-local

# Stress-Tests (100+ Events, ~60s)
make test-local-stress

# Performance-Tests (Query-Speed, ~15s)
make test-local-performance

# Lifecycle-Tests (DESTRUKTIV!, ~120s)
make test-local-lifecycle

# Vollständiger System-Test (Docker + E2E + Local)
make test-full-system
```

### 4.3 Pytest Direct

```bash
# Alle E2E + Local
pytest -v -m "e2e or local_only"

# Nur langsame Tests
pytest -v -m "slow"

# Bestimmte Test-Datei
pytest -v tests/local/test_full_system_stress.py

# Mit Live-Output
pytest -v -s -m local_only

# Stop bei erstem Fehler
pytest -v -x -m e2e
```

---

## 5. Test-Szenarien

### 5.1 Szenario: Vollständiger System-Test

**Ziel**: Alle Services unter Last validieren

```bash
# 1. System starten
docker compose up -d

# 2. Warten auf Health
sleep 30

# 3. E2E-Tests
pytest -v -m e2e

# 4. Stress-Tests
pytest -v tests/local/test_full_system_stress.py::test_stress_100_market_data_events

# 5. Performance-Tests
pytest -v tests/local/test_analytics_performance.py

# Erwartete Dauer: ~90s
```

**Success-Kriterien**:
- ✅ Alle Container healthy
- ✅ E2E-Tests: 18/18 passed
- ✅ Stress-Tests: 4/4 passed
- ✅ Performance-Tests: 6/6 passed

---

### 5.2 Szenario: Performance-Debugging

**Ziel**: Langsame Queries identifizieren

```bash
# 1. Datenbank mit Test-Daten füllen
pytest -v tests/local/test_full_system_stress.py::test_stress_concurrent_signal_and_order_flow

# 2. Performance-Tests ausführen
pytest -v -s tests/local/test_analytics_performance.py

# 3. Ausgabe analysieren
# Erwartete Ausgabe:
#   ✓ Query completed in 245ms
#   ✓ Returned 10 rows
#   📊 Top Symbols by Signal Count:
#     - BTCUSDT (buy): 45 signals
```

**Fehlersuche**:
- Query > 500ms? → Index fehlt
- Query > 2s? → EXPLAIN ANALYZE prüfen

---

### 5.3 Szenario: Recovery-Test

**Ziel**: Service-Ausfälle simulieren

```bash
# 1. Services starten
docker compose up -d

# 2. Einzelnen Service crashen lassen
docker compose stop cdb_core

# 3. Prüfen: Andere Services stabil?
docker compose ps

# 4. Service neu starten
docker compose up -d cdb_core

# 5. Lifecycle-Test ausführen
pytest -v tests/local/test_docker_lifecycle.py::test_docker_compose_restart_individual_service
```

---

## 6. Troubleshooting

### 6.1 Container nicht healthy

**Problem**:
```bash
docker compose ps
# cdb_core    unhealthy
```

**Lösung**:
```bash
# Logs prüfen
docker compose logs cdb_core --tail=50

# Health-Check manuell testen
curl -fsS http://localhost:8001/health

# Container neu starten
docker compose restart cdb_core

# Warten auf Health
sleep 20
docker compose ps cdb_core
```

---

### 6.2 PostgreSQL Connection Refused

**Problem**:
```
psycopg2.OperationalError: connection refused
```

**Lösung**:
```bash
# 1. Prüfen: Container läuft?
docker compose ps cdb_postgres

# 2. Prüfen: Port exposed?
docker compose ps | grep 5432

# 3. ENV-Variable setzen
export POSTGRES_HOST=localhost

# 4. Passwort prüfen
grep POSTGRES_PASSWORD .env
```

---

### 6.3 Redis Authentication Error

**Problem**:
```
redis.exceptions.AuthenticationError: Authentication required
```

**Lösung**:
```bash
# ENV-Variable setzen
export REDIS_PASSWORD=claire_redis_secret_2024

# Oder: In Test-Fixture anpassen
redis.Redis(
    host='localhost',
    port=6379,
    password='claire_redis_secret_2024'
)
```

---

### 6.4 Tests zu langsam

**Problem**: Tests dauern >5 Minuten

**Optimierung**:
```bash
# Nur schnelle Tests
pytest -v -m "e2e and not slow"

# Parallel ausführen (mit pytest-xdist)
pip install pytest-xdist
pytest -v -m e2e -n 4

# Bestimmte Tests skippenexport SKIP_SLOW_TESTS=1
pytest -v -m "e2e and not slow"
```

---

### 6.5 Docker Out of Memory

**Problem**: Container crashen mit OOM

**Lösung**:
```bash
# Docker-Ressourcen erhöhen (Docker Desktop)
# Settings → Resources → Memory: 8GB+

# Container-Stats prüfen
docker stats

# Ungenutzte Ressourcen aufräumen
docker system prune -a
docker volume prune
```

---

## 7. CI vs. Lokal

### 7.1 Test-Trennung

| Test-Typ | Marker | CI | Lokal | Duration | Requires Docker |
|----------|--------|----|----|----------|-----------------|
| **Unit** | `@pytest.mark.unit` | ✅ | ✅ | <1s | ❌ |
| **Integration** | `@pytest.mark.integration` | ✅ | ✅ | <5s | ❌ (Mocks) |
| **E2E** | `@pytest.mark.e2e` | ❌ | ✅ | 10-60s | ✅ |
| **Local-Only** | `@pytest.mark.local_only` | ❌ | ✅ | 60-300s | ✅ |

### 7.2 CI-Pipeline (.github/workflows/tests.yml)

```yaml
# CI führt NUR aus:
pytest -v -m "not e2e and not local_only"

# Explizit NICHT in CI:
# - E2E-Tests (brauchen Docker Compose)
# - Local-Only Tests (zu ressourcenintensiv)
# - Slow Tests (>10s)
```

### 7.3 Pre-Commit Hooks

```bash
# Pre-Commit führt NUR Unit-Tests aus
# .pre-commit-config.yaml:
hooks:
  - id: pytest
    args: ["-m", "unit", "--tb=short"]
```

---

## 8. Erweiterte Szenarien

### 8.1 Custom Stress-Test schreiben

```python
# tests/local/test_custom_stress.py
import pytest

@pytest.mark.local_only
@pytest.mark.slow
def test_custom_stress_scenario(redis_client, postgres_conn):
    """Custom Stress-Test für spezifisches Szenario"""

    # 1. Setup: Baseline messen
    cursor = postgres_conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM signals")
    baseline = cursor.fetchone()[0]

    # 2. Load: Events publizieren
    for i in range(200):
        event = {"type": "signal", "symbol": "BTCUSDT", ...}
        redis_client.publish("signals", json.dumps(event))

    # 3. Validation: DB-Count prüfen
    time.sleep(5)
    cursor.execute("SELECT COUNT(*) FROM signals")
    after = cursor.fetchone()[0]

    assert after > baseline, "Events not persisted"
```

---

### 8.2 Performance-Baseline definieren

```python
# tests/local/conftest.py
import pytest

@pytest.fixture(scope="session")
def performance_baseline():
    """Performance-Baseline für Regression-Tests"""
    return {
        "query_signals_aggregation_ms": 500,
        "query_portfolio_timeseries_ms": 1000,
        "query_trades_join_ms": 1500,
        "stress_100_events_sec": 15,
    }

@pytest.mark.local_only
def test_performance_regression(performance_baseline):
    """Prüfe: Performance nicht schlechter als Baseline"""
    # ... Test-Logik
    assert elapsed_ms < performance_baseline["query_signals_aggregation_ms"]
```

---

## 9. Abschluss-Checklist

Vor Commit lokaler Tests:

- [ ] Alle E2E-Tests bestehen (18/18)
- [ ] Alle Local-Only Tests bestehen
- [ ] Docker Compose Stack läuft stabil
- [ ] Keine CRITICAL/ERROR Logs in Services
- [ ] Makefile-Targets funktionieren
- [ ] Dokumentation aktualisiert
- [ ] CI-Tests unverändert (keine E2E in CI!)

---

## 10. Kontakt & Support

**Issues**: https://github.com/jannekbuengener/Claire_de_Binare_Cleanroom/issues

**Dokumentation**:
- `TESTING_GUIDE.md` - Allgemeine Test-Richtlinien
- `E2E_PAPER_TEST_REPORT.md` - E2E-Test-Report
- `README_ANALYTICS.md` - Analytics Query Tool

---

**Status**: ✅ Operational
**Letzte Aktualisierung**: 2025-11-20
**Test-Coverage**: 135+ Tests (18 E2E, 12+ Local-Only)
