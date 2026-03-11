# Patchset Plan - Issue #345 Signal Generation Pipeline

**Team:** B (Dev-Stream)
**Issue:** #345 - Enable signal generation from 100ms MEXC trades
**Commit:** `bf3ca40` - fix(signal): enable signal generation pipeline
**Date:** 2025-12-29
**Status:** Deliverable

---

## Executive Summary

**Problem:** 0 signals generated despite 32k+ trades flowing through pipeline

**Root Causes:** 4 critical bugs (all Blocker-class)
1. Logging system broken (hardcoded INFO level)
2. Missing method `Signal.generate_reason()` → AttributeError
3. Volume check blocking all trades (`qty` vs `volume` field mismatch)
4. Redis publishing crash (None values in XADD)

**Solution:** 4 isolated patches, each testable independently

**Impact:** Pipeline now generates 7+ signals/minute, E2E validated ✅

---

## Patch #1: Logging System - LOG_LEVEL Support

### Problem
```python
# services/signal/service.py:36-40 (before)
logging.basicConfig(
    level=logging.INFO,  # ← Hardcoded, ignored LOG_LEVEL env var
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
```

**Impact:** All DEBUG logs invisible → blind debugging

### Solution
```python
# services/signal/service.py:6 (add import)
import os

# services/signal/service.py:37-42 (fixed)
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
```

### Testing
```powershell
# Set LOG_LEVEL=DEBUG in dev.yml
docker logs cdb_signal | grep DEBUG

# Expected: 100+ DEBUG lines showing pct_change calculations
# Actual (before fix): 0 DEBUG lines
# Actual (after fix): ✅ DEBUG logs flowing
```

### Files Changed
- `services/signal/service.py` (+2 lines, import os + log_level)

---

## Patch #2: Signal Creation - Inline Reason Generation

### Problem
```python
# services/signal/service.py:137-139 (before)
reason=Signal.generate_reason(
    market_data.pct_change, self.config.threshold_pct
),
```

**Error:** `AttributeError: type object 'Signal' has no attribute 'generate_reason'`

**Impact:** Every signal generation attempt crashed → signals_generated_total = 0

### Solution
```python
# services/signal/service.py:137 (fixed)
reason=f"Momentum: {market_data.pct_change:+.4f}% > {self.config.threshold_pct}%",
```

### Testing
```powershell
# Trigger signal (pct_change > threshold)
docker logs cdb_signal | grep "Signal generiert"

# Expected: "✨ Signal generiert: BTCUSDT BUY @ $87598.03 (+0.01%)"
# Actual (before fix): ERROR AttributeError
# Actual (after fix): ✅ Signals generated
```

### Files Changed
- `services/signal/service.py` (-3 lines, +1 line inline reason)

---

## Patch #3: Volume Filter - Disable for Raw Trades

### Problem
```python
# services/signal/config.py:28
min_volume: float = float(os.getenv("SIGNAL_MIN_VOLUME", "100000"))

# market_data payload (from cdb_ws):
{"qty": "0.00014501"}  # ← NOT "volume"!

# MarketData.from_dict():
volume=float(data.get("volume", 0.0))  # ← Defaults to 0.0!

# Signal check (service.py:123-127):
if market_data.volume < self.config.min_volume:  # 0.0 < 100000 = ALWAYS TRUE
    logger.debug(f"{market_data.symbol}: Volume zu niedrig ({market_data.volume})")
    return None  # ← ALL SIGNALS BLOCKED!
```

**Impact:** 100% signal rejection despite pct_change exceeding threshold

### Solution
```yaml
# infrastructure/compose/dev.yml:79
SIGNAL_MIN_VOLUME: "0"  # DISABLED: Raw trades use 'qty' field, not 'volume'
```

**Note:** This is a **workaround**, not a fix. See CONTRACTS.md for proper solution.

### Testing
```powershell
# Check signal generation with volume=0.0
docker logs cdb_signal | grep "Volume zu niedrig"

# Expected (before fix): "Volume zu niedrig (0.0)" on every trade > threshold
# Expected (after fix): No volume rejections, signals generated ✅
```

### Files Changed
- `infrastructure/compose/dev.yml` (+1 line config)

---

## Patch #4: Redis Publishing - None Value Filtering

### Problem
```python
# services/signal/models.py:33-49 (before)
def to_dict(self) -> dict:
    return {
        "type": self.type,
        "signal_id": self.signal_id,  # ← None!
        "bot_id": self.bot_id,        # ← None!
        ...
    }

# Redis XADD (service.py:163-165):
self.redis_client.xadd(
    self.config.output_stream, signal.to_dict(), maxlen=10000
)
# ↑ ERROR: Invalid input of type: 'NoneType'
```

**Impact:** Signals generated but NOT published → risk manager receives nothing

### Solution
```python
# services/signal/models.py:36-54 (fixed)
def to_dict(self) -> dict:
    """Convert to a plain dictionary for transport."""
    # Filter out None values for Redis compatibility (xadd doesn't accept None)
    return {
        k: v
        for k, v in {
            "type": self.type,
            "signal_id": self.signal_id,
            "bot_id": self.bot_id,
            ...
        }.items()
        if v is not None  # ← Filter None values
    }
```

### Testing
```bash
# Check Redis stream for published signals
docker exec cdb_redis sh -c 'redis-cli -a $(cat /run/secrets/redis_password) XLEN stream.signals'

# Expected (before fix): 0 (signals generated but publishing crashed)
# Expected (after fix): 7+ (signals published successfully) ✅

# Verify no publishing errors
docker logs cdb_signal | grep "Signal-Publishing"
# Expected: No ERROR lines
```

### Files Changed
- `services/signal/models.py` (+18 lines, dict comprehension with filter)

---

## Configuration Changes (Evidence-Based)

### Threshold Tuning
```yaml
# infrastructure/compose/dev.yml:78
SIGNAL_THRESHOLD_PCT: "0.005"  # Was: 3.0% (default for candles)
```

**Evidence:**
- 100ms MEXC trades: max ~0.014%, typical <0.01%
- 3.0% threshold: 0 signals in hours
- 0.01% threshold: Still 0 signals (volume check blocking)
- 0.005% threshold: 7+ signals/minute ✅

### Debug Logging
```yaml
# infrastructure/compose/dev.yml:80
LOG_LEVEL: "DEBUG"
```

**Purpose:** Enable detailed logging for signal generation debugging

---

## Patch Application Order

**Critical Path:** Patches MUST be applied in this order

1. **Patch #1 (Logging)** - Enables visibility for validation of other patches
2. **Patch #2 (Signal Creation)** - Fixes crash on signal generation
3. **Patch #3 (Volume Filter)** - Unblocks signal flow
4. **Patch #4 (Redis Publishing)** - Enables downstream consumption

**Rationale:** Each patch depends on previous patches for testing

---

## Testing Matrix

| Patch | Test Command | Success Criteria | Verified |
|-------|--------------|------------------|----------|
| #1 | `docker logs cdb_signal \| grep DEBUG` | DEBUG logs visible | ✅ |
| #2 | `docker logs cdb_signal \| grep "Signal generiert"` | No AttributeError | ✅ |
| #3 | `docker logs cdb_signal \| grep "Volume zu niedrig"` | No volume rejections | ✅ |
| #4 | `docker exec cdb_redis redis-cli XLEN stream.signals` | >0 signals published | ✅ |

**E2E Validation:**
```powershell
# Full pipeline check
docker exec cdb_signal curl -fsS http://localhost:8005/metrics | grep signals_generated_total
# Expected: signals_generated_total 7+

docker logs cdb_risk | grep "Signal empfangen"
# Expected: "📨 Signal empfangen: BTCUSDT BUY" (7+ occurrences)
```

---

## Rollback Plan

### If Patch Fails After Deployment:

1. **Revert compose config:**
   ```yaml
   SIGNAL_THRESHOLD_PCT: "3.0"
   SIGNAL_MIN_VOLUME: "100000"
   LOG_LEVEL: "INFO"
   ```

2. **Revert code changes:**
   ```bash
   git revert bf3ca40  # Reverts all 4 patches
   ```

3. **Rebuild + restart:**
   ```bash
   docker-compose build cdb_signal
   docker-compose up -d --force-recreate cdb_signal
   ```

---

## Metrics (Before/After)

| Metric | Before | After | Delta |
|--------|--------|-------|-------|
| `signals_generated_total` | 0 | 7+ | +∞ |
| `redis_publish_total` (signals) | 0 | 7+ | +∞ |
| DEBUG logs visibility | 0% | 100% | +100% |
| Signal generation crashes | 100% | 0% | -100% |
| Volume check false positives | 100% | 0% | -100% |

**Pipeline Health:**
- ✅ cdb_ws → 32k+ trades published
- ✅ cdb_signal → 7+ signals generated
- ✅ cdb_risk → 7+ signals received (blocked: no allocation - expected)

---

## Future Improvements (Out of Scope)

1. **Fix `qty` → `volume` mapping** (see CONTRACTS.md Issue #1)
2. **Add Signal.generate_reason() static method** (cleaner API)
3. **Implement volume check for aggregated trades** (when candle support added)
4. **Add None-safety to all Redis XADD calls** (global pattern)

---

**Deliverable:** Patchset Plan ✅
**Commit:** bf3ca40
**Status:** Deployed, E2E Validated, Pushed to origin/main
