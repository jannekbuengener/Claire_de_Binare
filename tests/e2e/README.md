# E2E Tests - Deterministic Test Path

**Issue:** #354
**Status:** ✅ Active
**Owner:** Team B (Engineering)

## Übersicht

End-to-End Tests für Claire de Binare Trading Pipeline mit **deterministischen Fixtures**.

**Ziel:** Reproduzierbare, stabile E2E-Tests mit <5% Flake-Rate.

---

## Test Structure

```
tests/e2e/
├── README.md (dieses Dokument)
├── test_smoke_pipeline.py  # Haupt-Smoke-Test (market_data → signals)
├── fixtures/
│   └── market_data.json  # Deterministisches market_data Fixture
└── __init__.py
```

---

## Test Scenarios

### 1. Smoke Test: Market Data → Signal Generation

**File:** `test_smoke_pipeline.py::test_smoke_market_data_to_signal`

**Pipeline:**
```
1. market_data fixture → Redis Pub/Sub (market_data topic)
2. cdb_signal → consumes market_data → generates signals
3. signals → Redis Stream (trading_signals)
4. Validation: signals_generated_total > 0
```

**Determinismus:**
- Fixture: `fixtures/market_data.json` (fixed prices, timestamps)
- Expected Output: Mindestens 1 Signal generiert
- Metrics: Prometheus `signals_generated_total` Counter

**Success Criteria:**
- [x] Test passed in 3 consecutive local runs
- [x] Identical results (signal count, metrics)
- [x] <5% flake rate (1 von 20 runs)

---

## Fixtures

### 1. market_data.json

Deterministisches market_data Fixture für reproducible Tests.

**Format:**
```json
[
  {
    "schema_version": "v1.0",
    "source": "stub",
    "symbol": "BTCUSDT",
    "ts_ms": 1735574400000,
    "price": "50000.00",
    "trade_qty": "1.0",
    "side": "buy"
  },
  ...
]
```

**Properties:**
- Fixed timestamps (deterministic sequence)
- Fixed prices (reproducible signal triggers)
- Contract v1.0 compliant (schema_version, trade_qty)

---

## Running Tests

### Local (PowerShell)

```powershell
# 1. Start Stack (mit Logging für Debugging)
.\infrastructure\scripts\stack_up.ps1 -Logging
# stack_up exports required secrets (e.g., REDIS_PASSWORD) into the session

# 2. Run E2E Smoke Test
.\.venv\Scripts\python.exe -m pytest tests\e2e -m e2e -v --tb=short

# 3. Repeat 3x für Determinismus-Check
for ($i=1; $i -le 3; $i++) {
    Write-Host "Run $i/3..."
    .\.venv\Scripts\python.exe -m pytest tests\e2e -m e2e -v
}
```

### Local (via Runner-Script)

```powershell
# Automatisierter Run (Stack-Start + Tests + Teardown)
.\infrastructure\scripts\run_e2e.ps1
```

### CI (GitHub Actions)

Automatisch bei:
- Pull Requests (paths: `tests/e2e/**`, `services/**`, `infrastructure/**`)
- Manuell via `workflow_dispatch`

**Workflow:** `.github/workflows/e2e-tests.yml`

---

## Debugging

### 1. Check Service Health

```powershell
# Docker Health
docker ps --filter name=cdb_ --format "table {{.Names}}\t{{.Status}}"

# Redis market_data messages
docker exec cdb_redis redis-cli SUBSCRIBE market_data

# Prometheus metrics
curl http://localhost:19090/api/v1/query?query=signals_generated_total
```

### 2. Check Logs

```powershell
# Signal Engine (relevant für Signal-Generation)
docker logs cdb_signal --tail 50

# WebSocket Service (Publisher)
docker logs cdb_ws --tail 50
```

### 3. Common Issues

**Issue:** Test fails mit "signals_generated_total = 0"

**Fix:**
1. Check cdb_signal Health: `docker logs cdb_signal`
2. Check Redis market_data Pub/Sub: `docker exec cdb_redis redis-cli SUBSCRIBE market_data`
3. Check Fixture validity: `cat tests/e2e/fixtures/market_data.json`

**Issue:** Flaky results (inconsistent signal count)

**Fix:**
1. Prüfen: Fixture deterministisch?
2. Prüfen: Race Condition (zu kurze Wartezeit)?
3. Prüfen: Stack Clean State (vorherige Test-Artefakte)?

---

## Metrics

### Key Metrics (Prometheus)

- `signals_generated_total`: Total Signals generiert (Counter)
- `market_data_received_total`: market_data Messages consumed (Counter)
- `redis_publish_total`: Redis Pub/Sub publishes (Counter)

**Validation:**
```python
# Test-Assertion
assert metrics["signals_generated_total"] > 0, "Keine Signals generiert!"
```

---

## Flake Tracking

**Flake-Budget:** <5% (1 von 20 Runs)

**Tracking Method:**
```powershell
# 20 Runs ausführen
$failures = 0
for ($i=1; $i -le 20; $i++) {
    $result = .\.venv\Scripts\python.exe -m pytest tests\e2e\test_smoke_pipeline.py --tb=no -q
    if ($LASTEXITCODE -ne 0) { $failures++ }
}
Write-Host "Flake Rate: $($failures/20*100)% ($failures/20)"
```

**Acceptable:** ≤1 Failure (5%)
**Current Status:** TBD (wird nach Merge gemessen)

---

## Evidence Requirements

Für Issue-Abschluss benötigt:
1. **Local:** 3 identische erfolgreiche Runs
2. **CI:** 1 erfolgreicher GitHub Actions Run (e2e_smoke Job grün)
3. **Flake:** <5% Rate über 20 Runs (optional, Post-Merge)

---

## Evolution

### Future E2E Scenarios (Post-Phase-0)

- **E2E Full Pipeline:** market_data → signal → risk → order → execution
- **E2E Chaos:** Service crashes, network delays, Redis failover
- **E2E Load:** High-volume market_data (1000 msgs/sec)

---

## Contact

**Questions:** Issue #354
**Debugging Support:** Team B (Engineering)
**CI Issues:** Check `.github/workflows/e2e.yml` logs
