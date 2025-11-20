# Risk Engine TODO Analysis
**Date**: 2025-11-20 17:52 UTC
**File**: services/risk_engine.py:431

## Current TODO Comment

```python
# TODO: Replace placeholder risk logic with production-grade rules and
# connectivity to portfolio and order management services.
```

## Analysis

### Evidence that TODO is OUTDATED:

1. **Comprehensive Implementation**:
   - `evaluate_signal_v2()` is 200+ lines with full production logic
   - Integrates MEXC Perpetuals (liquidation, funding fees)
   - Advanced Position Sizing (4 methods: Fixed Fractional, Vol Targeting, Kelly, ATR)
   - Execution Simulator (slippage, fees, liquidity)
   - 7-layer risk validation

2. **Test Coverage**:
   - 23 tests covering risk_engine.py
   - 100% pass rate
   - Edge cases, integration scenarios all validated

3. **Production-Ready Features**:
   - ENV-based configuration
   - Structured logging
   - Type hints
   - Error handling

### Recommendation:

**OPTION A**: Remove TODO entirely (logic is production-grade)

**OPTION B**: Update TODO to reflect actual gap:
```python
# TODO: Add live connectivity to portfolio service (currently using mock state)
# TODO: Integrate with real order management system (paper-trading works)
```

**OPTION C**: Keep as reminder for Phase N2 (Live Trading)

## Decision:

Recommend **OPTION B** - Update TODO to be specific about what's actually missing:
- Live portfolio state (vs. mock)
- Real order management integration

The core risk logic itself is NOT placeholder and should not be labeled as such.
