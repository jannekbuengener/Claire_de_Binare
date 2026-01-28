# Operator Drill Blueprint

**Status:** Draft / Blueprint
**Scope:** Operational Readiness & Safety
**Issue:** #662

## 1. Objective
Demonstrate that a human operator (or automated watchdog) can stop the system within **30 seconds** (SLA) and produce verifiable evidence of the stoppage.

## 2. Prerequisites
- System running (Dev or Shadow/Prod)
- Alertmanager/Notification channel configured
- `trigger-operator-drill.ps1` available

## 3. Drill Sequence

| Step | Action | Expected Outcome | Evidence Artifact |
|------|--------|------------------|-------------------|
| 1 | **Trigger Alert** | Alertmanager sends "DRILL: High Latency" warning | `alert_payload.json` |
| 2 | **Activate Kill-Switch** | Operator runs `make kill-switch-activate` | `kill_switch.state` / Redis Key |
| 3 | **Inject Test Signal** | `cdb_signal` receives test payload | `signal_injection.log` |
| 4 | **Verify Block** | `cdb_risk` rejects signal (REASON: EMERGENCY_STOP) | `risk_service_rejection.log` |
| 5 | **Resume** | Operator runs `make kill-switch-deactivate` | `system_recovery.log` |

## 4. Evidence Package Schema (`timeline.json`)

The drill script MUST produce a JSON timeline adhering to this structure:

```json
{
  "drill_id": "DRILL-20260128-001",
  "operator": "cdb-admin",
  "start_time": "2026-01-28T10:00:00Z",
  "steps": [
    {
      "id": "alert_trigger",
      "timestamp": "2026-01-28T10:00:01Z",
      "status": "PASS",
      "details": "Webhook received 200 OK"
    },
    {
      "id": "kill_switch_activation",
      "timestamp": "2026-01-28T10:00:15Z",
      "status": "PASS",
      "details": "State file created / Redis key set"
    },
    {
      "id": "order_block_verification",
      "timestamp": "2026-01-28T10:00:16Z",
      "status": "PASS",
      "details": "Risk service rejected signal: MANUAL_STOP"
    }
  ],
  "sla_met": true,
  "total_duration_ms": 15000
}
```

## 5. Failure Conditions
- **FAIL**: Orders processed despite active kill-switch.
- **FAIL**: Drill takes > 30s to activate stop.
- **FAIL**: No evidence produced.
- **FAIL**: Stack crashes instead of graceful halt.
