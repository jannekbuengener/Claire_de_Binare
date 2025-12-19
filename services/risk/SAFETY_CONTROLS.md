# Risk Management - Safety Controls (Issue #177)

**Version**: 2.0
**Status**: Production Ready
**Created**: 2025-12-19

## Overview

Enhanced multi-layer risk management system with comprehensive safety controls designed to prevent catastrophic trading losses and provide emergency intervention capabilities.

## Safety Architecture

### Risk Layers (in Priority Order)

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 0: EMERGENCY STOP (Redis Kill Switch)                │
│ Priority: CRITICAL | Overrides: ALL                        │
│ Purpose: Manual emergency trading halt                      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Layer 1: CIRCUIT BREAKER (Daily Drawdown + Cooldown)       │
│ Priority: CRITICAL | Overrides: Layers 1.5-3                │
│ Purpose: Auto-halt on excessive losses                      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Layer 1.5: MAX OPEN POSITIONS (Position Count Limit)       │
│ Priority: HIGH | Overrides: Layers 1.6-3                    │
│ Purpose: Prevent portfolio over-diversification             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Layer 1.6: PER-SYMBOL LIMITS (Symbol Position Limits)      │
│ Priority: HIGH | Overrides: Layers 2-3                      │
│ Purpose: Prevent concentration risk                         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Layer 2: TOTAL EXPOSURE (Portfolio Exposure Limit)         │
│ Priority: MEDIUM | Overrides: Layer 3                       │
│ Purpose: Limit total market exposure                        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Layer 3: POSITION SIZE (Individual Trade Size)             │
│ Priority: MEDIUM | Overrides: None                          │
│ Purpose: Prevent oversized individual trades                │
└─────────────────────────────────────────────────────────────┘
                            ↓
                    ✅ ORDER APPROVED
```

## Layer 0: Emergency Stop

**Purpose**: Manual override to halt ALL trading immediately.

### Configuration

```bash
# Enable/disable emergency stop check (default: enabled)
ENABLE_EMERGENCY_STOP=true

# Redis key to monitor
# Set to "1", "true", or "yes" to activate emergency stop
redis-cli SET "trading:emergency_stop" "1"
```

### How It Works

- **Highest Priority**: Checked before all other risk layers
- **Redis-Based**: Controlled via single Redis key
- **Fail-Safe**: If Redis check fails → block trading
- **Instant Activation**: Takes effect on next signal
- **Global Impact**: Blocks ALL symbols, ALL strategies

### Emergency Stop Activation

```bash
# ACTIVATE emergency stop (halt all trading)
redis-cli SET "trading:emergency_stop" "1"

# DEACTIVATE emergency stop (resume trading)
redis-cli DEL "trading:emergency_stop"

# CHECK status
redis-cli GET "trading:emergency_stop"
```

### Use Cases

- Market crash / flash crash detected
- Exchange API issues
- Bot behavior anomaly detected
- Manual intervention required
- System maintenance

## Layer 1: Circuit Breaker (Enhanced)

**Purpose**: Automatically halt trading when daily losses exceed threshold.

### Configuration

```bash
# Maximum daily drawdown before circuit breaker triggers (default: 5%)
MAX_DAILY_DRAWDOWN_PCT=0.05

# Cooldown period in minutes after trigger (default: 60)
CIRCUIT_BREAKER_COOLDOWN=60

# Auto-reset after cooldown? (default: false)
CIRCUIT_BREAKER_AUTO_RESET=false
```

### How It Works

1. **Trigger**: Daily P&L <= -(Balance × MAX_DAILY_DRAWDOWN_PCT)
   - Example: $10,000 balance, 5% limit = triggers at -$500 daily loss

2. **Cooldown**: Enforces waiting period after trigger
   - Default: 60 minutes
   - Prevents immediate re-trading after losses

3. **Reset Options**:
   - **Auto-Reset** (if enabled): Resets after cooldown automatically
   - **Manual Reset** (default): Requires manual intervention via API

### Manual Circuit Breaker Reset

```bash
# Reset circuit breaker via API
curl -X POST http://risk-manager:8002/reset-circuit-breaker
```

### Monitoring

```bash
# Check circuit breaker status
curl http://risk-manager:8002/status | jq '.safety_status'

# Response:
{
  "circuit_breaker_active": false,
  "circuit_breaker_triggered_at": null,  # null if not active
  "emergency_stop_active": false
}
```

## Layer 1.5: Max Open Positions

**Purpose**: Limit number of simultaneous open positions.

### Configuration

```bash
# Maximum number of open positions (default: 5)
MAX_OPEN_POSITIONS=5
```

### How It Works

- Counts all open positions across ALL symbols
- Blocks new orders when limit reached
- Allows closing positions even when at limit

### Example

```bash
# With MAX_OPEN_POSITIONS=5:
# Currently open: BTC, ETH, SOL, ADA, DOGE (5 positions)
# New signal: MATIC → BLOCKED (would be 6th position)

# After closing SOL:
# Currently open: BTC, ETH, ADA, DOGE (4 positions)
# New signal: MATIC → APPROVED
```

## Layer 1.6: Per-Symbol Position Limits

**Purpose**: Prevent duplicate positions and enforce symbol-specific size limits.

### Configuration

```bash
# Max positions per symbol (default: 1)
MAX_POSITIONS_PER_SYMBOL=1

# Per-symbol absolute limits (optional, JSON format)
PER_SYMBOL_LIMITS='{"BTCUSDT": 0.5, "ETHUSDT": 10.0, "SOLUSDT": 100.0}'
```

### How It Works

**Position Count Limit**:
- Default: 1 position per symbol (prevents duplicate entries)
- Example: If already have BTCUSDT position → block new BTCUSDT signal

**Absolute Size Limit** (if configured):
- Symbol-specific maximum position size
- Example: Max 0.5 BTC, Max 10 ETH
- Useful for limiting exposure to volatile assets

### Example

```python
# Configuration:
MAX_POSITIONS_PER_SYMBOL=1
PER_SYMBOL_LIMITS={"BTCUSDT": 0.5}

# Scenario 1: Position Count
# Current: BTCUSDT position (0.3 BTC)
# Signal: BUY BTCUSDT → BLOCKED (already have position)

# Scenario 2: Absolute Limit
# Current: BTCUSDT position (0.5 BTC) - at limit
# Signal: BUY BTCUSDT → BLOCKED (position = 0.5, limit = 0.5)
```

## Layer 2: Total Exposure Limit

**Purpose**: Limit total notional value of all open positions.

### Configuration

```bash
# Maximum total exposure (default: 30% of balance)
MAX_TOTAL_EXPOSURE_PCT=0.30
```

### How It Works

- Calculates: Total Exposure = Σ(position_size × current_price) for all positions
- Blocks new orders when total exposure exceeds: Balance × MAX_TOTAL_EXPOSURE_PCT
- Example: $10,000 balance, 30% limit → max $3,000 total exposure

## Layer 3: Position Size Limit

**Purpose**: Limit size of individual trades.

### Configuration

```bash
# Maximum position size per trade (default: 10% of balance)
MAX_POSITION_PCT=0.10
```

### How It Works

- Maximum position size: Balance × MAX_POSITION_PCT
- Example: $10,000 balance, 10% limit → max $1,000 per trade
- Actual position size scaled by signal confidence

## Configuration Examples

### Conservative Profile (Recommended for Production Start)

```bash
# Risk Limits
MAX_POSITION_PCT=0.05              # 5% per position
MAX_TOTAL_EXPOSURE_PCT=0.15        # 15% total exposure
MAX_DAILY_DRAWDOWN_PCT=0.03        # 3% max daily loss

# Safety Controls
ENABLE_EMERGENCY_STOP=true
MAX_OPEN_POSITIONS=3               # Max 3 positions
MAX_POSITIONS_PER_SYMBOL=1         # No duplicates
CIRCUIT_BREAKER_COOLDOWN=120       # 2 hour cooldown
CIRCUIT_BREAKER_AUTO_RESET=false   # Manual reset required

# Per-Symbol Limits (Bitcoin only, limit 0.1 BTC)
PER_SYMBOL_LIMITS='{"BTCUSDT": 0.1}'
```

### Moderate Profile (After 72-hour validation)

```bash
# Risk Limits
MAX_POSITION_PCT=0.10              # 10% per position
MAX_TOTAL_EXPOSURE_PCT=0.30        # 30% total exposure
MAX_DAILY_DRAWDOWN_PCT=0.05        # 5% max daily loss

# Safety Controls
ENABLE_EMERGENCY_STOP=true
MAX_OPEN_POSITIONS=5               # Max 5 positions
MAX_POSITIONS_PER_SYMBOL=1
CIRCUIT_BREAKER_COOLDOWN=60        # 1 hour cooldown
CIRCUIT_BREAKER_AUTO_RESET=false

# Per-Symbol Limits
PER_SYMBOL_LIMITS='{"BTCUSDT": 0.5, "ETHUSDT": 10.0}'
```

### Aggressive Profile (Experienced, validated systems only)

```bash
# Risk Limits
MAX_POSITION_PCT=0.15              # 15% per position
MAX_TOTAL_EXPOSURE_PCT=0.50        # 50% total exposure
MAX_DAILY_DRAWDOWN_PCT=0.10        # 10% max daily loss

# Safety Controls
ENABLE_EMERGENCY_STOP=true
MAX_OPEN_POSITIONS=10
MAX_POSITIONS_PER_SYMBOL=2         # Allow 2 positions per symbol
CIRCUIT_BREAKER_COOLDOWN=30        # 30 min cooldown
CIRCUIT_BREAKER_AUTO_RESET=true    # Auto-reset enabled

# No per-symbol limits (rely on percentage limits)
PER_SYMBOL_LIMITS='{}'
```

## Monitoring & Observability

### Health Check Endpoint

```bash
# Basic health check
curl http://risk-manager:8002/health

# Response:
{
  "status": "ok",
  "service": "risk_manager",
  "version": "2.0.0"
}
```

### Detailed Status Endpoint

```bash
# Full status including safety state
curl http://risk-manager:8002/status | jq

# Response includes:
{
  "risk_state": {
    "total_exposure": 1500.50,
    "daily_pnl": -120.30,
    "open_positions": 3,
    "signals_approved": 45,
    "signals_blocked": 12,
    "positions": {"BTCUSDT": 0.3, "ETHUSDT": 5.0, "SOLUSDT": 50.0},
    "pending_orders": 0
  },
  "safety_status": {
    "emergency_stop_active": false,
    "circuit_breaker_active": false,
    "circuit_breaker_triggered_at": null,
    "max_open_positions": 5,
    "current_open_positions": 3
  },
  "risk_limits": {
    "max_position_pct": 0.10,
    "max_total_exposure_pct": 0.30,
    "max_daily_drawdown_pct": 0.05,
    "max_open_positions": 5,
    "max_positions_per_symbol": 1,
    "per_symbol_limits": {"BTCUSDT": 0.5}
  }
}
```

### Prometheus Metrics

```bash
# Metrics endpoint
curl http://risk-manager:8002/metrics

# Key metrics:
orders_approved_total        # Orders passed risk checks
orders_blocked_total         # Orders blocked by risk checks
circuit_breaker_active       # 1 if active, 0 if not
risk_total_exposure_value    # Total position value
risk_pending_orders_total    # Pending order confirmations
```

### Grafana Dashboard Queries

```promql
# Circuit breaker triggers (count)
increase(circuit_breaker_active[24h])

# Order block rate
rate(orders_blocked_total[5m]) / rate(orders_approved_total[5m])

# Current exposure as % of balance
(risk_total_exposure_value / 10000) * 100
```

## Testing

### Run Safety Tests

```bash
# Navigate to risk service directory
cd services/risk

# Run comprehensive safety tests
python -m pytest tests/test_safety_controls.py -v

# Run specific test class
python -m pytest tests/test_safety_controls.py::TestEmergencyStop -v

# Run with coverage
python -m pytest tests/test_safety_controls.py --cov=service --cov-report=html
```

### Manual Safety Testing

```bash
# Test 1: Emergency Stop
redis-cli SET "trading:emergency_stop" "1"
# Send test signal → should be BLOCKED
redis-cli DEL "trading:emergency_stop"

# Test 2: Circuit Breaker
# Manually set daily_pnl to trigger (-600 for $10k balance, 5% limit)
# Via risk manager API or database update
# Send test signal → should be BLOCKED

# Test 3: Max Positions
# Open 5 positions, try to open 6th → should be BLOCKED

# Test 4: Per-Symbol Limit
# Open BTCUSDT position, try to open another BTCUSDT → should be BLOCKED
```

## Troubleshooting

### Circuit Breaker Won't Reset

**Symptom**: Circuit breaker still active after cooldown period

**Solution**:
```bash
# Check cooldown configuration
curl http://risk-manager:8002/status | jq '.risk_limits.circuit_breaker_cooldown_minutes'

# If auto-reset disabled, manual reset required:
curl -X POST http://risk-manager:8002/reset-circuit-breaker

# Or via Redis:
redis-cli DEL "risk:circuit_breaker_active"
```

### Emergency Stop Not Working

**Symptom**: Trading continues despite emergency stop set

**Checks**:
1. Verify ENABLE_EMERGENCY_STOP=true in .env
2. Check Redis key format:
   ```bash
   redis-cli GET "trading:emergency_stop"
   # Should return: "1", "true", or "yes"
   ```
3. Check Risk Manager logs for Redis connection errors
4. Restart Risk Manager if needed

### Position Count Mismatch

**Symptom**: Risk Manager shows different position count than expected

**Solution**:
```bash
# Check current positions
curl http://risk-manager:8002/status | jq '.risk_state.positions'

# Positions with qty < 1e-6 are considered closed
# Verify positions match Execution Service state
```

## Performance Considerations

- **Emergency Stop Check**: ~1-2ms (Redis GET)
- **Circuit Breaker**: ~0.5ms (in-memory check)
- **Position Limits**: ~0.3ms (in-memory dict lookup)
- **Total Overhead**: ~2-3ms per signal

**Recommendation**: All safety checks complete in < 5ms → negligible impact on signal processing latency.

## Future Enhancements (Planned)

- [ ] Position-level stop-loss tracking
- [ ] Dynamic risk limit adjustment based on volatility
- [ ] Risk score per signal (composite risk metric)
- [ ] Multi-timeframe drawdown tracking (hourly, daily, weekly)
- [ ] Automated risk report generation
- [ ] Risk event notifications (Telegram/Discord)

## References

- **Issue**: #177 - Trading Safety & Position Limits
- **Roadmap**: AUTONOMOUS_ROADMAP.md - Phase 2
- **Tests**: services/risk/tests/test_safety_controls.py
- **Config**: services/risk/config.py
- **Service**: services/risk/service.py
