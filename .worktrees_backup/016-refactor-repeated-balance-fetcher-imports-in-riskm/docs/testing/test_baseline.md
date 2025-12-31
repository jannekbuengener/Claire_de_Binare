# Test Baseline Report

**Generated**: 2025-12-27
**Commit**: a0fa11b (Post Issue #123)

## Executive Summary

| Metric | Count | Percentage |
|--------|-------|------------|
| **Total Tests** | 56 | 100% |
| **Unit Tests** | 42 | 75.0% |
| **Integration Tests** | 7 | 12.5% |
| **E2E Tests** | 5 | 8.9% |
| **Performance Tests** | 1 | 1.8% |
| **Chaos Tests** | 1 | 1.8% |

**Code Coverage**: 4.85% (baseline - tests collected, not executed)

---

## Test Inventory by Category

### Unit Tests (42 tests)

**DB Writer Service** (3 tests):
- test_service_initialization
- test_config_validation
- test_event_persistence

**Execution Service** (3 tests):
- test_service_initialization
- test_config_validation
- test_order_submission

**Market Service** (3 tests):
- test_service_initialization
- test_config_validation
- test_market_data_ingestion

**PSM Service** (4 tests):
- test_service_initialization
- test_config_validation
- test_event_sourcing_replay
- test_snapshot_creation

**Risk Service** (3 tests):
- test_service_initialization
- test_config_validation
- test_action_masking

**Signal Service** (3 tests):
- test_service_initialization
- test_config_validation
- test_signal_generation

**Core Domain** (23 tests):
- Clock: 4 tests (deterministic mode, injection, guardrails)
- Event: 4 tests (creation, type enum, ID determinism)
- Models: 3 tests (signal, position, order creation)
- Secrets: 4 tests (Docker secrets, env vars, defaults)
- Seed: 4 tests (set/get, determinism, default)
- UUID Generator: 4 tests (returns string, deterministic, seeded, hex length)

### Integration Tests (7 tests)

**MEXC Testnet** (7 tests):
- Offline Mode: 4 tests (balance, USDT, ticker, order status)
- External Mode: 3 tests (client init, balance, ticker)

### E2E Tests (5 tests)

**Deterministic Replay** (5 tests):
- test_fixed_clock_determinism
- test_seed_manager_determinism
- test_uuid_generator_determinism
- test_event_hash_consistency
- test_event_replay_determinism

### Performance Tests (1 test)

- test_baseline_smoke

### Chaos Tests (1 test)

- test_resilience_suite_gate

---

## Critical Path Tests (Paper Trading E2E)

**Location**: `tests/e2e/test_paper_trading_p0.py`

**Known P0 Tests** (from previous run):
1. ✅ test_order_to_execution_flow
2. ✅ test_order_results_schema
3. ✅ test_stream_persistence
4. ✅ test_subscriber_count
5. ❌ test_replay_determinism (Unicode encoding issue - known bug)

**Pass Rate**: 4/5 (80%) - 1 pre-existing encoding failure

**Related Issues**:
- #227: P0 E2E - Validate stabilized paper-trading tests
- #260: Signal.from_dict() missing - blocks TC-P0-003/004
- #224: order_results not published

---

## Coverage Analysis

**Services with 0% Coverage** (untested in current run):
- allocation (263 lines)
- db_writer (216 lines)
- execution (992 lines)
- regime (247 lines)
- risk (865 lines)
- signal (160 lines)

**Core with Partial Coverage**:
- event.py: 71%
- models.py: 71%
- secrets.py: 50%
- clock.py: 51%
- seed.py: 69%
- uuid_gen.py: 52%

**Note**: Low coverage expected for collect-only run. Coverage improves when tests execute.

---

## Known Gaps & Issues

### Blocking Issues
1. **#260**: Signal.from_dict() missing - blocks TC-P0-003/004 E2E tests
2. **No test markers**: Tests lack unit/integration/e2e markers (addressed in #271)
3. **No isolated test stack**: Tests run against dev stack (addressed in #274)
4. **No deterministic fixtures**: DB state not reproducible (addressed in #275)

### Test Stability Issues
- Replay determinism test fails on Windows (charmap encoding)
- No flaky detection mechanism (#276)
- No repeat-run validation

---

## Recommendations

**Immediate Actions** (P0):
1. Implement test markers taxonomy (#271)
2. Fix Signal.from_dict() bug (#260)
3. Create deterministic PostgreSQL fixtures (#275)
4. Build isolated test stack overlay (#274)

**Short-term** (P1):
- Add flaky detection loop (#276)
- Increase unit test coverage to 60%+
- Stabilize E2E tests to ≥95% pass rate

**Long-term** (P2):
- Reach 80% code coverage target
- Implement chaos engineering suite
- Add performance regression testing

---

## Baseline Validation

**Checklist**:
- ✅ Test inventory collected (56 tests)
- ✅ Tests categorized (unit/integration/e2e/performance/chaos)
- ✅ Critical path identified (paper trading E2E)
- ✅ Known gaps documented
- ✅ Baseline report generated

**Next Steps**: Execute Issue #271 (Markers Taxonomy)
