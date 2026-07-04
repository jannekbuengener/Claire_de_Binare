# MEXC Testnet Setup Guide

**Safe testing environment for Claire de Binare trading bot**

> **LEGACY NOTICE:** The `.env`-based configuration instructions in this guide reflect the
> pre-canonical setup model. The current runtime uses Docker secrets
> (`~/Documents/.secrets/.cdb/`) and the Blue/Red compose canon. For secret setup use
> `.\tools\cdb.ps1 secrets init`; for stack start use `.\tools\cdb.ps1 runtime up`.
> The sections below are retained for historical reference only — they do **not**
> describe the current operational path.
>
> **Venue semantics (post PR #3720, Refs #3718/#3719):** MEXC offers **no** Spot API
> testnet/sandbox. Spot REST default is `https://api.mexc.com`. `MexcClient(testnet=True)`
> **fail-closed** (`ValueError`). `MEXC_TESTNET` is a **nominal** legacy flag only — not a
> no-send proof and not a sandbox venue. Safe non-trading is `DRY_RUN=true` +
> `MOCK_TRADING=true`. Spot WS uses `wss://wbs-api.mexc.com/ws` (independent of
> `MEXC_TESTNET`). The former `https://contract.mexc.com` host was a deprecated MEXC
> **Futures** domain, not a spot testnet. See
> `docs/live-readiness/LR-050-VENUE-ENDPOINT-SEMANTICS-2026-07-03.md` and
> `knowledge/ARCHITECTURE_MAP.md` §6. **LR remains NO-GO.**

## Overview

> **Historical:** This guide was written when a MEXC Spot "testnet" was assumed. Official
> MEXC documentation and repo verification (LR-050, PR #3720) confirm **no Spot API
> testnet/sandbox** exists. CDB safe testing uses **Paper mode** (`DRY_RUN=true`,
> `MOCK_TRADING=true`) — not a separate spot testnet URL.

The MEXC Testnet **web UI** (`testnet.mexc.com`) provided a risk-free environment to test
trading operations with **fake money** before going live. That UI context is **not** wired
into the current CDB spot REST/WS path.

### Key Benefits

✅ **No Risk** - Uses simulated funds, no real money involved
✅ **Real API** - Same API as production for accurate testing
✅ **Full Features** - Test all order types and operations
✅ **Free Balance** - Get testnet USDT for testing

---

## Quick Start

### 1. Get Testnet Credentials

1. Go to: https://testnet.mexc.com/
2. Create account or login
3. Navigate to **API Management**
4. Create new API Key
5. Copy **API Key** and **API Secret**
6. **Enable Spot Trading** permissions

### 2. Configure Environment

Edit `.env` file:

```bash
# MEXC API Configuration (Testnet)
MEXC_API_KEY=your_testnet_api_key_here
MEXC_API_SECRET=your_testnet_api_secret_here
MEXC_TESTNET=true                     # true = testnet (safe)
MOCK_TRADING=false                    # false = use MEXC API
DRY_RUN=true                          # true = log only (safest)
```

### 3. Initialize Secrets (canonical)

```powershell
.\tools\cdb.ps1 secrets init
```

Expected output:
```
🧪 MEXC Testnet Setup
==================================================

📋 Current Configuration:
--------------------------------------------------
  MEXC_TESTNET:    true
  MOCK_TRADING:    false
  DRY_RUN:         true
  MEXC_API_KEY:    [SET]
  MEXC_API_SECRET: [SET]

✅ MEXC API credentials configured

🔌 Testing MEXC Testnet Connection...
--------------------------------------------------
✅ Connection successful!
   Testnet USDT Balance: 10000.00
   BTC/USDT Price: 42350.50

✅ Testnet connection validated!
```

---

## Trading Modes

### 🟢 Dry Run Mode (Safest)

**Configuration:**
```bash
MEXC_TESTNET=true
DRY_RUN=true
```

**Behavior:**
- Orders are **logged** but NOT sent to MEXC
- Validates order parameters
- Tests business logic without API calls
- **Recommended for initial testing**

**Use When:**
- Testing new features
- Debugging order logic
- Validating risk management

---

### 🟡 Testnet Mode (Historical — not current CDB spot path)

> **Historical / misleading:** There is **no** MEXC Spot API testnet. Setting
> `MEXC_TESTNET=true` with `DRY_RUN=false` is **exchange-capable** on the mainnet spot
> host (`https://api.mexc.com`) and is **not** a sandbox. `MexcClient(testnet=True)` now
> **fail-closed** (PR #3720). For safe integration testing use **Dry Run Mode** or
> **Paper mode** (`TRADING_MODE=paper`).

**Configuration (legacy model — do not use as operational guidance):**
```bash
MEXC_TESTNET=true
DRY_RUN=false
```

**Behavior (pre-#3720 assumption — stale):**
- Was documented as orders sent to a "MEXC Testnet" spot host
- **Current code:** no spot testnet; `testnet=True` raises `ValueError`

---

### 🔴 Live Mode (Real Money - Use with Caution!)

**Configuration:**
```bash
MEXC_TESTNET=false
DRY_RUN=false
```

**Behavior:**
- Orders sent to **MEXC Production**
- Uses **REAL MONEY** ⚠️
- Actual trades executed

**⚠️ Requirements:**
- Complete testnet validation
- Security audit passed
- Risk management verified
- Production credentials configured
- **Start with small amounts!**

---

## Testing Workflow

### Phase 1: Dry Run Testing

```bash
# 1. Configure dry run mode (legacy .env model — see LEGACY NOTICE above)
MEXC_TESTNET=true
DRY_RUN=true

# 2. Start services (canonical)
.\tools\cdb.ps1 runtime up

# 3. Monitor logs (no real orders)
docker logs -f cdb_execution

# 4. Verify order validation works
# Expected: Orders logged, parameters validated
```

### Phase 2: Testnet Testing (Historical)

> **Historical:** Phase 2 assumed a spot testnet connection. Post PR #3720,
> `test_mexc_testnet.py` validates **fail-closed** `testnet=True` behavior and mainnet
> defaults — not a live spot sandbox.

```bash
# 1. (Historical) Switch to testnet mode — NOT a sandbox in current code
DRY_RUN=false

# 2. Run integration tests (fail-closed + mainnet default semantics)
pytest tests/integration/test_mexc_testnet.py -v

# 3. Test manual order flow — testnet=True FAILS CLOSED (ValueError)
python -c "
from core.clients.mexc import MexcClient
# MexcClient(testnet=True)  # raises ValueError — no spot testnet
client = MexcClient(testnet=False)  # mainnet spot base https://api.mexc.com

# Get balance
balance = client.get_balance('USDT')
print(f'Balance: {balance}')

# Place small test order (uncomment when ready)
# order = client.place_market_order('BTCUSDT', 'BUY', 0.0001)
# print(f'Order: {order}')
"

# 4. Monitor execution service
docker logs -f cdb_execution
```

### Phase 3: Production Preparation

```bash
# 1. Complete testnet validation
✅ All integration tests pass
✅ Order execution working correctly
✅ Risk limits enforced
✅ Error handling tested

# 2. Security checklist
✅ API keys in Docker secrets (not .env)
✅ Rate limiting configured
✅ Position limits set
✅ Circuit breakers tested
✅ Emergency stop mechanism tested

# 3. Start small in production
- Set very low position limits
- Monitor every trade manually
- Gradually increase limits
```

---

## Common Issues

### Issue: "API credentials not configured"

**Solution:**
```bash
# Check .env file
grep MEXC .env

# Make sure keys are set (not empty)
MEXC_API_KEY=mxc_abc123...
MEXC_API_SECRET=def456...
```

### Issue: "Connection failed: 401 Unauthorized"

**Causes:**
- Invalid API key/secret
- API key not enabled for Spot Trading
- Wrong API host (historical docs referenced deprecated `contract.mexc.com`)

**Solution:**
1. Regenerate API key on testnet.mexc.com (web UI only — not CDB spot REST path)
2. Enable Spot Trading permission
3. Update `.env` with new credentials

### Issue: "Insufficient balance"

**Solution:**
1. Login to https://testnet.mexc.com/
2. Go to Wallet
3. Request testnet USDT funding
4. Wait for balance to update

### Issue: "Order rejected: MIN_NOTIONAL"

**Cause:** Order value too small

**Solution:**
```python
# Increase order quantity
# Minimum: ~10 USDT equivalent

# Bad: 0.00001 BTC (~0.50 USD)
# Good: 0.0003 BTC (~15 USD)
```

---

## API Endpoints

### Current CDB spot endpoints (post PR #3720)

| Surface | URL | Notes |
|---------|-----|-------|
| Spot REST (default) | `https://api.mexc.com` | Mainnet spot; no spot testnet exists |
| Spot WebSocket | `wss://wbs-api.mexc.com/ws` | Public feed; not switched by `MEXC_TESTNET` |
| `MexcClient(testnet=True)` | — | **Fail-closed** (`ValueError`) |

### Historical / external references (not CDB spot REST path)

- **Deprecated futures host (do not use):** `https://contract.mexc.com` — former MEXC
  **Futures** domain, discontinued 2026-01-19; was mislabeled "testnet" in old docs
- **MEXC web testnet UI (external):** `https://testnet.mexc.com/` — not the CDB spot API
- **Docs:** `https://mexcdevelop.github.io/apidocs/spot_v3_en/`

### Production URLs (official mainnet spot)

- **Spot API:** `https://api.mexc.com`
- **Web UI:** `https://www.mexc.com/`

---

## Integration Tests

### Run All Tests

```bash
# Run testnet integration tests
pytest tests/integration/test_mexc_testnet.py -v

# Run with coverage
pytest tests/integration/test_mexc_testnet.py --cov=services.execution
```

### Test Categories

**1. Connection Tests** (Always safe)
- `test_testnet_client_initialization`
- `test_get_account_balance`
- `test_get_usdt_balance`
- `test_get_ticker_price`

**2. Validation Tests** (Safe - no execution)
- `test_market_order_validation`

**3. Execution Tests** (Requires manual enable)
- `test_place_market_order_testnet` (⚠️ skipped by default)
- `test_get_order_status_testnet` (⚠️ skipped by default)

### Enable Execution Tests

```bash
# Remove @pytest.mark.skip decorator
# Set DRY_RUN=false
# Run specific test
pytest tests/integration/test_mexc_testnet.py::TestMexcTestnetOrders::test_place_market_order_testnet -v -s
```

---

## Monitoring

### Service Logs

```bash
# Execution service
docker logs -f cdb_execution

# Risk manager
docker logs -f cdb_risk

# All services (canonical)
.\tools\cdb.ps1 service logs -ServiceName cdb_execution
```

### Check Order History

```python
from core.clients.mexc import MexcClient

# Historical example used testnet=True — now fail-closed (ValueError).
client = MexcClient(testnet=False)  # https://api.mexc.com

# Get recent orders
orders = client.session.get(
    f"{client.base_url}/api/v3/openOrders",
    params={"symbol": "BTCUSDT"}
)
print(orders.json())
```

---

## Safety Checklist

Before enabling real trading:

### Testnet Validation
- [ ] Testnet connection working
- [ ] Balance queries successful
- [ ] Test orders executed correctly
- [ ] Order status tracking works
- [ ] Error handling tested

### Risk Management
- [ ] Position limits enforced
- [ ] Max exposure limits working
- [ ] Stop-loss triggers tested
- [ ] Circuit breakers functional
- [ ] Emergency stop tested

### Security
- [ ] API keys in Docker secrets
- [ ] No credentials in code/logs
- [ ] Rate limiting configured
- [ ] Audit trail enabled
- [ ] Monitoring alerts set up

### Production Readiness
- [ ] All integration tests pass
- [ ] Load testing completed
- [ ] Failover tested
- [ ] Backup systems ready
- [ ] Team trained on emergency procedures

---

## Support

### Documentation
- [MEXC Testnet Docs](https://mexcdevelop.github.io/apidocs/spot_v3_en/)
- [Claire de Binare Docs](../README.md)

### Issues
- Report bugs: [GitHub Issues](https://github.com/jannekbuengener/Claire_de_Binare/issues)
- Tag with: `testnet`, `mexc`, `integration`

---

**Remember:** Testnet is for learning and testing. Always validate thoroughly before live trading! 🚀
