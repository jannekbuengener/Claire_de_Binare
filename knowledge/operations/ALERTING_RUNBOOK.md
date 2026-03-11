# Alerting Runbook - Quick Alert Testing

**Version:** 1.0
**Erstellt:** 2025-12-31
**Zweck:** Alertmanager in 2 Minuten testen

---

## Prerequisites

Stack muss mit `-Logging` Flag gestartet sein:

```powershell
.\infrastructure\scripts\stack_up.ps1 -Profile dev -Logging
```

---

## Quick Check (30 Sekunden)

### 1. Container Status

```powershell
docker ps --filter "name=cdb_alertmanager" --format "table {{.Names}}\t{{.Status}}"
```

**Erwartete Ausgabe:**
```
NAMES               STATUS
cdb_alertmanager    Up X minutes (healthy)
```

### 2. Prometheus Target

```powershell
# Check Alertmanager Target
docker exec cdb_prometheus wget -qO- http://localhost:9090/api/v1/targets | Select-String "alertmanager"
```

**Erwartete Ausgabe:**
```json
{
  "status": "success",
  "data": {
    "activeTargets": [
      {
        "labels": {"job": "alertmanager"},
        "health": "up"
      }
    ]
  }
}
```

---

## Alert Test (2 Minuten)

### Test-Alert triggern

**Option 1: Manual Alert via Prometheus API**

```powershell
# POST Test-Alert
$body = @{
    "annotations" = @{
        "summary" = "Test Alert from Runbook"
        "description" = "Manual test alert to verify routing"
    }
    "labels" = @{
        "alertname" = "TestAlert"
        "severity" = "warning"
        "service" = "test"
    }
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri "http://localhost:19090/api/v1/alerts" -Body $body -ContentType "application/json"
```

**Option 2: Service Down Simulation**

```powershell
# Stop a service temporarily
docker stop cdb_ws

# Wait 60 seconds for alert to fire
Start-Sleep -Seconds 60

# Check Prometheus Alerts
docker exec cdb_prometheus wget -qO- "http://localhost:9090/api/v1/alerts" | ConvertFrom-Json | Select-Object -ExpandProperty data | Select-Object -ExpandProperty alerts | Where-Object { $_.labels.alertname -eq "ServiceDown" }

# Restart service
docker start cdb_ws
```

### Verify Alert in Alertmanager UI

**Browser:**
- URL: `http://localhost:9093` (wenn Port Binding aktiviert)
- Navigate: Alerts → Active Alerts
- Verify: TestAlert oder ServiceDown visible

**CLI:**
```powershell
docker exec cdb_alertmanager wget -qO- http://localhost:9093/api/v2/alerts | ConvertFrom-Json | Select-Object -First 3
```

---

## Alert Routing Verification

### Check Receivers

```powershell
# List configured receivers
docker exec cdb_alertmanager wget -qO- http://localhost:9093/api/v2/receivers
```

**Expected Receivers:**
- `default-receiver`
- `critical-receiver`
- `high-priority-receiver`
- `trading-halt-receiver`

### Verify Webhook (if enabled)

```powershell
# Check Signal Service logs for webhook reception
docker logs cdb_signal --tail 50 | Select-String "alert"
```

---

## Common Issues

### Alertmanager Container not healthy

```powershell
# Check logs
docker logs cdb_alertmanager --tail 30

# Common causes:
# - Config syntax error in alertmanager.yml
# - Volume mount failed
# - Network issue
```

### Prometheus can't reach Alertmanager

```powershell
# Test network connectivity
docker exec cdb_prometheus wget -qO- http://cdb_alertmanager:9093/-/healthy
```

**Expected:** `Alertmanager is Healthy.`

### Alerts not firing

```powershell
# Check Prometheus rules
docker exec cdb_prometheus wget -qO- http://localhost:9090/api/v1/rules | ConvertFrom-Json | Select-Object -ExpandProperty data | Select-Object -ExpandProperty groups | Select-Object -ExpandProperty rules | Select-Object -First 5
```

---

## Production Readiness Checklist

- [ ] Alertmanager Target shows "UP" in Prometheus
- [ ] Test alert fires and appears in Alertmanager UI
- [ ] Webhook receiver responds (check Signal Service logs)
- [ ] Critical alert routing verified (Circuit Breaker test)
- [ ] Email/Slack receivers configured (production only)
- [ ] Inhibition rules tested (ServiceDown suppresses others)

---

## Evidence Template (for Issues)

```markdown
**Alert Test Result:**

**Date:** 2025-12-31
**Stack:** dev + Logging

**1. Container Status:**
\`\`\`
cdb_alertmanager    Up 5 minutes (healthy)
\`\`\`

**2. Prometheus Target:**
\`\`\`
alertmanager: UP
\`\`\`

**3. Test Alert:**
- Alert Name: ServiceDown
- Trigger: Stopped cdb_ws for 60s
- Status: FIRING → RESOLVED
- Webhook: Received by cdb_signal (log evidence)

**4. Routing:**
- Receiver: default-receiver
- Group: alertname, severity, service
- Repeat Interval: 4h

✅ Alertmanager operational
```

---

## Quick Commands Reference

```powershell
# Start stack with Alertmanager
.\infrastructure\scripts\stack_up.ps1 -Profile dev -Logging

# Check Alertmanager health
docker exec cdb_alertmanager wget -qO- http://localhost:9093/-/healthy

# List active alerts
docker exec cdb_alertmanager wget -qO- http://localhost:9093/api/v2/alerts

# Check Prometheus targets
docker exec cdb_prometheus wget -qO- http://localhost:9090/api/v1/targets

# Trigger test alert (stop service)
docker stop cdb_ws
Start-Sleep -Seconds 60
docker start cdb_ws
```

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
