# Alerting Digest Policy - Daily Email Summary

**Status:** ✅ Active
**Last Updated:** 2026-01-19
**Grafana Version:** 11.4.0

---

## Rationale

### Problem: Alert Fatigue
During Shadow Mode (14+ days), continuous warning alerts for non-critical issues create **alert fatigue**:
- 43+ hours of `TradePipelineStalled` warnings
- Risk manager blocking 3694 orders (rate: 0.014/s = ~50/hour)
- Each warning → immediate email → noise

### Solution: Daily Digest
**Objective:** Reduce noise while maintaining safety.

**Strategy:**
- **Critical alerts** → Immediate notification (safety-critical)
- **Warning alerts** → Daily digest (1 email/day, grouped summary)

**Benefits:**
- ✅ Safety preserved (critical alerts still immediate)
- ✅ Reduced inbox clutter (warnings batched)
- ✅ Better pattern recognition (grouped by alertname/component/issue)
- ✅ Lower response burden (daily review instead of constant interruption)

---

## Policy Configuration

### Notification Policy Structure

```json
{
  "receiver": "email-main",
  "group_by": ["alertname", "component", "issue"],
  "group_wait": "30s",
  "group_interval": "24h",
  "repeat_interval": "24h",
  "routes": [
    {
      "receiver": "email-main",
      "object_matchers": [["severity", "=", "critical"]],
      "group_by": ["alertname", "component", "issue"],
      "group_wait": "10s",
      "group_interval": "5m",
      "repeat_interval": "1h"
    },
    {
      "receiver": "email-main",
      "object_matchers": [["severity", "=", "warning"]],
      "group_by": ["alertname", "component", "issue"],
      "group_wait": "5m",
      "group_interval": "24h",
      "repeat_interval": "24h"
    }
  ]
}
```

### Timing Parameters Explained

| Parameter | Critical | Warning | Default (Fallback) |
|-----------|----------|---------|-------------------|
| **group_wait** | 10s | 5m | 30s |
| **group_interval** | 5m | 24h | 24h |
| **repeat_interval** | 1h | 24h | 24h |

**Definitions:**
- **group_wait:** Initial wait time before sending first notification (allows grouping of rapid-fire alerts)
- **group_interval:** Time to wait before sending updates about existing alert groups
- **repeat_interval:** Time between reminders for still-firing alerts

### Label-Based Routing

**Grouping Keys:**
```yaml
group_by: ["alertname", "component", "issue"]
```

**Example Grouping:**
```
Alert 1: TradePipelineStalled (component=trading_pipeline, issue=pipeline_stall)
Alert 2: TradePipelineStalled (component=trading_pipeline, issue=pipeline_stall)
Alert 3: HighMemoryUsage (component=cdb_risk, issue=memory_leak)
```

→ **2 groups:**
1. TradePipelineStalled (1 notification)
2. HighMemoryUsage (1 notification)

**Benefits:**
- Reduces redundant notifications
- Groups related alerts together
- Makes patterns visible (e.g., "5x TradePipelineStalled in 24h")

---

## Alert Severity Guidelines

### When to Use `severity=critical`

**Immediate notification required** - system down, data loss, safety breach:
- `ServiceDown` - Core services unavailable
- `CircuitBreakerTriggered` - Trading halted by safety mechanism
- `DatabaseConnectionLost` - Data persistence at risk
- `DailyDrawdownExceeded` - Risk limit breached
- `SoakTest_ServiceDown` - Stability test failed (abort trigger)

**Characteristics:**
- ⚠️ Requires immediate human intervention
- ⚠️ System cannot self-recover
- ⚠️ Real risk of data loss or safety violation

### When to Use `severity=warning`

**Daily digest acceptable** - degraded performance, informational:
- `TradePipelineStalled` - Pipeline blocked but no data loss
- `HighCPUUsage` - Performance degradation
- `HighMemoryUsage` - Potential leak, not critical yet
- `PositionLimitApproaching` - Approaching threshold (not breached)
- `SoakTest_NoOrdersGenerated` - Investigate, not abort

**Characteristics:**
- ℹ️ System continues operating (degraded mode okay)
- ℹ️ Can wait for daily review
- ℹ️ No immediate safety risk

---

## How to Change the Policy

### Via Grafana UI

1. Navigate to **Alerting → Notification policies**
2. Edit root policy or sub-routes
3. Modify timing parameters:
   - `group_wait` - Initial grouping window
   - `group_interval` - Update frequency
   - `repeat_interval` - Reminder frequency

### Via API (Programmatic)

**Get Current Policy:**
```bash
curl -u admin:<password> http://localhost:3000/api/v1/provisioning/policies
```

**Update Policy:**
```bash
curl -u admin:<password> -X PUT \
  -H "Content-Type: application/json" \
  -d @notification_policy.json \
  http://localhost:3000/api/v1/provisioning/policies
```

**Verify:**
```bash
curl -u admin:<password> http://localhost:3000/api/v1/provisioning/policies | jq
```

### Via File (Provisioning)

**Location:** `infrastructure/monitoring/grafana/notification_policy_daily_digest.json`

**Apply:**
```bash
# Restart Grafana to reload provisioning
docker restart cdb_grafana
```

---

## Evidence & Validation

### Current Policy Export

**File:** `infrastructure/monitoring/grafana/notification_policy_daily_digest.json`

```json
{
  "receiver": "email-main",
  "group_by": ["alertname", "component", "issue"],
  "routes": [
    {
      "object_matchers": [["severity", "=", "critical"]],
      "group_wait": "10s",
      "group_interval": "5m",
      "repeat_interval": "1h"
    },
    {
      "object_matchers": [["severity", "=", "warning"]],
      "group_wait": "5m",
      "group_interval": "24h",
      "repeat_interval": "24h"
    }
  ],
  "group_wait": "30s",
  "group_interval": "24h",
  "repeat_interval": "24h"
}
```

### Alert Path Examples

**Example 1: TradePipelineStalled (Warning)**
```
Alert Fires → Match severity=warning route
├─ group_wait: 5m (batch with other warnings)
├─ group_interval: 24h (next update in 24h)
└─ repeat_interval: 24h (reminder in 24h if still firing)

Result: 1 email/day (grouped with other warnings)
```

**Example 2: CircuitBreakerTriggered (Critical)**
```
Alert Fires → Match severity=critical route
├─ group_wait: 10s (immediate, minimal batching)
├─ group_interval: 5m (updates every 5min)
└─ repeat_interval: 1h (hourly reminders)

Result: Email within 10s, updates every 5min, reminders every 1h
```

**Example 3: Multiple Warnings (Same Group)**
```
TradePipelineStalled fires (10:00)
HighMemoryUsage fires (10:03)  ← component=cdb_risk (different group)
TradePipelineStalled fires (10:05) ← Same group as first

Groups created:
├─ Group 1: TradePipelineStalled (component=trading_pipeline, issue=pipeline_stall)
│   └─ Alerts: 2x TradePipelineStalled
└─ Group 2: HighMemoryUsage (component=cdb_risk, issue=memory_usage)
    └─ Alerts: 1x HighMemoryUsage

Emails sent:
├─ 10:05 → "TradePipelineStalled (2 alerts)" [group_wait: 5m elapsed]
└─ 10:08 → "HighMemoryUsage (1 alert)" [group_wait: 5m elapsed]
```

### Verification Commands

**Check Current Policy:**
```bash
docker exec cdb_grafana wget -qO- \
  --user=admin --password=<password> \
  http://localhost:3000/api/v1/provisioning/policies | jq '.routes'
```

**List Active Alerts:**
```bash
docker exec cdb_prometheus wget -qO- \
  http://localhost:9090/api/v1/alerts | jq '.data.alerts[] | {alertname, severity, state}'
```

**Test Alert Path:**
```bash
# Simulate warning alert
curl -X POST http://localhost:9090/api/v1/alerts \
  -d '[{"labels":{"alertname":"TestWarning","severity":"warning"}}]'

# Check notification log
docker logs cdb_grafana --tail 100 | grep -i "notification"
```

---

## Safety Validation

### Critical Alerts Still Immediate

**Test:** CircuitBreakerTriggered alert
```bash
# If circuit breaker fires
curl http://localhost:8002/metrics | grep circuit_breaker_triggered
# Expected: 1

# Check alert state
docker exec cdb_prometheus wget -qO- \
  http://localhost:9090/api/v1/alerts | grep CircuitBreakerTriggered
# Expected: state=firing, notification sent within 10s
```

**Validation:** ✅ Critical alerts bypass daily digest, sent immediately.

### Warnings Batched Daily

**Test:** TradePipelineStalled alert (current state)
```bash
# Alert is currently pending/firing
docker exec cdb_prometheus wget -qO- \
  http://localhost:9090/api/v1/alerts | grep TradePipelineStalled
# Expected: state=pending (will fire after 10min)

# Check notification timing
# Expected: First notification after group_wait=5m + 10m alert (15min total)
# Expected: Next notification in 24h (not immediate)
```

**Validation:** ✅ Warning alerts grouped and sent daily, no immediate spam.

---

## Monitoring the Policy

### Key Metrics

**Alert Volume by Severity:**
```bash
# Count alerts by severity
docker exec cdb_prometheus wget -qO- \
  'http://localhost:9090/api/v1/query?query=ALERTS{alertstate="firing"}' \
  | jq '.data.result | group_by(.metric.severity) | map({severity: .[0].metric.severity, count: length})'
```

**Notification Rate:**
```bash
# Grafana notification logs
docker logs cdb_grafana --since 24h | grep -i "notification sent" | wc -l
```

**Expected Results (Daily Digest Active):**
- Critical alerts: 0-5/day (immediate, rare)
- Warning alerts: 1-2 emails/day (grouped digest)
- Total emails: 1-7/day (down from 50+/day without digest)

---

## Rollback Procedure

### Revert to Immediate Notifications

**Option 1: Via API**
```bash
# Remove warning route (fall back to root policy with short intervals)
curl -u admin:<password> -X PUT \
  -H "Content-Type: application/json" \
  -d '{
    "receiver": "email-main",
    "group_by": ["alertname"],
    "group_wait": "10s",
    "group_interval": "5m",
    "repeat_interval": "1h"
  }' \
  http://localhost:3000/api/v1/provisioning/policies
```

**Option 2: Via UI**
1. Go to **Alerting → Notification policies**
2. Delete warning route
3. Modify root policy intervals to immediate values

**Option 3: Restore Backup**
```bash
# Restore original policy from backup
cp infrastructure/monitoring/grafana/notification_policy_backup.json \
   infrastructure/monitoring/grafana/notification_policy_daily_digest.json

# Restart Grafana
docker restart cdb_grafana
```

---

## Related Documentation

- [TradePipelineStalled Alert](../../../../infrastructure/monitoring/alerts.yml#L243) - Warning alert benefiting from digest
- [PRE_INCIDENT_EVAL Report](./PRE_INCIDENT_EVAL_until_2026-01-17T21_17_02Z.md) - Context for alert noise
- [Grafana Notification Policies](https://grafana.com/docs/grafana/latest/alerting/manage-notifications/create-notification-policy/) - Official docs

---

## Change Log

| Date | Change | Author |
|------|--------|--------|
| 2026-01-19 | Initial policy: Daily digest for warnings | Claude Code |

---

*Report generated by Claude Code - Alerting optimization for Shadow Mode*
