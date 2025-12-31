# Alerting Runbook

**Status:** ✅ ACTIVE (Alertmanager deployed)
**Issue:** #352
**Created:** 2025-12-30
**Author:** Claude (Session Lead)

---

## Quick Start (2 Minutes)

### 1. Start Stack mit Alertmanager

```powershell
# Windows (PowerShell)
.\infrastructure\scripts\stack_up.ps1 -Logging

# Verify Alertmanager is up
docker ps | Select-String alertmanager
```

### 2. Check Prometheus Target

```powershell
# Open Prometheus UI
Start-Process "http://localhost:9090/targets"

# Verify: Target "alertmanager" should be UP
# URL: http://alertmanager:9093/api/v1/alerts
```

### 3. Trigger Test Alert

```powershell
# Prometheus Expression Browser
# Navigate to: http://localhost:9090/graph

# Execute test expression (pending then firing after 30s):
ALERTS{alertname="AlertmanagerTest"}

# Check Alertmanager UI:
Start-Process "http://localhost:9093"
```

---

## Alertmanager URLs

| URL | Purpose |
|-----|---------|
| `http://localhost:9093` | Alertmanager UI (Dashboard) |
| `http://localhost:9093/#/alerts` | Active Alerts |
| `http://localhost:9093/#/silences` | Silences Management |
| `http://localhost:9093/api/v1/alerts` | Alerts API (JSON) |
| `http://localhost:9093/-/healthy` | Health Check |

---

## Alert Severity Levels

| Severity | Group Wait | Repeat Interval | Receiver |
|----------|------------|-----------------|----------|
| **critical** | 0s (immediate) | 5min | `critical-receiver` |
| **high** | 30s | 1h | `high-receiver` |
| **warning** | 1min | 4h | `warning-receiver` |
| **default** | 10s | 12h | `default-receiver` |

---

## Common Operations

### View Active Alerts

```powershell
# Via curl/Invoke-WebRequest
Invoke-WebRequest http://localhost:9093/api/v1/alerts | ConvertFrom-Json | ConvertTo-Json -Depth 5

# Via Alertmanager UI
Start-Process "http://localhost:9093/#/alerts"
```

### Silence an Alert

```powershell
# Via UI (recommended)
Start-Process "http://localhost:9093/#/silences"
# Click "New Silence", fill matchers, duration

# Via API (advanced)
$silence = @{
    matchers = @(
        @{name="alertname"; value="HighCPUUsage"; isRegex=$false}
    )
    startsAt = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
    endsAt = (Get-Date).AddHours(1).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
    comment = "Maintenance window"
    createdBy = "ops@cdb"
} | ConvertTo-Json

Invoke-WebRequest -Uri "http://localhost:9093/api/v1/silences" `
    -Method POST `
    -ContentType "application/json" `
    -Body $silence
```

### Test Alert Rules

```powershell
# Via Prometheus
# Navigate to: http://localhost:9090/alerts

# Check rule evaluation:
# - Pending: Rule condition met, but group_wait not elapsed
# - Firing: Alert sent to Alertmanager
# - Inactive: Rule condition not met
```

---

## Alert Rules (Prometheus)

Alert rules are defined in `infrastructure/monitoring/alerts.yml`.

**Example Alert:**

```yaml
groups:
  - name: test_alerts
    interval: 15s
    rules:
      - alert: AlertmanagerTest
        expr: vector(1)
        for: 30s
        labels:
          severity: warning
          service: test
        annotations:
          summary: "Alertmanager test alert (pending then firing)"
          description: "This alert fires after 30s for testing purposes"
```

**Reload Prometheus Config:**

```powershell
# Reload without restart
Invoke-WebRequest -Uri "http://localhost:9090/-/reload" -Method POST

# Or restart Prometheus
docker restart cdb_prometheus
```

---

## Troubleshooting

### Alertmanager Not Showing Alerts

**Symptom:** Alerts fire in Prometheus, but don't appear in Alertmanager

**Check:**

```powershell
# 1. Verify Prometheus → Alertmanager connection
# http://localhost:9090/status → "Runtime & Build Information" → "Alertmanagers"
# Should show: http://alertmanager:9093/api/v2/alerts (state: UP)

# 2. Check Prometheus logs
docker logs cdb_prometheus | Select-String -Pattern "alertmanager|error"

# 3. Check Alertmanager logs
docker logs cdb_alertmanager | Select-String -Pattern "error|warn"

# 4. Verify network connectivity
docker exec cdb_prometheus wget -qO- http://alertmanager:9093/-/healthy
```

**Solution:**

```powershell
# If Alertmanager shows as DOWN:
# 1. Check alertmanager container is running
docker ps -a | Select-String alertmanager

# 2. Verify network (both containers on cdb_network)
docker inspect cdb_prometheus | Select-String NetworkMode
docker inspect cdb_alertmanager | Select-String NetworkMode

# 3. Restart stack
.\infrastructure\scripts\stack_down.ps1
.\infrastructure\scripts\stack_up.ps1 -Logging
```

---

### Alert Not Routing to Receiver

**Symptom:** Alert appears in Alertmanager, but no notification sent

**Check:**

```powershell
# 1. Check receiver config
cat infrastructure/monitoring/alertmanager.yml | Select-String -Pattern "receiver|webhook"

# 2. Check Alertmanager logs for webhook attempts
docker logs cdb_alertmanager | Select-String -Pattern "webhook|notify"

# 3. Test webhook endpoint (if using real receiver)
Invoke-WebRequest http://localhost:9099/webhook -Method POST -Body '{"test": "alert"}'
```

**Solution:**

```powershell
# For testing (no real receiver yet):
# Alertmanager will log errors about unreachable webhook (expected)
# This is normal until real notification channel is configured (Slack, PagerDuty, etc.)

# To configure real receiver, edit:
# infrastructure/monitoring/alertmanager.yml
# Replace webhook_configs with:
# - slack_configs (for Slack)
# - pagerduty_configs (for PagerDuty)
# - email_configs (for Email)
```

---

### Prometheus Not Loading Alert Rules

**Symptom:** Alert rules don't appear in Prometheus UI

**Check:**

```powershell
# 1. Verify alerts.yml syntax
cat infrastructure/monitoring/alerts.yml

# 2. Check Prometheus logs
docker logs cdb_prometheus | Select-String -Pattern "error|alert|rule"

# 3. Check rule file path in prometheus.yml
cat infrastructure/monitoring/prometheus.yml | Select-String -Pattern "rule_files"
```

**Solution:**

```powershell
# If syntax error in alerts.yml:
# 1. Validate YAML syntax (https://www.yamllint.com/)
# 2. Fix errors
# 3. Reload Prometheus:
Invoke-WebRequest -Uri "http://localhost:9090/-/reload" -Method POST

# If rules.yml not found:
# 1. Check volume mount in base.yml
docker inspect cdb_prometheus | Select-String -Pattern "alerts.yml"

# 2. Verify file exists in container
docker exec cdb_prometheus ls -la /etc/prometheus/alerts.yml
```

---

## Evidence & Validation

### Proof of Alertmanager Operation

**1. Target UP in Prometheus:**

```powershell
# Navigate to: http://localhost:9090/targets
# Look for: alertmanager (1/1 up)
```

**2. Alert Firing in Alertmanager:**

```powershell
# Navigate to: http://localhost:9093/#/alerts
# Look for test alert (if configured)
```

**3. Healthcheck:**

```powershell
# Should return HTTP 200
Invoke-WebRequest http://localhost:9093/-/healthy
```

---

## Next Steps (Future Integration)

### Replace Placeholder Receivers

**Slack Integration:**

```yaml
receivers:
  - name: 'slack-critical'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL'
        channel: '#cdb-alerts-critical'
        title: 'CDB Alert: {{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
```

**PagerDuty Integration:**

```yaml
receivers:
  - name: 'pagerduty-critical'
    pagerduty_configs:
      - service_key: 'YOUR_PAGERDUTY_KEY'
        description: '{{ .GroupLabels.alertname }}: {{ .CommonAnnotations.summary }}'
```

**Email Integration:**

```yaml
receivers:
  - name: 'email-team'
    email_configs:
      - to: 'team@example.com'
        from: 'alertmanager@cdb.local'
        smarthost: 'smtp.gmail.com:587'
        auth_username: 'alertmanager@cdb.local'
        auth_password: 'YOUR_PASSWORD'
```

---

## References

- Alertmanager Docs: https://prometheus.io/docs/alerting/latest/alertmanager/
- Alert Rules: https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/
- Issue: #352
- Epic: #346 (Phase 0 – Shipability Base)
