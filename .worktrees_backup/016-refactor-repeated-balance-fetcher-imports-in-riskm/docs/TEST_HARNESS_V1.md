# Test Harness v1 - CDB Test Execution Guide

**Team:** B (Dev-Stream)
**Version:** 1.0
**Date:** 2025-12-29
**Status:** Deliverable

---

## Quick Start

```powershell
# Activate venv (Windows)
.\.venv\Scripts\Activate.ps1

# OR: Direct execution
.venv/Scripts/python.exe -m pytest

# Minimal smoke test
.venv/Scripts/python.exe -m pytest tests/unit/test_models.py -v
```

---

## Test Execution Commands

### 1. Smoke Suite (P0 - Fast)
```powershell
# Core models + clock + secrets (< 1s)
.venv/Scripts/python.exe -m pytest tests/unit/test_models.py tests/unit/test_clock.py tests/unit/test_secrets.py -v
```

### 2. Unit Tests (Isolated, No Docker)
```powershell
# All unit tests
.venv/Scripts/python.exe -m pytest tests/unit/ -v

# Specific service
.venv/Scripts/python.exe -m pytest tests/unit/signal/ -v
.venv/Scripts/python.exe -m pytest tests/unit/risk/ -v
```

### 3. E2E Suite (Requires Docker Stack)
```powershell
# Prerequisites: Docker stack running
# Check: docker ps --filter "name=cdb_"

# P0 Happy Path
.venv/Scripts/python.exe -m pytest -m e2e tests/e2e/test_paper_trading_p0.py -v

# Full E2E (longer)
.venv/Scripts/python.exe -m pytest tests/e2e/ -v
```

### 4. Integration Tests (Partial Docker)
```powershell
# Emergency stop workflow
.venv/Scripts/python.exe -m pytest tests/integration/test_emergency_stop.py -v

# MEXC testnet (requires API credentials)
.venv/Scripts/python.exe -m pytest tests/integration/test_mexc_testnet.py -v
```

### 5. Chaos & Resilience (Advanced)
```powershell
# Fault injection (requires running stack)
.venv/Scripts/python.exe -m pytest tests/resilience/test_fault_injection.py -v

# Chaos suite gate
.venv/Scripts/python.exe -m pytest tests/chaos/test_resilience.py -v
```

---

## Test Markers

```python
# Available markers (from pytest.ini):
@pytest.mark.e2e          # End-to-end tests (requires full stack)
@pytest.mark.integration  # Integration tests (partial stack)
@pytest.mark.slow         # Tests > 5s
@pytest.mark.chaos        # Chaos engineering tests
```

**Usage:**
```powershell
# Run only E2E tests
.venv/Scripts/python.exe -m pytest -m e2e

# Skip slow tests
.venv/Scripts/python.exe -m pytest -m "not slow"
```

---

## Test Coverage Report

```powershell
# Generate coverage report
.venv/Scripts/python.exe -m pytest --cov=services --cov=core --cov-report=html

# Open: htmlcov/index.html
```

---

## Definition of Done (DoD)

### For Pull Requests:
- [ ] Smoke suite PASSES (test_models + test_clock + test_secrets)
- [ ] Relevant unit tests PASS
- [ ] No new failures in existing tests
- [ ] Coverage delta: ≥ 0% (no decrease)

### For E2E Validation:
- [ ] Docker stack healthy: `docker ps --filter "name=cdb_"`
- [ ] E2E P0 suite PASSES: `pytest -m e2e tests/e2e/test_paper_trading_p0.py`
- [ ] Key metrics visible:
  - `signals_generated_total > 0`
  - `risk_pending_orders_total >= 0`
  - No ERROR logs in services

---

## Troubleshooting

### Problem: "No module named pytest"
**Solution:** Use venv python, not system python
```powershell
.venv/Scripts/python.exe -m pytest
```

### Problem: "Collection errors"
**Check:**
```powershell
.venv/Scripts/python.exe -m pytest --collect-only 2>&1 | grep ERROR
```

### Problem: E2E tests fail with connection errors
**Solution:** Ensure Docker stack is running
```powershell
docker-compose -f infrastructure/compose/base.yml -f infrastructure/compose/dev.yml up -d
```

### Problem: Tests hang or timeout
**Solution:** Check for leaked resources
```powershell
# Kill stuck pytest processes
taskkill /F /IM python.exe

# Clean pytest cache
rm -rf .pytest_cache
```

---

## Test Statistics (2025-12-29)

```
Total Tests Collected: 228
├─ Unit:        ~180
├─ E2E:         ~20
├─ Integration: ~15
├─ Chaos:       ~5
├─ Resilience:  ~5
└─ Performance: ~3

Smoke Suite: 3 tests, < 1s
Full Suite:  ~30-60s (without Docker)
E2E Suite:   ~2-5min (with Docker)
```

---

## Next Steps (Out of Scope for v1)

- [ ] CI/CD integration (GitHub Actions)
- [ ] Parallel test execution
- [ ] Test data fixtures library
- [ ] Performance regression tracking
- [ ] Mutation testing

---

**Deliverable:** Test Harness v1 ✅
**Handover:** See HANDOVERS_TO_TEAM_A.md for infra requirements
