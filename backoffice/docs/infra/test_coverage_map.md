# Test-Coverage-Map - Service/Module → Tests

**Erstellt von**: devops-infrastructure-architect (in Abstimmung mit software-jochen)
**Datum**: 2025-11-16
**Scope**: Unit-, Integration-, E2E-Tests im Repo

---

## Services/Module

| Service/Modul | Tests vorhanden? | Typ | Pfad | Abdeckung | Lücken |
|---------------|------------------|-----|------|-----------|--------|
| **cdb_ws** (WebSocket Screener) | ❌ Nein | — | — | 0% | Keine Unit-/Integration-Tests |
| **cdb_rest** (REST Screener) | ❌ Nein | — | — | 0% | Keine Unit-/Integration-Tests |
| **cdb_core** (Signal Engine) | ❌ Nein | — | — | 0% | Keine Service-spezifischen Tests |
| **cdb_risk** (Risk Manager) | ❌ Nein | — | — | 0% | Keine Service-spezifischen Tests |
| **cdb_execution** (Execution Service) | ❌ Nein | — | — | 0% | Keine Service-spezifischen Tests |
| **query_service** | ⚠️ Partial | Unit | `backoffice/services/query_service/test_service.py` | Unklar | Service nicht in docker-compose.yml (Legacy?) |
| **Repository** (allgemein) | ✅ Ja | Unit | `tests/unit/test_smoke_repo.py` | Basic | Smoke-Tests, keine Logik-Tests |
| **Docker Compose** | ✅ Ja | Integration | `tests/integration/test_compose_smoke.py` | Basic | Health-Checks, keine Event-Flow-Tests |

---

## Test-Typen

### Unit-Tests

| Pfad | Scope | Status | Bemerkungen |
|------|-------|--------|-------------|
| `tests/unit/test_smoke_repo.py` | Repository-Smoke | ✅ Vorhanden | Prüft grundlegende Repo-Struktur (Files, Ordner) |
| `backoffice/services/query_service/test_service.py` | query_service | ⚠️ Unklar | Service nicht in docker-compose.yml → Test vermutlich Legacy |

**Lücken**:
- Keine Service-Logik-Tests (Signal-Generierung, Risk-Checks, Order-Execution)
- Keine ENV-Parsing-Tests (kritisch wegen SR-002: ENV-Naming-Konflikt!)
- Keine Redis-Event-Handling-Tests (Pub/Sub-Logik)

### Integration-Tests

| Pfad | Scope | Status | Bemerkungen |
|------|-------|--------|-------------|
| `tests/integration/test_compose_smoke.py` | Docker Compose Health-Checks | ✅ Vorhanden | Prüft, ob Services hochfahren und healthy sind |

**Lücken**:
- Keine End-to-End-Event-Flow-Tests (`market_data` → `signals` → `orders` → `order_results`)
- Keine Redis-Integration-Tests (Pub/Sub-Nachrichtenaustausch)
- Keine Datenbank-Integration-Tests (PostgreSQL-Writes/Reads)
- Keine Prometheus-Scraping-Tests

### E2E-Tests

| Pfad | Scope | Status | Bemerkungen |
|------|-------|--------|-------------|
| — | — | ❌ Keine | Keine End-to-End-Tests vorhanden |

**Kritische E2E-Szenarien (fehlen komplett)**:
1. **Happy Path**: Marktdaten → Signal → Risk-Check → Order → Execution → DB-Persistenz
2. **Risk-Limit-Trigger**: Signal → Risk-Check FAIL (Daily Drawdown) → Trading-Halt
3. **Circuit-Breaker**: Marktanomalien → Circuit-Breaker → Pause → Retry → Resume
4. **Data-Stale**: Keine Marktdaten >30s → Pause → Neue Daten → Resume

---

## Test-Abdeckung nach Kategorie

### Nach Service-Typ

| Service-Typ | Services | Test-Abdeckung | Priorität für Tests |
|-------------|----------|----------------|---------------------|
| **Screener** | `cdb_ws`, `cdb_rest` | 0% | 🟡 MEDIUM (Input-Layer, einfacher) |
| **Signal Engine** | `cdb_core` | 0% | 🟠 HIGH (Kernlogik) |
| **Risk Manager** | `cdb_risk` | 0% | 🔴 CRITICAL (Sicherheitsrelevant!) |
| **Execution** | `cdb_execution` | 0% | 🟠 HIGH (Order-Handling) |
| **Infrastruktur** | Redis, Postgres, Prometheus, Grafana | Integration-Smoke (Basic) | 🟢 LOW (Standard-Images) |

### Nach Test-Typ

| Test-Typ | Abdeckung | Anzahl Tests | Bemerkungen |
|----------|-----------|--------------|-------------|
| **Unit** | 🟢 Minimal | 2 (smoke + query_service) | Nur grundlegende Struktur-Tests |
| **Integration** | 🟡 Basic | 1 (compose_smoke) | Nur Health-Checks, keine Event-Flows |
| **E2E** | 🔴 Keine | 0 | Kritische Lücke! |

---

## Empfohlene Test-Erweiterungen

### 🔴 CRITICAL (Sofort)

1. **Risk Manager Unit-Tests**:
   - ENV-Parsing (SR-002: Dezimal vs. Prozent)
   - Limit-Checks (Daily Drawdown, Exposure, Position Size)
   - Alert-Generierung (RISK_LIMIT, CIRCUIT_BREAKER)
   - **Pfad**: `tests/unit/test_risk_manager_limits.py`

2. **Risk Manager Integration-Tests**:
   - Redis-Event-Handling (`signals` → Risk-Check → `orders` oder `alerts`)
   - **Pfad**: `tests/integration/test_risk_event_flow.py`

### 🟠 HIGH (Mittelfristig)

3. **Signal Engine Unit-Tests**:
   - Signal-Generierung (Momentum-Strategie)
   - Threshold-Checks (`SIGNAL_THRESHOLD`, `MIN_VOLUME`)
   - **Pfad**: `tests/unit/test_signal_engine.py`

4. **Execution Service Unit-Tests**:
   - Order-Parsing
   - PostgreSQL-Writes (mit Mock/Test-DB)
   - **Pfad**: `tests/unit/test_execution_service.py`

5. **E2E Happy Path**:
   - Mock-Marktdaten → Signal Engine → Risk Manager → Execution → DB-Check
   - **Pfad**: `tests/e2e/test_happy_path.py`

### 🟡 MEDIUM (Nice-to-have)

6. **Screener Unit-Tests**:
   - MEXC-API-Mock-Responses
   - Redis-Publish-Logik
   - **Pfad**: `tests/unit/test_screeners.py`

7. **E2E Risk-Scenarios**:
   - Daily Drawdown Limit → Trading-Halt
   - Circuit-Breaker → Pause → Resume
   - **Pfad**: `tests/e2e/test_risk_scenarios.py`

---

## Test-Setup-Empfehlungen

### Fixtures (ergänzen in `tests/conftest.py`)

```python
@pytest.fixture
def mock_risk_env(monkeypatch):
    """Mock Risk-Parameter-ENV für Tests (SR-002-konform: Dezimal)"""
    env_vars = {
        "MAX_DAILY_DRAWDOWN_PCT": "0.05",  # 5%
        "MAX_POSITION_PCT": "0.10",        # 10%
        "MAX_EXPOSURE_PCT": "0.50",        # 50%
        "STOP_LOSS_PCT": "0.02",           # 2%
        "MAX_SLIPPAGE_PCT": "0.01",        # 1%
        "MAX_SPREAD_MULTIPLIER": "5.0",
        "DATA_STALE_TIMEOUT_SEC": "30",
    }
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    return env_vars

@pytest.fixture
def sample_signal():
    """Sample Trading-Signal für Tests"""
    return {
        "symbol": "BTC_USDT",
        "signal_type": "BUY",
        "strength": 5.0,
        "price": 50000.0,
        "timestamp": 1736600000
    }

@pytest.fixture
def redis_test_client():
    """Redis-Client für Integration-Tests (echte Verbindung)"""
    import redis
    client = redis.Redis(
        host="localhost",
        port=6379,
        password=os.getenv("REDIS_PASSWORD"),
        db=1  # Test-DB (nicht 0)
    )
    yield client
    client.flushdb()  # Cleanup nach Test
```

### Test-Struktur (erweitert)

```
tests/
├── conftest.py                       # Erweiterte Fixtures
├── unit/
│   ├── test_smoke_repo.py            # ✅ Vorhanden
│   ├── test_risk_manager_limits.py   # 🔴 NEU: CRITICAL
│   ├── test_signal_engine.py         # 🟠 NEU: HIGH
│   └── test_execution_service.py     # 🟠 NEU: HIGH
├── integration/
│   ├── test_compose_smoke.py         # ✅ Vorhanden
│   ├── test_risk_event_flow.py       # 🔴 NEU: CRITICAL
│   └── test_redis_pubsub.py          # 🟡 NEU: MEDIUM
└── e2e/
    ├── test_happy_path.py            # 🟠 NEU: HIGH
    └── test_risk_scenarios.py        # 🟡 NEU: MEDIUM
```

---

## Zusammenfassung

### Aktuelle Test-Situation

- **Vorhanden**: Nur grundlegende Smoke-Tests (Repo-Struktur, Docker Compose Health-Checks)
- **Fehlend**: Service-Logik-Tests, Risk-Engine-Tests, E2E-Tests
- **Kritischste Lücke**: **Risk Manager** (sicherheitsrelevant, SR-002-Risiko!)

### Empfohlene Prioritäten

1. **Sofort**: Risk Manager Unit-/Integration-Tests (SR-002-Absicherung)
2. **Vor Production**: E2E Happy Path, Signal Engine Unit-Tests
3. **Post-MVP**: Screener-Tests, erweiterte E2E-Szenarien

### Test-Coverage-Ziel (MVP)

| Komponente | Ziel-Abdeckung | Aktuell | Delta |
|------------|----------------|---------|-------|
| **Risk Manager** | 80% (Unit + Integration) | 0% | +80% |
| **Signal Engine** | 70% (Unit) | 0% | +70% |
| **Execution Service** | 60% (Unit + Integration) | 0% | +60% |
| **E2E** | 3 Szenarien (Happy Path + 2 Risk-Scenarios) | 0 | +3 |

**Geschätzter Aufwand**: 3-5 Tage für CRITICAL-Tests (Risk Manager + E2E Happy Path)
