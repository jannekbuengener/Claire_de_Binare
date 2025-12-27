# Pytest Markers Taxonomy

**Purpose**: Standardize test categorization for selective execution locally and in CI.

---

## Available Markers

| Marker | Description | Execution | Coverage |
|--------|-------------|-----------|----------|
| `unit` | Fast, isolated unit tests | CI + Local | 47 tests |
| `integration` | Tests with mock/stub services | CI + Local | 4 tests |
| `e2e` | End-to-end tests with real containers | Local only | 5 tests |
| `external` | External network tests (real APIs) | Opt-in only | 3 tests |
| `slow` | Tests with >10s runtime | Manual | 1 test |
| `chaos` | Destructive resilience tests | Local only | 1 test |
| `local_only` | Explicitly local execution (not in CI) | Local only | 2 tests |
| `feature` | Feature workflow validation | CI + Local | 0 tests |
| `mandatory` | Must pass for feature deployment | CI + Local | 0 tests |

**Total Tests**: 56 (not all mutually exclusive - some tests have multiple markers)

---

## Usage Examples

### Run Only Unit Tests
```bash
pytest -m "unit"
```

### Run Only E2E Tests (requires E2E_RUN=1)
```bash
E2E_RUN=1 pytest -m "e2e" -v
```

### Run Only Integration Tests
```bash
pytest -m "integration"
```

### Run External Tests (requires credentials)
```bash
CDB_EXTERNAL_TESTS=1 pytest -m "external" -v
```

### Exclude Slow Tests
```bash
pytest -m "not slow"
```

### Run All Non-Local Tests (CI-safe)
```bash
pytest -m "not local_only"
```

### Run Multiple Markers (Unit + Integration)
```bash
pytest -m "unit or integration"
```

### Run Critical Path (Unit + Integration + E2E)
```bash
E2E_RUN=1 pytest -m "unit or integration or e2e"
```

---

## Marker Definitions (pytest.ini)

```ini
[pytest]
markers =
    unit: schnelle, isolierte Unit-Tests (CI + lokal)
    integration: Tests mit Mock-Services (CI + lokal)
    external: External network tests (opt-in only)
    e2e: End-to-End Tests mit echten Containern (NUR lokal)
    local_only: Explizit nur lokal ausführen (nicht in CI)
    slow: Tests mit >10s Laufzeit
    chaos: Chaos/Resilience Tests - DESTRUKTIV! (NUR lokal)
    feature: Feature workflow tests for deployment validation
    mandatory: Tests that must pass for feature deployment
```

---

## Test Inventory by Marker

### Unit Tests (47)
**Core Domain** (23 tests):
- `tests/unit/test_models.py`: Signal, Position, Order creation (3 tests)
- `tests/unit/test_event.py`: Event domain objects (4 tests)
- `tests/unit/test_secrets.py`: Secrets management (4 tests)
- `tests/unit/test_clock.py`: Clock utilities (4 tests)
- `tests/unit/test_seed.py`: Seed/RNG determinism (4 tests)
- `tests/unit/test_uuid_gen.py`: UUID generation (4 tests)

**Service Tests** (18 tests):
- `tests/unit/db_writer/test_service.py`: DB Writer (3 tests)
- `tests/unit/execution/test_service.py`: Execution Service (3 tests)
- `tests/unit/market/test_service.py`: Market Data (3 tests)
- `tests/unit/psm/test_service.py`: Platform State Manager (4 tests)
- `tests/unit/risk/test_service.py`: Risk Management (3 tests)
- `tests/unit/signal/test_service.py`: Signal Service (3 tests)

**Replay Tests** (5 tests):
- `tests/replay/test_deterministic_replay.py`: Event sourcing determinism (5 tests)

**Performance Baseline** (1 test):
- `tests/performance/test_baseline_measurements.py`: Smoke test

### Integration Tests (4)
**MEXC Testnet** (4 tests):
- `tests/integration/test_mexc_testnet.py::TestMexcTestnetOffline`: Offline stub tests (4 tests)

### E2E Tests (5)
**Paper Trading P0** (5 tests):
- `tests/e2e/test_paper_trading_p0.py`: Order → Execution → Results flow (5 tests)
  - Requires: `E2E_RUN=1`
  - Requires: Docker stack running
  - Requires: Redis accessible

### External Tests (3)
**MEXC Testnet External** (3 tests):
- `tests/integration/test_mexc_testnet.py::TestMexcTestnetExternal`: Real API calls (3 tests)
  - Requires: `CDB_EXTERNAL_TESTS=1`
  - Requires: `MEXC_API_KEY` and `MEXC_API_SECRET`

### Slow Tests (1)
- `tests/performance/test_baseline_measurements.py::test_baseline_smoke`
  - Requires: `PERF_BASELINE_RUN=1`

### Chaos Tests (1)
- `tests/chaos/test_resilience.py::test_resilience_suite_gate`
  - Requires: `RUN_CHAOS_TESTS=1`

---

## CI Configuration

### Default CI Run (Fast Feedback)
```bash
pytest -m "unit or integration" --cov=core --cov=services --cov-fail-under=80
```

### Full CI Run (Optional)
```bash
# Unit + Integration (fast)
pytest -m "unit or integration"

# E2E (slow, requires stack)
E2E_RUN=1 pytest -m "e2e" --no-cov
```

### Local Development
```bash
# Quick feedback loop
pytest -m "unit" --maxfail=1

# Pre-commit validation
pytest -m "unit or integration"

# Full suite (requires stack)
E2E_RUN=1 pytest
```

---

## Migration Checklist

- ✅ All markers defined in `pytest.ini`
- ✅ All 56 tests tagged with appropriate markers
- ✅ Unit tests: 47 tagged
- ✅ Integration tests: 4 tagged
- ✅ E2E tests: 5 tagged
- ✅ Performance tests: 1 tagged
- ✅ Chaos tests: 1 tagged
- ✅ Marker selection validated (`pytest -m "unit"` works)
- ✅ Documentation created (`docs/testing/markers.md`)

---

## Next Steps

1. **Immediate**: Use markers in CI pipeline (`.github/workflows/`)
2. **Short-term**: Add `feature` and `mandatory` markers to new tests
3. **Long-term**: Reach ≥95% E2E pass rate for critical path tests

---

## References

- pytest.ini: Test configuration and marker definitions
- Issue #271: Markers Taxonomy & Tag All Tests
- Issue #268: Test Inventory & Baseline Report
