# Local-Only Test Design - Claire de Binaire
> **Design-Dokument für erweiterte lokale Test-Suite**
> Erstellt: 2025-11-20
> Status: Design Phase

---

## 📊 Bestandsaufnahme

### Vorhandene Tests (~103 Tests)

**Unit-Tests** (83):
- ✅ execution_simulator (23 Tests)
- ✅ mexc_perpetuals (29 Tests)
- ✅ position_sizing (26 Tests)
- ✅ risk_engine_core (3 Tests)
- ✅ compose_smoke (1 Test)

**Integration-Tests** (2):
- ✅ event_pipeline (2 Tests mit Mocks)

**E2E-Tests** (18):
- ✅ docker_compose_full_stack (5 Tests)
- ✅ redis_postgres_integration (8 Tests)
- ✅ event_flow_pipeline (5 Tests)

### Test-Abdeckung nach Schicht

| Schicht | Abdeckung | Lücken |
|---------|-----------|--------|
| **Helper-Module** | ✅ 100% | - |
| **Services** | ⚠️ 20% | Signal Engine, Risk Manager, Execution Service |
| **Service-Integration** | ⚠️ 30% | Multi-Service-Flows |
| **Infrastructure** | ✅ 90% | - |
| **Performance** | ❌ 0% | Alle |
| **Resilience** | ❌ 0% | Alle |
| **Data-Integrity** | ⚠️ 40% | Event-Store, Audit-Trail |

---

## 🎯 Fehlende Test-Kategorien

### A. Service-Spezifische Tests (20-30 Tests)

**Warum lokal-only?**
- Testen echte Service-Implementierungen
- Benötigen Docker-Container für Redis
- Längere Setup/Teardown-Zeiten

**Neue Test-Dateien:**

#### 1. `tests/local/test_signal_engine_service.py` (8-10 Tests)
```python
@pytest.mark.local_only
@pytest.mark.slow
def test_signal_engine_subscribes_to_market_data():
    """Signal Engine subscribes to market_data channel"""

@pytest.mark.local_only
def test_signal_engine_generates_momentum_signal():
    """Signal Engine generates buy/sell signals from market data"""

@pytest.mark.local_only
def test_signal_engine_publishes_to_signals_channel():
    """Signals are published to Redis 'signals' channel"""

@pytest.mark.local_only
def test_signal_engine_health_endpoint():
    """Health endpoint returns 200 + stats"""

@pytest.mark.local_only
def test_signal_engine_stats_tracking():
    """Stats are incremented correctly"""
```

#### 2. `tests/local/test_risk_manager_service.py` (12-15 Tests)
```python
@pytest.mark.local_only
def test_risk_manager_layer_1_data_quality():
    """Layer 1: Rejects stale/invalid data"""

@pytest.mark.local_only
def test_risk_manager_layer_2_position_limits():
    """Layer 2: Blocks positions > 10% portfolio"""

@pytest.mark.local_only
def test_risk_manager_layer_3_daily_drawdown():
    """Layer 3: Blocks trading at 5% daily loss"""

@pytest.mark.local_only
def test_risk_manager_layer_4_total_exposure():
    """Layer 4: Blocks at 30% total exposure"""

@pytest.mark.local_only
def test_risk_manager_layer_5_circuit_breaker():
    """Layer 5: Emergency stop at 10% total loss"""

@pytest.mark.local_only
def test_risk_manager_layer_6_spread_check():
    """Layer 6: Rejects wide bid-ask spreads"""

@pytest.mark.local_only
def test_risk_manager_layer_7_timeout_check():
    """Layer 7: Rejects orders with stale data"""

@pytest.mark.local_only
def test_risk_manager_approves_valid_signal():
    """Valid signals are approved"""

@pytest.mark.local_only
def test_risk_manager_publishes_alerts():
    """CRITICAL/WARNING alerts are published"""
```

#### 3. `tests/local/test_execution_service.py` (5-7 Tests)
```python
@pytest.mark.local_only
def test_execution_service_mock_executor_buy():
    """MockExecutor executes buy orders"""

@pytest.mark.local_only
def test_execution_service_mock_executor_sell():
    """MockExecutor executes sell orders"""

@pytest.mark.local_only
def test_execution_service_persists_to_postgres():
    """Execution results are written to PostgreSQL"""

@pytest.mark.local_only
def test_execution_service_publishes_order_results():
    """order_results are published to Redis"""
```

---

### B. Service-Integration Tests (8-12 Tests)

**Warum lokal-only?**
- Testen mehrere Services gleichzeitig
- Benötigen alle 8 Container running
- E2E-Flows mit echten Message-Bus-Interaktionen

**Neue Test-Dateien:**

#### 4. `tests/local/test_signal_to_risk_integration.py` (4-5 Tests)
```python
@pytest.mark.local_only
@pytest.mark.slow
def test_signal_engine_publishes_risk_manager_receives():
    """End-to-End: Signal -> Risk Manager"""
    # 1. Signal Engine publishes signal
    # 2. Risk Manager receives signal
    # 3. Validate message content

@pytest.mark.local_only
def test_invalid_signal_triggers_alert():
    """Risk Manager publishes alert for invalid signals"""

@pytest.mark.local_only
def test_approved_signal_becomes_order():
    """Approved signals are converted to orders"""
```

#### 5. `tests/local/test_risk_to_execution_integration.py` (4-5 Tests)
```python
@pytest.mark.local_only
def test_risk_manager_publishes_execution_receives():
    """End-to-End: Risk -> Execution"""

@pytest.mark.local_only
def test_execution_result_updates_risk_state():
    """order_results update Risk Manager state"""

@pytest.mark.local_only
def test_rejected_order_triggers_alert():
    """Failed executions trigger alerts"""
```

#### 6. `tests/local/test_full_pipeline_integration.py` (4-6 Tests)
```python
@pytest.mark.local_only
@pytest.mark.slow
def test_market_data_to_database_flow():
    """Complete flow: market_data -> signals -> orders -> DB"""
    # 1. Publish market_data
    # 2. Wait for signal
    # 3. Wait for order
    # 4. Wait for execution_result
    # 5. Verify in PostgreSQL

@pytest.mark.local_only
@pytest.mark.slow
def test_multiple_signals_sequential_processing():
    """Multiple signals are processed in order"""

@pytest.mark.local_only
def test_pipeline_statistics_are_tracked():
    """All services track stats correctly"""
```

---

### C. Performance Tests (5-8 Tests)

**Warum lokal-only?**
- Benötigen echte Docker-Container
- Generieren Last
- Lange Laufzeiten (>30s)

**Neue Test-Dateien:**

#### 7. `tests/local/test_performance_redis.py` (3-4 Tests)
```python
@pytest.mark.local_only
@pytest.mark.slow
def test_redis_pubsub_throughput():
    """Measure: Messages/second durch Redis"""
    # Publish 1000 messages, measure time

@pytest.mark.local_only
@pytest.mark.slow
def test_redis_concurrent_publishers():
    """Multiple publishers don't interfere"""

@pytest.mark.local_only
def test_redis_message_latency():
    """Measure: Publish -> Subscribe latency"""
```

#### 8. `tests/local/test_performance_postgres.py` (2-4 Tests)
```python
@pytest.mark.local_only
@pytest.mark.slow
def test_postgres_write_throughput():
    """Measure: Inserts/second for trades table"""

@pytest.mark.local_only
def test_postgres_concurrent_writes():
    """Concurrent writes don't cause deadlocks"""
```

---

### D. Resilience/Chaos Tests (6-10 Tests)

**Warum lokal-only?**
- Simulieren Container-Ausfälle
- Erfordern Docker-Kontrolle
- Nicht in CI sinnvoll

**Neue Test-Dateien:**

#### 9. `tests/local/test_resilience_container_restart.py` (3-5 Tests)
```python
@pytest.mark.local_only
@pytest.mark.slow
def test_signal_engine_recovers_after_restart():
    """Signal Engine reconnects to Redis after restart"""
    # 1. Stop cdb_core
    # 2. Wait 5s
    # 3. Start cdb_core
    # 4. Verify subscribes again

@pytest.mark.local_only
@pytest.mark.slow
def test_risk_manager_recovers_state_after_restart():
    """Risk state is recovered from order_results"""

@pytest.mark.local_only
@pytest.mark.slow
def test_execution_service_handles_redis_disconnect():
    """Execution service reconnects to Redis"""
```

#### 10. `tests/local/test_resilience_database.py` (3-5 Tests)
```python
@pytest.mark.local_only
@pytest.mark.slow
def test_postgres_connection_pool_recovery():
    """Connection pool recovers from DB restart"""

@pytest.mark.local_only
def test_execution_service_retries_failed_db_writes():
    """DB write failures trigger retries"""
```

---

### E. Data-Integrity Tests (4-6 Tests)

**Warum lokal-only?**
- Prüfen echte PostgreSQL-Constraints
- Erfordern komplexe Daten-Setups
- Längere Laufzeiten

**Neue Test-Dateien:**

#### 11. `tests/local/test_data_integrity_postgres.py` (4-6 Tests)
```python
@pytest.mark.local_only
def test_signals_table_foreign_key_constraints():
    """Foreign keys prevent orphaned records"""

@pytest.mark.local_only
def test_trades_table_check_constraints():
    """Check constraints enforce valid data"""

@pytest.mark.local_only
def test_portfolio_snapshots_temporal_consistency():
    """Snapshots maintain temporal order"""

@pytest.mark.local_only
def test_audit_trail_completeness():
    """Every order has corresponding audit entries"""
```

---

## 📂 Neue Verzeichnisstruktur

```
tests/
├── unit/                     # Schnelle Unit-Tests (CI)
│   ├── test_risk_engine_core.py
│   ├── test_risk_engine_edge_cases.py
│   ├── test_execution_simulator.py
│   ├── test_mexc_perpetuals.py
│   └── test_position_sizing.py
│
├── integration/              # Integration mit Mocks (CI)
│   └── test_event_pipeline.py
│
├── e2e/                      # E2E mit Containern (lokal)
│   ├── test_docker_compose_full_stack.py
│   ├── test_redis_postgres_integration.py
│   └── test_event_flow_pipeline.py
│
└── local/                    # ✨ NEU: Erweiterte lokale Tests
    ├── conftest.py           # Fixtures für lokale Tests
    ├── service/              # Service-spezifische Tests
    │   ├── test_signal_engine_service.py
    │   ├── test_risk_manager_service.py
    │   └── test_execution_service.py
    ├── integration/          # Multi-Service-Integration
    │   ├── test_signal_to_risk_integration.py
    │   ├── test_risk_to_execution_integration.py
    │   └── test_full_pipeline_integration.py
    ├── performance/          # Performance-Tests
    │   ├── test_performance_redis.py
    │   └── test_performance_postgres.py
    ├── resilience/           # Chaos-Tests
    │   ├── test_resilience_container_restart.py
    │   └── test_resilience_database.py
    └── data_integrity/       # Data-Integrity-Tests
        └── test_data_integrity_postgres.py
```

---

## 🏗️ Implementierungs-Reihenfolge

### Phase 1: Service-Tests (Prio 1)
1. `test_risk_manager_service.py` - **KRITISCH** (nur 3 Tests vorhanden!)
2. `test_signal_engine_service.py`
3. `test_execution_service.py`

### Phase 2: Integration-Tests (Prio 2)
4. `test_signal_to_risk_integration.py`
5. `test_risk_to_execution_integration.py`
6. `test_full_pipeline_integration.py`

### Phase 3: Performance-Tests (Prio 3)
7. `test_performance_redis.py`
8. `test_performance_postgres.py`

### Phase 4: Resilience-Tests (Nice-to-Have)
9. `test_resilience_container_restart.py`
10. `test_resilience_database.py`

### Phase 5: Data-Integrity (Nice-to-Have)
11. `test_data_integrity_postgres.py`

---

## 🔧 Neue Fixtures (`tests/local/conftest.py`)

```python
import pytest
import docker
import redis
import psycopg2
import time
from typing import Generator

@pytest.fixture(scope="session")
def docker_client() -> docker.DockerClient:
    """Docker client for container control"""
    return docker.from_env()

@pytest.fixture(scope="function")
def redis_client() -> Generator[redis.Redis, None, None]:
    """Redis client connected to cdb_redis"""
    client = redis.Redis(
        host="localhost",
        port=6379,
        password=os.getenv("REDIS_PASSWORD"),
        decode_responses=True
    )
    yield client
    client.close()

@pytest.fixture(scope="function")
def postgres_connection() -> Generator[psycopg2.connection, None, None]:
    """PostgreSQL connection to cdb_postgres"""
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        dbname="claire_de_binare",
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD")
    )
    yield conn
    conn.close()

@pytest.fixture(scope="function")
def restart_container():
    """Helper to restart a container"""
    def _restart(container_name: str, wait_seconds: int = 10):
        client = docker.from_env()
        container = client.containers.get(container_name)
        container.restart()
        time.sleep(wait_seconds)
    return _restart

@pytest.fixture(scope="function")
def wait_for_health():
    """Helper to wait for container health"""
    def _wait(container_name: str, timeout: int = 30):
        client = docker.from_env()
        start_time = time.time()
        while time.time() - start_time < timeout:
            container = client.containers.get(container_name)
            if container.health == "healthy":
                return True
            time.sleep(1)
        return False
    return _wait
```

---

## 📊 Erwartete Test-Statistik nach Implementierung

| Kategorie | Vorher | Nachher | Delta |
|-----------|--------|---------|-------|
| **Unit-Tests** | 83 | 83 | 0 |
| **Integration-Tests** | 2 | 2 | 0 |
| **E2E-Tests** | 18 | 18 | 0 |
| **Service-Tests** | 0 | 25 | **+25** |
| **Service-Integration** | 0 | 12 | **+12** |
| **Performance-Tests** | 0 | 7 | **+7** |
| **Resilience-Tests** | 0 | 8 | **+8** |
| **Data-Integrity** | 0 | 6 | **+6** |
| **GESAMT** | **103** | **161** | **+58** |

---

## ✅ Definition of Done

Für jeden neuen Test gilt:

1. ✅ **Marker gesetzt**: `@pytest.mark.local_only` + optional `@pytest.mark.slow`
2. ✅ **Docstring**: Klare Beschreibung
3. ✅ **AAA-Pattern**: Arrange-Act-Assert
4. ✅ **Cleanup**: Fixtures räumen auf
5. ✅ **Deterministisch**: Keine Flaky-Tests
6. ✅ **Dokumentiert**: In `LOCAL_E2E_TESTS.md` erwähnt

---

## 🚀 Ausführungs-Commands

```bash
# Alle lokalen Service-Tests
pytest -v -m local_only tests/local/service/

# Alle lokalen Integration-Tests
pytest -v -m local_only tests/local/integration/

# Alle Performance-Tests
pytest -v -m "local_only and slow" tests/local/performance/

# Alle Resilience-Tests
pytest -v tests/local/resilience/

# Alle neuen lokalen Tests
pytest -v -m local_only tests/local/
```

---

**Version**: 1.0-draft
**Autor**: Claire Local Test Orchestrator
**Status**: Design abgeschlossen, ready für Implementierung
