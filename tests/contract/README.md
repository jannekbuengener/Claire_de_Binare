# Contract Tests

Contract tests validate the integration contracts between components to prevent regression.

## Purpose

Unlike unit tests (which test isolated components) or integration tests (which test end-to-end flows), contract tests verify that:
1. **Data formats** are correctly transformed between components
2. **Schema constraints** are enforced
3. **Backward compatibility** is maintained

## Test Structure

```
tests/contract/
├── __init__.py
├── README.md                    # This file
└── test_signal_schema.py        # Signal → db_writer → DB contract
```

## Running Contract Tests

### Run All Contract Tests
```bash
pytest tests/contract/ -v
```

### Run Specific Contract Test
```bash
pytest tests/contract/test_signal_schema.py -v
```

### Run Single Test Case
```bash
pytest tests/contract/test_signal_schema.py::TestSignalSchemaContract::test_signal_with_side_buy_maps_to_signal_type_buy -v
```

## Current Contract Tests

### Signal Schema Contract (`test_signal_schema.py`)

**Issue**: #595
**Context**: Signals emit `side` (BUY/SELL), but DB schema expects `signal_type` (buy/sell lowercase)

**What it tests**:
- ✅ `side='BUY'` maps to `signal_type='buy'`
- ✅ `side='SELL'` maps to `signal_type='sell'`
- ✅ Explicit `signal_type` field is preserved
- ✅ Case normalization (BUY → buy, Buy → buy)
- ⚠️  Missing fields → `'unknown'` (fails DB constraint)
- ⚠️  Invalid values → lowercase but fails DB constraint

**Schema Constraint**:
```sql
signal_type VARCHAR(10) NOT NULL CHECK (signal_type IN ('buy', 'sell'))
```

**Test Output Example**:
```bash
$ pytest tests/contract/test_signal_schema.py -v

tests/contract/test_signal_schema.py::TestSignalSchemaContract::test_signal_with_side_buy_maps_to_signal_type_buy PASSED
tests/contract/test_signal_schema.py::TestSignalSchemaContract::test_signal_with_side_sell_maps_to_signal_type_sell PASSED
tests/contract/test_signal_schema.py::TestSignalSchemaContract::test_signal_with_explicit_signal_type_is_preserved PASSED
...

==================== 9 passed, 1 skipped in 0.23s ====================
```

**Failure Detection**:
If the `side → signal_type` mapping in `services/db_writer/db_writer.py` is broken:
```python
# BROKEN CODE (for demonstration):
signal_type = data.get("side")  # Missing .lower() call

# Test would fail with:
# AssertionError: Expected signal_type='buy', got 'BUY'
```

## Adding New Contract Tests

1. Create test file: `tests/contract/test_<component>_contract.py`
2. Document the contract being tested
3. Test happy path (correct transformations)
4. Test edge cases (missing fields, invalid values)
5. Test failure modes (regression detection)
6. Add documentation to this README

## CI Integration

Contract tests run in CI with other test suites:
```bash
pytest tests/  # Includes contract tests
```

**Test Gate**: Contract tests are part of the deterministic test gate (Issue #427, #430)

## Related Issues

- #595: Signal schema contract test
- #427: Deterministic test gate
- #430: CI baseline
- #586: db_writer field mapping
- #587: Signal stuck at 0

---

**Generated**: 2026-01-15
**Maintainer**: CDB Test Team
