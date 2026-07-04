# Trading Modes

**Claire de Binare** supports three distinct trading modes with progressive safety levels.

## Overview

| Mode | Real Money | Exchange Connection | Safety | Use Case |
|------|------------|---------------------|--------|----------|
| **PAPER** | ❌ No | ❌ No | 🟢 Highest | Development, testing strategies |
| **STAGED** | ❌ No* | ⚠️ Nominal `MEXC_TESTNET` only — **no spot testnet** | 🟡 Medium | Pre-production validation (exchange-capable on mainnet spot host when `DRY_RUN=false`) |
| **LIVE** | ✅ YES | ✅ Production | 🔴 DANGER | Real trading |

\* STAGED sets `MOCK_TRADING=false`, `DRY_RUN=false` in legacy mapping — **exchange-capable**
on mainnet spot REST (`https://api.mexc.com`); not a sandbox. No-send remains
`DRY_RUN=true` + `MOCK_TRADING=true`. See LR-050 venue semantics (PR #3720).

---

## Configuration

### Environment Variables

**Primary Configuration:**
```bash
# Trading mode (default: paper)
TRADING_MODE=paper|staged|live

# LIVE mode safety confirmation (required for live mode)
LIVE_TRADING_CONFIRMED=yes
```

**Legacy Compatibility:**
The system automatically sets these based on `TRADING_MODE`:
- `MOCK_TRADING` - Use mock executor vs real exchange executor
- `DRY_RUN` - Log trades vs execute trades
- `MEXC_TESTNET` - **Nominal flag only** (no MEXC spot testnet; not a no-send proof;
  `MexcClient(testnet=True)` fail-closed per PR #3720)

---

## Modes in Detail

### PAPER Mode (Default)

**Characteristics:**
- ✅ Simulated trading only
- ❌ No exchange connection
- ❌ No real money
- 🟢 Safest mode

**Use Cases:**
- Strategy development
- Algorithm testing
- Backtest validation
- Learning the system

**Configuration Example:**
```bash
# .env
TRADING_MODE=paper

# Or omit entirely (paper is default)
```

**What Happens:**
- Orders logged but not sent to exchange
- Fills simulated with mock data
- Portfolio tracked in memory only
- No API keys required

---

### STAGED Mode (Pre-production — not a spot testnet)

**Characteristics:**
- ⚠️ **Exchange-capable** when `DRY_RUN=false` and `MOCK_TRADING=false` (mainnet spot REST)
- ❌ **No MEXC Spot testnet/sandbox** — `MEXC_TESTNET=true` is nominal only (PR #3720)
- ❌ No real money **by intent** — but not fail-closed without `DRY_RUN`/`MOCK_TRADING`
- 🟡 Medium safety — requires explicit no-send gates for safe testing

**Use Cases:**
- Pre-production validation with real network latency (mainnet spot host)
- Order execution path verification **with** `DRY_RUN=true` / mock executor for safety
- API integration testing under controlled gates

**Configuration Example:**
```bash
# .env
TRADING_MODE=staged

# API credentials required when exchange-capable (mainnet spot — not a sandbox)
MEXC_API_KEY=/run/secrets/mexc_api_key
MEXC_API_SECRET=/run/secrets/mexc_api_secret
```

**What Happens:**
- Legacy mapping sets `MEXC_TESTNET=true`, `MOCK_TRADING=false`, `DRY_RUN=false`
- Orders **may** be sent to mainnet spot REST (`https://api.mexc.com`) — **not** a testnet
- `MexcClient(testnet=True)` **fail-closed** (`ValueError`); no spot sandbox exists
- For safe testing prefer **PAPER** mode or explicit `DRY_RUN=true` + `MOCK_TRADING=true`

---

### LIVE Mode (Production)

**Characteristics:**
- ✅ Real exchange connection
- ✅ **REAL MONEY AT RISK**
- 🔴 **MAXIMUM DANGER**

**Requirements:**
1. `TRADING_MODE=live`
2. `LIVE_TRADING_CONFIRMED=yes` (safety confirmation)
3. Production API credentials
4. Full system validation

**Configuration Example:**
```bash
# .env
TRADING_MODE=live
LIVE_TRADING_CONFIRMED=yes  # REQUIRED for live mode

# Production API credentials required
MEXC_API_KEY=/run/secrets/mexc_live_api_key
MEXC_API_SECRET=/run/secrets/mexc_live_api_secret
```

**Safety Checks:**
- ⚠️ Requires explicit `LIVE_TRADING_CONFIRMED=yes`
- ⚠️ Service exits if confirmation missing
- ⚠️ Logs prominent warnings on startup
- ⚠️ Requires production API credentials

**What Happens:**
- Orders sent to MEXC production
- **REAL MONEY TRADED**
- **REAL PROFITS AND LOSSES**
- Full operational risk

---

## Safety Features

### Default to PAPER

If no `TRADING_MODE` is set, the system defaults to PAPER mode:
```python
from core.config import get_trading_mode

mode = get_trading_mode()  # Returns TradingMode.PAPER if env var not set
```

### LIVE Mode Confirmation

LIVE mode **cannot start** without explicit confirmation:
```bash
# This will EXIT with error
TRADING_MODE=live

# This will start (DANGER)
TRADING_MODE=live
LIVE_TRADING_CONFIRMED=yes
```

**Error Message:**
```
🚨 LIVE TRADING MODE BLOCKED 🚨
LIVE mode requires LIVE_TRADING_CONFIRMED=yes environment variable
This is a safety measure to prevent accidental real-money trading
Current LIVE_TRADING_CONFIRMED value: '(not set)'
```

### Mode Validation

The system validates mode configuration on startup:
```python
from core.config import TradingMode, validate_trading_mode

mode = TradingMode.STAGED
validate_trading_mode(mode, api_key="...", api_secret="...")
# Raises ValueError if credentials missing for STAGED/LIVE
```

---

## Usage in Services

### Execution Service

```python
from core.config import get_trading_mode, TradingMode

# Get mode on startup
mode = get_trading_mode()  # Validates LIVE confirmation if needed

if mode == TradingMode.PAPER:
    executor = MockExecutor()
elif mode == TradingMode.STAGED:
    # Exchange-capable on mainnet spot; MEXC_TESTNET nominal — not a sandbox.
    # MexcClient(testnet=True) fail-closed (PR #3720).
    executor = MexcExecutor(testnet=False)
else:  # LIVE
    executor = MexcExecutor(testnet=False)
```

### Risk Service

```python
from core.config import get_trading_mode

mode = get_trading_mode()

if mode.is_safe:
    # Paper or Staged - safe to test aggressive strategies
    max_position_pct = 0.20
else:
    # Live - use conservative limits
    max_position_pct = 0.10
```

---

## Migration from Legacy Config

### Before (Legacy)

```bash
# Old .env
MOCK_TRADING=true
DRY_RUN=true
MEXC_TESTNET=true
```

### After (New)

```bash
# New .env (replaces all three variables)
TRADING_MODE=paper
```

### Automatic Conversion

The system provides `get_legacy_config()` for backward compatibility:
```python
from core.config import get_trading_mode, get_legacy_config

mode = get_trading_mode()
legacy = get_legacy_config(mode)

# legacy = {
#     "MOCK_TRADING": True,
#     "DRY_RUN": True,
#     "MEXC_TESTNET": True
# }
```

---

## Testing

### Run Unit Tests

```powershell
python -m pytest tests/unit/config/test_trading_mode.py -vv
```

### Test Scenarios

**1. Default Mode (PAPER)**
```powershell
# No env vars set
$env:TRADING_MODE = $null
python -m pytest tests/unit/config/test_trading_mode.py::TestGetTradingMode::test_default_is_paper -v
```

**2. STAGED Mode**
```powershell
$env:TRADING_MODE = "staged"
python -m pytest tests/unit/config/test_trading_mode.py::TestGetTradingMode::test_staged_mode_from_env -v
```

**3. LIVE Mode Safety**
```powershell
$env:TRADING_MODE = "live"
$env:LIVE_TRADING_CONFIRMED = $null
# Should exit with code 1
python -m pytest tests/unit/config/test_trading_mode.py::TestGetTradingMode::test_live_mode_without_confirmation_exits -v
```

---

## Checklist for Go-Live

Before enabling LIVE mode:

- [ ] All E2E tests passing in PAPER mode
- [ ] All E2E tests passing in STAGED mapping (with explicit no-send gates where required)
- [ ] 14-day paper trading completed successfully
- [ ] Risk limits validated under controlled pre-production runs
- [ ] Circuit breakers tested under controlled pre-production runs
- [ ] Emergency stop mechanism tested
- [ ] Production API credentials secured (Docker secrets)
- [ ] `LIVE_TRADING_CONFIRMED=yes` set explicitly
- [ ] Monitoring and alerting configured
- [ ] Team approval obtained

---

## Troubleshooting

### "Invalid trading mode" Error

**Cause:** Typo in `TRADING_MODE` value

**Fix:**
```bash
# Invalid
TRADING_MODE=production  # ❌ Not valid

# Valid
TRADING_MODE=live  # ✅ Correct
```

### LIVE Mode Blocked

**Cause:** Missing `LIVE_TRADING_CONFIRMED=yes`

**Fix:**
```bash
# Add to .env
LIVE_TRADING_CONFIRMED=yes
```

### API Credentials Error in STAGED/LIVE

**Cause:** Missing API keys for exchange connection

**Fix:**
```bash
# Ensure secrets are mounted
MEXC_API_KEY=/run/secrets/mexc_api_key
MEXC_API_SECRET=/run/secrets/mexc_api_secret

# Verify files exist
ls /run/secrets/
```

---

## References

- **Code:** `core/config/trading_mode.py`
- **Tests:** `tests/unit/config/test_trading_mode.py`
- **Related Issues:** #252 (Trading Mode Feature Flags)
- **Security:** `docs/SECURITY_HARDENING.md`
- **Testnet:** `knowledge/operations/TESTNET_SETUP.md`

---

**Last Updated:** 2026-07-04 (MEXC venue semantics reconcile, PR #3720 / #3726)
**Status:** ✅ Implemented (Issue #252)
