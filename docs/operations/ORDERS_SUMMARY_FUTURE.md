# Daily Orders Summary - Future Implementation

**Status:** DEFERRED (not in UI-only scope)
**Priority:** Nice-to-have
**Estimated Effort:** 2-3 hours
**Dependencies:** UI Alerting Digest must be working first

---

## Objective

Send **1 email per day** (08:00 UTC) with summary of last 24h orders:
- Total orders: created, filled, rejected, cancelled
- Top 5 rejection reasons (grouped)
- Optional: Total notional, fees, PnL

---

## Data Source

**Postgres Tables:** (already exist in schema.sql)

### Table: `orders`
```sql
-- Relevant columns:
id, order_id, symbol, side, order_type, price, size
approved, rejection_reason
status (pending|submitted|filled|partial|cancelled|rejected)
created_at, submitted_at, filled_at
```

### Table: `trades`
```sql
-- Relevant columns:
id, order_id, symbol, side, price, size
execution_price, fees, slippage_bps
timestamp
```

**Schema Path:** `infrastructure/database/schema.sql:48-133`

---

## SQL Query Template

```sql
-- Daily Orders Summary (last 24h)
WITH order_summary AS (
  SELECT
    COUNT(*) AS total_orders,
    COUNT(*) FILTER (WHERE status = 'filled') AS filled_count,
    COUNT(*) FILTER (WHERE status = 'rejected') AS rejected_count,
    COUNT(*) FILTER (WHERE status = 'cancelled') AS cancelled_count,
    COUNT(*) FILTER (WHERE status = 'pending') AS pending_count,
    SUM(size * COALESCE(avg_fill_price, price, 0)) AS total_notional
  FROM orders
  WHERE created_at >= NOW() - INTERVAL '24 hours'
),
top_rejections AS (
  SELECT
    rejection_reason,
    COUNT(*) AS count
  FROM orders
  WHERE rejection_reason IS NOT NULL
    AND created_at >= NOW() - INTERVAL '24 hours'
  GROUP BY rejection_reason
  ORDER BY count DESC
  LIMIT 5
),
trade_summary AS (
  SELECT
    COUNT(*) AS total_trades,
    SUM(size * execution_price) AS total_notional,
    SUM(fees) AS total_fees
  FROM trades
  WHERE timestamp >= NOW() - INTERVAL '24 hours'
)
SELECT
  o.*,
  t.total_trades,
  t.total_fees
FROM order_summary o, trade_summary t;
```

---

## Implementation Options

### Option 1: Python Cron Service (RECOMMENDED)

**New Files:**
- `services/reports/daily_orders_summary.py`
- `services/reports/Dockerfile`
- `services/reports/requirements.txt`
- `infrastructure/compose/reports.yml`

**Service Architecture:**
```python
# daily_orders_summary.py
import psycopg2, smtplib, time
from datetime import datetime, timezone
from email.mime.text import MIMEText

def read_secret(path):
    with open(path) as f:
        return f.read().strip()

def get_db_connection():
    dsn = read_secret('/run/secrets/postgres_password_dsn')
    return psycopg2.connect(dsn)

def fetch_summary(conn):
    with conn.cursor() as cur:
        cur.execute(SQL_QUERY)  # from template above
        return cur.fetchall()

def format_email_body(data):
    # HTML/Markdown formatting
    return f"""
    <h2>CDB Daily Orders Summary</h2>
    <p><strong>Period:</strong> {date_range}</p>

    <h3>Order Statistics</h3>
    <ul>
      <li>Total Orders: {total}</li>
      <li>Filled: {filled}</li>
      <li>Rejected: {rejected}</li>
      <li>Cancelled: {cancelled}</li>
    </ul>

    <h3>Top 5 Rejection Reasons</h3>
    <ol>
      {rejection_list}
    </ol>

    <h3>Trade Summary</h3>
    <ul>
      <li>Total Trades: {trades}</li>
      <li>Notional: ${notional:.2f}</li>
      <li>Fees: ${fees:.4f}</li>
    </ul>
    """

def send_email(body):
    smtp_host = "smtp.gmail.com:587"
    smtp_user = read_secret('/run/secrets/smtp_user')
    smtp_pass = read_secret('/run/secrets/smtp_password')
    from_addr = read_secret('/run/secrets/smtp_from')
    to_addr = read_secret('/run/secrets/alert_email_to')

    msg = MIMEText(body, 'html')
    msg['Subject'] = f"CDB Daily Orders Summary - {datetime.now(timezone.utc).date()}"
    msg['From'] = f"CDB Reports <{from_addr}>"
    msg['To'] = to_addr

    with smtplib.SMTP(smtp_host) as smtp:
        smtp.starttls()
        smtp.login(smtp_user, smtp_pass)
        smtp.send_message(msg)

def wait_until_next_8am_utc():
    now = datetime.now(timezone.utc)
    target = now.replace(hour=8, minute=0, second=0, microsecond=0)
    if now >= target:
        target += timedelta(days=1)
    sleep_seconds = (target - now).total_seconds()
    time.sleep(sleep_seconds)

# Main loop
while True:
    wait_until_next_8am_utc()
    try:
        conn = get_db_connection()
        data = fetch_summary(conn)
        body = format_email_body(data)
        send_email(body)
        print(f"[{datetime.now(timezone.utc)}] Summary sent successfully")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()
```

**Dockerfile:**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY daily_orders_summary.py .
CMD ["python", "daily_orders_summary.py"]
```

**requirements.txt:**
```
psycopg2-binary==2.9.9
```

**Compose Integration:**
```yaml
# infrastructure/compose/reports.yml
services:
  cdb_reports:
    build:
      context: ../../services/reports
    container_name: cdb_reports
    restart: unless-stopped
    secrets:
      - postgres_password_dsn
      - smtp_user
      - smtp_password
      - smtp_from
      - alert_email_to
    environment:
      TZ: UTC
    networks:
      - cdb_network
    depends_on:
      - cdb_postgres

secrets:
  postgres_password_dsn:
    file: ${SECRETS_PATH}/POSTGRES_PASSWORD_DSN
```

---

### Option 2: Grafana Scheduled Report

**Pros:**
- No new service deployment
- Uses existing Grafana SMTP config
- UI-based setup (no code)

**Cons:**
- Report is PDF/CSV (dashboard screenshot)
- No custom HTML formatting
- Manual UI configuration (not git-tracked)
- Limited to dashboard panel layout

**Setup Steps:**
1. Create new Dashboard: "Orders Daily Summary"
2. Add Panel with Postgres data source
3. Query: Same SQL as above (aggregated view)
4. Visualization: Table or Stat panels
5. Reporting → New scheduled report:
   - Name: "Daily Orders Summary"
   - Dashboard: Orders Daily Summary
   - Schedule: Daily at 08:00 UTC
   - Recipients: (from alert_email_to secret)
   - Format: PDF or CSV
6. Save

**Limitation:** Report shows dashboard screenshot, not custom-formatted email body

---

## Recommendation

**Use Option 1 (Python Cron Service)** because:
- Full control over email formatting (HTML/Markdown)
- Can include complex aggregations (top rejections, trends)
- Git-tracked and reproducible
- Easy to extend (add charts, alerts, exports)
- Minimal resource footprint (~50MB RAM)

**Defer Option 2** unless:
- No-code requirement (business stakeholder needs to modify)
- Dashboard already exists and suitable

---

## Deployment Checklist

### Prerequisites
- ✅ Daily Digest alerting working (Phase 2 complete)
- ✅ SMTP secrets tested and verified
- ✅ Postgres accessible from new service

### New Files Needed
- [ ] `services/reports/daily_orders_summary.py`
- [ ] `services/reports/Dockerfile`
- [ ] `services/reports/requirements.txt`
- [ ] `infrastructure/compose/reports.yml`
- [ ] `docs/operations/ORDERS_SUMMARY.md` (usage guide)

### Secrets Required (already exist)
- ✅ `postgres_password_dsn` (or construct from postgres_password)
- ✅ `smtp_user`
- ✅ `smtp_password`
- ✅ `smtp_from`
- ✅ `alert_email_to`

### Testing Plan
1. Build image: `docker compose -f infrastructure/compose/reports.yml build`
2. Start service: `docker compose -f infrastructure/compose/reports.yml up -d`
3. Check logs: `docker logs cdb_reports -f`
4. Manual trigger (for testing):
   ```bash
   docker exec cdb_reports python -c "
   from daily_orders_summary import *
   conn = get_db_connection()
   data = fetch_summary(conn)
   print(format_email_body(data))
   "
   ```
5. Wait for scheduled run (08:00 UTC next day)
6. Verify email received

---

## Alternative Triggers

### Environment Variable Schedule
```python
# Instead of hardcoded 08:00:
SCHEDULE = os.getenv('REPORT_SCHEDULE', '08:00')  # HH:MM format
```

### Multiple Reports
```python
# Extend to weekly/monthly:
DAILY_SCHEDULE = '08:00'
WEEKLY_SCHEDULE = 'MON-08:00'
MONTHLY_SCHEDULE = '01-08:00'  # 1st of month
```

### On-Demand via API
```python
# Add Flask endpoint:
@app.route('/trigger-summary')
def trigger():
    send_summary()
    return {"status": "sent"}
```

---

## Email Template Example

```html
<!DOCTYPE html>
<html>
<head>
  <style>
    body { font-family: Arial, sans-serif; }
    .summary { background: #f5f5f5; padding: 20px; }
    .metric { display: inline-block; margin: 10px; }
    .metric-value { font-size: 24px; font-weight: bold; color: #2196F3; }
    .metric-label { font-size: 12px; color: #666; }
    table { border-collapse: collapse; width: 100%; }
    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
    th { background-color: #4CAF50; color: white; }
  </style>
</head>
<body>
  <h1>CDB Daily Orders Summary</h1>
  <p><strong>Period:</strong> 2026-01-16 08:00 UTC - 2026-01-17 08:00 UTC</p>

  <div class="summary">
    <div class="metric">
      <div class="metric-value">142</div>
      <div class="metric-label">Total Orders</div>
    </div>
    <div class="metric">
      <div class="metric-value">127</div>
      <div class="metric-label">Filled</div>
    </div>
    <div class="metric">
      <div class="metric-value">12</div>
      <div class="metric-label">Rejected</div>
    </div>
    <div class="metric">
      <div class="metric-value">3</div>
      <div class="metric-label">Cancelled</div>
    </div>
  </div>

  <h3>Top Rejection Reasons</h3>
  <table>
    <tr>
      <th>Reason</th>
      <th>Count</th>
    </tr>
    <tr>
      <td>Insufficient balance</td>
      <td>5</td>
    </tr>
    <tr>
      <td>Position limit exceeded</td>
      <td>4</td>
    </tr>
    <tr>
      <td>Circuit breaker active</td>
      <td>2</td>
    </tr>
    <tr>
      <td>Invalid symbol</td>
      <td>1</td>
    </tr>
  </table>

  <h3>Trade Execution</h3>
  <ul>
    <li><strong>Total Trades:</strong> 127</li>
    <li><strong>Total Notional:</strong> $8,542.37</li>
    <li><strong>Total Fees:</strong> $4.27</li>
    <li><strong>Avg Fill Rate:</strong> 89.4%</li>
  </ul>

  <hr>
  <p style="font-size: 10px; color: #999;">
    Generated by CDB Reports Service |
    <a href="http://localhost:3000">Grafana Dashboard</a>
  </p>
</body>
</html>
```

---

## Monitoring

### Key Metrics to Track
- Report send success rate (log parsing)
- Email delivery confirmation (SMTP logs)
- Query execution time (Postgres slow query log)
- Container uptime (should be 100%)

### Alerting
```yaml
# Add Prometheus alert:
- alert: OrdersSummaryNotSent
  expr: time() - cdb_reports_last_send_timestamp > 86400 * 1.5
  labels:
    severity: warning
  annotations:
    summary: "Daily orders summary not sent in 36h"
```

---

**Status:** Design complete, ready for implementation when needed
**Next Step:** Implement after UI-only digest fix is verified (24h test period)
