# Emergency Stop - Standard Operating Procedure (SOP)

**Critical Safety Mechanism for Claire de Binare Trading System**

## Overview

The **Kill-Switch** is a safety mechanism that immediately halts ALL trading activity. It persists across service restarts and cannot be bypassed.

**When activated:** Trading STOPS. No new orders accepted. Open positions remain as-is.
**When deactivated:** Trading RESUMES. Normal operations continue.

---

## Activation Triggers

### Automatic Triggers

| Trigger | Reason Code | Description |
|---------|-------------|-------------|
| **Circuit Breaker** | `CIRCUIT_BREAKER` | Daily loss exceeds configured limit (e.g., -5%) |
| **Risk Limit** | `RISK_LIMIT` | Total exposure exceeds maximum (e.g., >30% of capital) |
| **System Error** | `SYSTEM_ERROR` | Critical system failure detected |
| **Exchange Error** | `EXCHANGE_ERROR` | Cannot connect to exchange / API failures |
| **Auth Failure** | `AUTH_FAILURE` | Authentication or authorization failure |

### Manual Triggers

| Trigger | Reason Code | Description |
|---------|-------------|-------------|
| **Manual Stop** | `MANUAL` | Operator intervention (emergency, unusual activity, etc.) |

---

## Emergency Stop Activation

### Scenario 1: Automatic Activation (Circuit Breaker)

**What happens:**
1. Risk service detects daily loss exceeds limit (e.g., -5.2% > -5.0%)
2. Kill-switch automatically activates
3. All services immediately stop accepting new orders
4. Logs show: `🚨 KILL-SWITCH ACTIVATED - ALL TRADING STOPPED 🚨`
5. Alert sent to monitoring/alerting system

**Operator Response:**
1. Acknowledge alert
2. Check kill-switch status:
   ```python
   from core.safety import KillSwitch
   ks = KillSwitch()
   state, reason, message, activated_at = ks.get_state()
   print(f"State: {state}, Reason: {reason}, Message: {message}")
   ```
3. Investigate root cause
4. DO NOT deactivate until issue resolved
5. Follow deactivation procedure (see below)

---

### Scenario 2: Manual Activation (Operator)

**When to manually activate:**
- Unusual market activity (flash crash, extreme volatility)
- Suspected system malfunction
- Exchange degraded performance
- Testing/maintenance
- Any situation where trading should be paused

**How to activate manually:**

```python
from core.safety import activate_kill_switch, KillSwitchReason

# Activate with reason and operator ID
activate_kill_switch(
    reason=KillSwitchReason.MANUAL,
    message="Unusual market volatility - investigating",
    operator="your.email@example.com"
)

# Verify activation
from core.safety import get_kill_switch_state
print(f"Kill-switch active: {get_kill_switch_state()}")  # Should print True
```

**Via CLI (if implemented):**
```powershell
# Future implementation
python -m core.safety.cli activate --reason manual --message "Emergency stop" --operator admin
```

---

## Emergency Stop Deactivation

### Prerequisites for Deactivation

Before deactivating, ensure:
- [ ] Root cause identified and resolved
- [ ] System health verified (all services healthy)
- [ ] Risk limits verified (within acceptable ranges)
- [ ] Exchange connection stable
- [ ] No ongoing critical errors in logs
- [ ] Approval from authorized personnel (if required)

### Deactivation Procedure

**Step 1: Verify System Health**
```powershell
# Check all services healthy
make docker-health

# Check recent logs for errors
docker logs cdb_risk --tail 50 | Select-String "ERROR"
docker logs cdb_execution --tail 50 | Select-String "ERROR"
docker logs cdb_core --tail 50 | Select-String "ERROR"

# Verify Redis and Postgres connections
curl http://localhost:8002/health  # risk service
curl http://localhost:8003/health  # execution service
```

**Step 2: Deactivate Kill-Switch**
```python
from core.safety import KillSwitch

ks = KillSwitch()

# Deactivate with operator ID and justification (REQUIRED)
result = ks.deactivate(
    operator="your.email@example.com",
    justification="Circuit breaker triggered at -5.2% loss. Root cause: faulty signal from strategy X. Signal disabled. Risk limits verified. Safe to resume trading."
)

if result:
    print("✅ Kill-switch deactivated - Trading resumed")
else:
    print("❌ Deactivation failed - check logs")
```

**Step 3: Verify Deactivation**
```python
from core.safety import get_kill_switch_state

print(f"Kill-switch active: {get_kill_switch_state()}")  # Should print False
```

**Step 4: Monitor Resume**
```powershell
# Watch logs for resumed activity
make docker-logs

# Monitor for 5 minutes to ensure no immediate re-trigger
# Check first few trades execute successfully
```

---

## Persistence & Restart Behavior

### Kill-Switch State File

**Location:** `.cdb_kill_switch.state` (project root)

**Format:**
```
state=active|inactive
reason=manual|circuit_breaker|risk_limit|system_error|exchange_error|auth_failure|none
message=Human-readable explanation
activated_at=2025-12-27T14:30:00.123456|none
updated_at=2025-12-27T14:30:00.123456
```

**Persistence Rules:**
1. State persists across ALL service restarts
2. Docker container restarts → Kill-switch state PRESERVED
3. Server reboots → Kill-switch state PRESERVED (file-based)
4. Only explicit deactivation clears the kill-switch

### Service Restart Behavior

**When kill-switch is ACTIVE during restart:**
```
1. Service starts
2. Reads kill-switch state file
3. Detects ACTIVE state
4. Logs: "🚨 KILL-SWITCH ACTIVE - Trading disabled"
5. Service runs in safe mode (no order processing)
6. Waits for manual deactivation
```

**When kill-switch is INACTIVE during restart:**
```
1. Service starts
2. Reads kill-switch state file
3. Detects INACTIVE state
4. Logs: "Kill-switch inactive - Normal operation"
5. Service operates normally
```

---

## Audit Trail

### What is Logged

Every activation and deactivation is logged with:
- **Timestamp** (ISO 8601 UTC)
- **State** (ACTIVE / INACTIVE)
- **Reason** (MANUAL, CIRCUIT_BREAKER, etc.)
- **Message** (Human-readable explanation)
- **Operator** (Email/ID of person who triggered action)

### Viewing Audit Trail

**Check current state:**
```python
from core.safety import KillSwitch

ks = KillSwitch()
state, reason, message, activated_at = ks.get_state()

print(f"Current State: {state.value}")
print(f"Reason: {reason}")
print(f"Message: {message}")
print(f"Activated At: {activated_at}")
```

**View state file directly:**
```powershell
Get-Content .cdb_kill_switch.state
```

**View logs:**
```powershell
# Search for kill-switch events in logs
docker logs cdb_risk | Select-String "KILL-SWITCH"
docker logs cdb_execution | Select-String "KILL-SWITCH"
```

---

## Testing

### Unit Tests
```powershell
python -m pytest tests/unit/safety/test_kill_switch.py -vv
```

**Expected:** All tests pass

### Integration Tests
```powershell
python -m pytest tests/integration/test_emergency_stop.py -v
```

**Expected:** All tests pass

### Manual Testing (Safe Environment)

**Test Activation:**
```python
from core.safety import activate_kill_switch, KillSwitchReason

# ONLY in dev/test environment
activate_kill_switch(KillSwitchReason.MANUAL, "Test activation")
```

**Test Persistence:**
```powershell
# 1. Activate kill-switch (see above)
# 2. Restart services
make docker-down
make docker-up
# 3. Verify kill-switch still active (check logs or state file)
```

**Test Deactivation:**
```python
from core.safety import KillSwitch

ks = KillSwitch()
ks.deactivate("test_operator", "Test complete")
```

---

## Troubleshooting

### Kill-Switch Won't Deactivate

**Symptoms:**
- `deactivate()` returns `False`
- State remains ACTIVE after deactivation attempt

**Causes & Fixes:**
1. **Missing operator:** Provide operator ID
   ```python
   ks.deactivate("your.email@example.com", "Justification")
   ```

2. **Missing justification:** Provide detailed justification
   ```python
   ks.deactivate("admin", "Issue X resolved, verified system health")
   ```

3. **File permission error:** Check state file permissions
   ```powershell
   ls .cdb_kill_switch.state  # Should be writable
   ```

---

### State File Corrupted

**Symptoms:**
- Kill-switch always reports ACTIVE (even after deactivation)
- Services log "State file read error"

**Recovery:**
1. Stop all services
   ```powershell
   make docker-down
   ```

2. Backup corrupted file
   ```powershell
   cp .cdb_kill_switch.state .cdb_kill_switch.state.corrupted.$(Get-Date -Format "yyyyMMdd_HHmmss")
   ```

3. Delete corrupted file
   ```powershell
   rm .cdb_kill_switch.state
   ```

4. Restart services (new state file created as INACTIVE)
   ```powershell
   make docker-up
   ```

5. Verify state
   ```python
   from core.safety import get_kill_switch_state
   print(get_kill_switch_state())  # Should be False
   ```

---

### Kill-Switch Not Activating Automatically

**Symptoms:**
- Circuit breaker condition met but kill-switch not activated
- No "KILL-SWITCH ACTIVATED" log messages

**Diagnosis:**
1. Check risk service logs for circuit breaker trigger
   ```powershell
   docker logs cdb_risk --tail 100 | Select-String "circuit"
   ```

2. Verify kill-switch integration in risk service
   ```powershell
   docker logs cdb_risk | Select-String "kill"
   ```

3. Check state file writable
   ```powershell
   Test-Path .cdb_kill_switch.state -PathType Leaf
   ```

**Fix:**
- If not integrated yet, services need to call `activate_kill_switch()` when conditions met
- Verify services have access to state file

---

## Escalation Matrix

| Scenario | Action | Contact |
|----------|--------|---------|
| Kill-switch auto-activated | Acknowledge, investigate, follow SOP | On-call engineer |
| Cannot deactivate | Escalate to senior engineer | Tech lead |
| Repeated auto-activations | Review trading strategy / risk limits | Risk manager |
| State file corruption | Follow recovery procedure | DevOps / SRE |
| Production incident | Activate manually, investigate | Incident commander |

---

## Checklist for Production Use

Before deploying to production:
- [ ] Unit tests passing (test_kill_switch.py)
- [ ] Integration tests passing (test_emergency_stop.py)
- [ ] Manual activation tested in staging
- [ ] Manual deactivation tested in staging
- [ ] Persistence tested (restart services with active kill-switch)
- [ ] Audit trail verified (state file records all events)
- [ ] SOP reviewed by team
- [ ] Escalation contacts defined
- [ ] Monitoring/alerting configured for kill-switch events

---

## References

- **Code:** `core/safety/kill_switch.py`
- **Unit Tests:** `tests/unit/safety/test_kill_switch.py`
- **Integration Tests:** `tests/integration/test_emergency_stop.py`
- **Related:** `docs/TRADING_MODES.md` (trading mode safety)
- **Issue:** #250 (Emergency Stop Mechanism)

---

**Last Updated:** 2025-12-27
**Status:** ✅ Implemented (Issue #250)
**Approved By:** [Pending]
**Review Date:** [Pending]
