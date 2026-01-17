# Email Alerting Evidence - Gmail SMTP Configuration

**Date:** 2026-01-16
**PR:** #607
**Status:** ✅ Configured, awaiting live email delivery test

---

## Configuration Summary

### SMTP Settings (Grafana Environment)
```
GF_SMTP_ENABLED=true
GF_SMTP_HOST=smtp.gmail.com:587
GF_SMTP_USER=jannekbungener@gmail.com
GF_SMTP_PASSWORD=********* (16-char Google App Password)
GF_SMTP_FROM_ADDRESS=jannekbungener@gmail.com
GF_SMTP_FROM_NAME=CDB Alerts
GF_SMTP_STARTTLS_POLICY=MandatoryStartTLS
```

### Docker Secrets Mounted
```bash
$ docker inspect cdb_grafana --format '{{range .Mounts}}{{if eq .Type "bind"}}{{.Source}} -> {{.Destination}}{{println}}{{end}}{{end}}' | grep secret
C:/Users/janne/Documents/.secrets/.cdb/SMTP_FROM -> /run/secrets/smtp_from
C:/Users/janne/Documents/.secrets/.cdb/ALERT_EMAIL_TO -> /run/secrets/alert_email_to
C:/Users/janne/Documents/.secrets/.cdb/GRAFANA_PASSWORD -> /run/secrets/grafana_password
C:/Users/janne/Documents/.secrets/.cdb/SMTP_USER -> /run/secrets/smtp_user
C:/Users/janne/Documents/.secrets/.cdb/SMTP_PASSWORD -> /run/secrets/smtp_password
```

### Contact Point Created
```json
{
  "uid": "dfabzv9fdgmpse",
  "name": "email-main",
  "type": "email",
  "settings": {
    "addresses": "info.traumtaenzer@gmail.com",
    "singleEmail": true
  },
  "disableResolveMessage": false,
  "provenance": "api"
}
```

### Notification Policy
```json
{
  "receiver": "email-main",
  "group_by": ["grafana_folder", "alertname"]
}
```

---

## Alert Rules Created

### 1. CDB - High Error Rate (>5%)
- **UID:** cdb_error_rate_high
- **Severity:** Warning
- **Condition:** `(rate(execution_orders_rejected_total[5m]) / rate(execution_orders_received_total[5m])) * 100 > 5`
- **Evaluation:** 5 minutes
- **Description:** Order rejection rate is above 5% for the last 5 minutes

### 2. CDB - Orders Rejected
- **UID:** cdb_orders_rejected
- **Severity:** Info
- **Condition:** `increase(execution_orders_rejected_total[5m]) > 0`
- **Evaluation:** 5 minutes
- **Description:** One or more orders were rejected in the last 5 minutes

### 3. CDB - Circuit Breaker Activated
- **UID:** cdb_circuit_breaker_active
- **Severity:** Critical
- **Condition:** `circuit_breaker_active == 1`
- **Evaluation:** Immediate (0s)
- **Description:** Circuit breaker has been activated - trading is halted

---

## Grafana Logs Evidence

### SMTP Configuration Loaded
```
logger=settings t=2026-01-16T10:10:39.588297063Z level=info msg="Config overridden from Environment variable" var="GF_SMTP_HOST=smtp.gmail.com:587"
logger=settings t=2026-01-16T10:10:39.588300524Z level=info msg="Config overridden from Environment variable" var="GF_SMTP_USER=jannekbungener@gmail.com"
logger=settings t=2026-01-16T10:10:39.588304184Z level=info msg="Config overridden from Environment variable" var="GF_SMTP_PASSWORD=*********"
logger=settings t=2026-01-16T10:10:39.588308494Z level=info msg="Config overridden from Environment variable" var="GF_SMTP_FROM_ADDRESS=jannekbungener@gmail.com"
logger=settings t=2026-01-16T10:10:39.588312724Z level=info msg="Config overridden from Environment variable" var="GF_SMTP_FROM_NAME=CDB Alerts"
logger=settings t=2026-01-16T10:10:39.588317084Z level=info msg="Config overridden from Environment variable" var="GF_SMTP_STARTTLS_POLICY=MandatoryStartTLS"
```

### Secrets Read from Files
```
Getting secret GF_SMTP_USER from /run/secrets/smtp_user
Getting secret GF_SMTP_PASSWORD from /run/secrets/smtp_password
Getting secret GF_SMTP_FROM_ADDRESS from /run/secrets/smtp_from
```

### Alerts Firing to Local Notifier
```
logger=ngalert.sender.router rule_uid=cdb_circuit_breaker_active org_id=1 t=2026-01-16T10:14:20.007897839Z level=info msg="Sending alerts to local notifier" count=1
logger=ngalert.sender.router rule_uid=cdb_error_rate_high org_id=1 t=2026-01-16T10:14:23.341702343Z level=info msg="Sending alerts to local notifier" count=1
logger=ngalert.sender.router rule_uid=cdb_orders_rejected org_id=1 t=2026-01-16T10:14:26.675160065Z level=info msg="Sending alerts to local notifier" count=1
```

---

## Security Verification

### No Plaintext Secrets in Environment
```bash
$ docker inspect cdb_grafana | grep -i password
# Returns only __FILE references, not plaintext passwords
"GF_SECURITY_ADMIN_PASSWORD__FILE=/run/secrets/grafana_password"
"GF_SMTP_PASSWORD__FILE=/run/secrets/smtp_password"
```

### Secrets Not in Git
```bash
$ git status
# Shows only infrastructure/compose/base.yml modified
# No .secrets/ or password files tracked
modified:   infrastructure/compose/base.yml
```

---

## Testing Status

| Test | Status | Evidence |
|------|--------|----------|
| SMTP config loaded | ✅ Pass | See Grafana logs above |
| Secrets mounted | ✅ Pass | 5 secrets in /run/secrets/ |
| Contact point created | ✅ Pass | UID: dfabzv9fdgmpse |
| Notification policy updated | ✅ Pass | Receiver: email-main |
| Alert rules created | ✅ Pass | 3 rules active |
| Alerts firing to notifier | ✅ Pass | See router logs |
| **Email delivery** | ⏳ **Pending** | Requires live SMTP test |

---

## Next Steps for Email Delivery Test

1. **Trigger Test Alert:**
   ```bash
   # Temporarily set threshold to always trigger
   curl -X PUT http://localhost:3000/api/v1/provisioning/alert-rules/cdb_orders_rejected \
     -u "admin:PASSWORD" \
     -H "Content-Type: application/json" \
     -d '{"condition": "C", "data": [...], "noDataState": "Alerting", ...}'
   ```

2. **Wait 1-2 minutes** for alert to fire and email to send

3. **Check Gmail:**
   - **Inbox:** info.traumtaenzer@gmail.com
   - **Sent:** jannekbungener@gmail.com

4. **Verify Email Contents:**
   - Subject: `[FIRING:1] CDB - Orders Rejected`
   - From: CDB Alerts <jannekbungener@gmail.com>
   - Body includes: alert details, timestamp, summary

5. **Reset Alert Rule** to production threshold (> 0 instead of always-fire)

---

## Troubleshooting

### If Email Not Received

1. **Check Grafana logs for SMTP errors:**
   ```bash
   docker logs cdb_grafana 2>&1 | grep -iE "smtp|mail|send|tls|error"
   ```

2. **Verify Gmail App Password:**
   - Must be 16-character password (no spaces)
   - Generated from Google Account → Security → 2-Step Verification → App Passwords

3. **Test SMTP manually:**
   ```bash
   docker exec -it cdb_grafana sh
   telnet smtp.gmail.com 587
   # If connection fails, check firewall/network
   ```

4. **Check Gmail settings:**
   - Less secure app access: Not needed for App Passwords
   - 2-Step Verification: Must be enabled

---

**Report Generated:** 2026-01-16 11:20:00 UTC
**Next Review:** After live email delivery test
