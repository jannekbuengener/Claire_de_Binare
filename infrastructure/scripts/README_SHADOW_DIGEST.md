# Shadow Mode Daily Digest Generator

**Purpose:** Generate executive summary for Shadow Mode (last 24h UTC) with status, KPIs, alerts, incidents, and actions.

**Output:** `reports/shadow_mode/DAILY_DIGEST_<YYYY-MM-DD>.md` (max 1 page)

**Boundary:** Shadow/offline evidence only — **kein** LR-Go, **kein** Live-Kapital, **kein** Echtgeld-Signal (`docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`).

---

## Usage

### Manual Generation

```bash
# Generate digest for today (UTC)
python infrastructure/scripts/generate_shadow_digest.py

# Generate digest for specific date
python infrastructure/scripts/generate_shadow_digest.py --date 2026-01-19

# Generate and send via email (optional)
python infrastructure/scripts/generate_shadow_digest.py --email
```

### Automated Generation (Cron/Task Scheduler)

**Linux/Mac (crontab):**
```cron
# Run daily at 00:05 UTC (after day rollover)
5 0 * * * cd /path/to/Claire_de_Binare && python infrastructure/scripts/generate_shadow_digest.py
```

**Windows (Task Scheduler):**
```powershell
# Create scheduled task (run daily at 00:05)
$action = New-ScheduledTaskAction -Execute "python" -Argument "infrastructure/scripts/generate_shadow_digest.py" -WorkingDirectory "D:\Dev\Workspaces\Repos\Claire_de_Binare"
$trigger = New-ScheduledTaskTrigger -Daily -At "00:05"
Register-ScheduledTask -TaskName "ShadowModeDigest" -Action $action -Trigger $trigger
```

---

## Digest Structure

### 1. Status Ampel
```
Status: GREEN/YELLOW/RED
Reason: One-line explanation
```

**Logic:**
- **RED:** Critical alerts firing OR approval rate < 10%
- **YELLOW:** Pipeline stalled OR 3+ warning alerts OR degraded operation
- **GREEN:** Normal operation (trades flowing, approval rate > 50%)

### 2. KPIs (Last 24h)

**Signal Flow:**
- Signals Received (total)
- Orders Approved (total)
- Orders Blocked (total)
- Approval Rate (%)

**Execution:**
- Trades Filled (total)
- Trades Rejected (total)
- Fill Rate (%)

### 3. Top 3 Alerts
- Alert name
- Count (last 24h)
- Max severity (critical/warning)

### 4. Incidents / Breakpoints
- Active stalls or breakpoints
- Time window, severity, current state

### 5. Actions

**Changes Today:**
- Top 5 git commits (last 24h)

**Decisions Needed Tomorrow:**
- Max 3 actionable items based on status

---

## Data Sources

### Prometheus Metrics (24h)
```bash
# Signal flow
increase(signals_received_total[24h])
increase(orders_approved_total[24h])
increase(orders_blocked_total[24h])

# Execution
increase(execution_orders_filled_total[24h])
increase(execution_orders_rejected_total[24h])
```

### Prometheus Alerts
```bash
# All active alerts
docker exec cdb_prometheus wget -qO- "http://localhost:9090/api/v1/alerts"
```

### Git Changes
```bash
# Commits last 24h
git log --since=24.hours --oneline --no-merges
```

---

## Reproducibility

**Every digest includes evidence commands** in the appendix for manual verification:

```bash
# Reproduce digest
python infrastructure/scripts/generate_shadow_digest.py --date 2026-01-19

# Manual data collection (same queries used by script)
docker exec cdb_prometheus wget -qO- "http://localhost:9090/api/v1/query?query=increase(signals_received_total[24h])"
docker exec cdb_prometheus wget -qO- "http://localhost:9090/api/v1/alerts"
git log --since=24.hours --oneline --no-merges
```

---

## Email Configuration (Optional)

### Setup SMTP (Grafana)

**Prerequisites:**
- Grafana SMTP configured in `infrastructure/compose/compose.red.yml` (RED monitoring stack)
- `base.yml` ist CI/lab baseline, nicht der kanonische Operator-Grafana-Pfad
- Secrets: `smtp_user`, `smtp_password`, `smtp_from`, `alert_email_to`

**Current Status:** Email sending placeholder implemented (requires Grafana SMTP API integration)

**Future Implementation:**
```python
# Send via Grafana API or direct SMTP
python infrastructure/scripts/generate_shadow_digest.py --email
```

---

## Troubleshooting

### Script Fails with "Prometheus not reachable"

**Check Prometheus container:**
```bash
docker ps --filter name=cdb_prometheus
docker logs cdb_prometheus --tail 50
```

**Test Prometheus API:**
```bash
docker exec cdb_prometheus wget -qO- "http://localhost:9090/-/healthy"
```

### Metrics Show Zero

**Verify Prometheus scraping:**
```bash
# Check targets
curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job, health, lastError}'

# Check metric exists
docker exec cdb_prometheus wget -qO- "http://localhost:9090/api/v1/label/__name__/values" | grep signals_received_total
```

### Git Changes Empty

**Check git log:**
```bash
# Verify commits exist
git log --since=24.hours --oneline

# Check current branch
git branch --show-current
```

---

## Integration with Monitoring

### Daily Digest as Alerting Input

**Use digest status for escalation:**
```yaml
# Alert if digest shows RED status 2 days in a row
alert: ShadowModeDigestRed
expr: |
  count(
    changes in (vector(1))[2d:1d]
    where digest_status == "RED"
  ) >= 2
```

### Digest Archive

**Digests stored in:** `reports/shadow_mode/DAILY_DIGEST_*.md`

**Retention:** Indefinite (git-tracked)

**Query historical status:**
```bash
# Find all RED status days
grep -r "Status: RED" reports/shadow_mode/DAILY_DIGEST_*.md

# Count digest files
ls -1 reports/shadow_mode/DAILY_DIGEST_*.md | wc -l
```

---

## Example Digest

**File:** `reports/shadow_mode/DAILY_DIGEST_2026-01-19.md`

```markdown
# Shadow Mode Daily Digest - 2026-01-19

## Status: RED
**2 critical alert(s) firing**

## KPIs (Last 24h)
- Signals Received: 3230
- Orders Approved: 0
- Orders Blocked: 3230
- Approval Rate: 0.0%
- Trades Filled: 0

## Top 3 Alerts
- DatabaseConnectionLost: 1 (critical)
- RedisConnectionLost: 1 (critical)
- TradePipelineStalled: 1 (warning)

## Actions
- **URGENT:** Resolve critical alerts
- **WARNING:** Investigate low approval rate
- **WARNING:** Fix pipeline stall
```

---

## Development

### Script Location
`infrastructure/scripts/generate_shadow_digest.py`

### Dependencies
- Python 3.8+
- Docker (for Prometheus queries)
- Git (for commit history)

### Testing
```bash
# Dry run (no file write)
python infrastructure/scripts/generate_shadow_digest.py --date 2026-01-19

# Verify output
cat reports/shadow_mode/DAILY_DIGEST_2026-01-19.md
```

---

## Related Documentation

- [TradePipelineStalled Alert](../infrastructure/monitoring/alerts.yml#L243)
- [Daily Digest Policy](../reports/shadow_mode/ALERTING_DIGEST_POLICY.md)
- [PRE_INCIDENT_EVAL Report](../reports/shadow_mode/PRE_INCIDENT_EVAL_until_2026-01-17T21_17_02Z.md)

---

*Shadow Mode Daily Digest Documentation - Claire de Binare Trading Bot*
