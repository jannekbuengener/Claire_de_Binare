# Live Trading Runbook

**CRITICAL:** Diese Checkliste MUSS vollständig abgearbeitet werden, bevor `MOCK_TRADING="false"` gesetzt wird.

## Status: 🔴 NOT READY FOR LIVE

---

## Pre-Flight Checklist

### 1. Secrets & Credentials ✅
- [x] MEXC API Key vorhanden (`/run/secrets/mexc_api_key`)
- [x] MEXC API Secret vorhanden (`/run/secrets/mexc_api_secret`)
- [ ] **TODO:** MEXC API Keys auf Testnet verifiziert (separate Test-Order)
- [ ] **TODO:** MEXC API Keys auf Mainnet verifiziert (separate Test-Order)
- [ ] **TODO:** API Key Permissions überprüft (nur Spot Trading, kein Withdrawal)

### 2. Risk Configuration ⚠️
- [x] Early-Live max allocation: 0.02 (2%)
- [x] `USE_REAL_BALANCE="false"` in dev.yml (Paper Mode)
- [ ] **TODO:** `USE_REAL_BALANCE="true"` NUR für Live-Deployment vorbereiten
- [ ] **TODO:** MEXC Account Balance > $100 USDT (Minimum für Live)
- [ ] **TODO:** Risk-Limits korrekt konfiguriert:
  - `MAX_POSITION_PCT`: 0.10 (10% max pro Position)
  - `MAX_TOTAL_EXPOSURE_PCT`: 0.30 (30% max total)
  - `MAX_DAILY_DRAWDOWN_PCT`: 0.05 (5% Circuit Breaker)

### 3. Kill-Switch Mechanisms ✅
- [x] Allocation kann via `ALLOCATION_RULES_JSON` auf 0 gesetzt werden
- [x] Risk blockiert bei `allocation_pct == 0`
- [x] Bot-Shutdown Stream funktioniert (`stream.bot_shutdown`)
- [ ] **TODO:** Manual Kill-Switch tested (via Redis XADD)
- [ ] **TODO:** Emergency Runbook erstellt (wie stoppe ich ALLES sofort?)

### 4. Monitoring & Observability 🔴
- [ ] **TODO:** Grafana Dashboards für Live Trading
  - Orders per minute
  - Fill Rate
  - P&L tracking
  - Circuit Breaker status
- [ ] **TODO:** Alerting konfiguriert:
  - Circuit Breaker triggered
  - Unusual order volume
  - MEXC API errors
  - Balance drops > 5%
- [ ] **TODO:** Log-Aggregation für Execution Service (structured logs)

### 5. Pipeline Stability ⚠️
- [x] Candles-Service läuft stabil (48h+)
- [x] Regime-Service erkennt korrekt HIGH_VOL_CHAOTIC
- [x] Allocation-Service bootstrapped korrekt nach Restart
- [x] Risk-Service Early-Live Exception funktioniert
- [ ] **TODO:** 48h Observation Window OHNE Crashes
- [ ] **TODO:** 100+ Orders im Paper Mode erfolgreich processed

### 6. Execution Service Readiness 🔴
- [x] `MOCK_TRADING="true"` explizit gesetzt (Paper Mode)
- [ ] **TODO:** LiveExecutor Code-Review abgeschlossen
- [ ] **TODO:** MEXC API Rate Limits verstanden (600 req/min)
- [ ] **TODO:** Order Retry Logic tested
- [ ] **TODO:** Partial Fill Handling tested
- [ ] **TODO:** Network Timeout Handling tested

### 7. Compliance & Documentation 🔴
- [ ] **TODO:** Trading Strategy dokumentiert (warum traden wir?)
- [ ] **TODO:** Risk Management Policy dokumentiert
- [ ] **TODO:** Incident Response Plan dokumentiert
- [ ] **TODO:** Rollback Plan dokumentiert (wie zurück zu Paper?)
- [ ] **TODO:** Legal/Tax Implications geklärt (je nach Jurisdiction)

---

## Live-Switch Procedure (NICHT JETZT AUSFÜHREN!)

**Wann:** Erst wenn ALLE Checkboxen oben ✅ sind.

### Step 1: Backup
```bash
# Backup current config
cp infrastructure/compose/dev.yml infrastructure/compose/dev.yml.backup.$(date +%Y%m%d_%H%M%S)

# Backup Redis streams (snapshot)
docker exec cdb_redis sh -c 'redis-cli -a $(cat /run/secrets/redis_password) SAVE'
```

### Step 2: Config Change
```yaml
# infrastructure/compose/dev.yml
cdb_execution:
  environment:
    MOCK_TRADING: "false"         # ⚠️ LIVE MODE
    USE_REAL_BALANCE: "true"      # ⚠️ REAL BALANCE
```

### Step 3: Deployment
```bash
cd infrastructure/compose
$env:SECRETS_PATH="C:\Users\janne\Documents\.secrets\.cdb"
docker compose -f base.yml -f dev.yml up -d --build cdb_execution
```

### Step 4: Verification (CRITICAL)
```bash
# 1. Check execution mode
docker logs cdb_execution --tail 50 | grep "Mode:"
# Expected: "Mode: LIVE"

# 2. Check LiveExecutor loaded
docker logs cdb_execution --tail 50 | grep "LiveExecutor"
# Expected: "Using LiveExecutor"

# 3. Monitor first order (should be SMALL)
docker logs cdb_execution --follow
```

### Step 5: Post-Deployment Monitoring (First 24h)
- [ ] Check MEXC account balance every 1h
- [ ] Monitor stream.orders for unexpected volume
- [ ] Monitor Execution logs for API errors
- [ ] Monitor Risk logs for unusual blocks
- [ ] Verify P&L tracking accuracy

---

## Rollback Procedure (Emergency)

**Wenn irgendetwas schief geht:**

```bash
# 1. STOP execution immediately
docker stop cdb_execution

# 2. Cancel all open MEXC orders (manual via MEXC UI or API)

# 3. Restore Paper Mode
git checkout infrastructure/compose/dev.yml
docker compose -f base.yml -f dev.yml up -d --build cdb_execution

# 4. Verify rollback
docker logs cdb_execution --tail 50 | grep "Mode:"
# Expected: "Mode: MOCK"
```

---

## Current Status: NOT READY

**Blocking Issues:**
1. Monitoring/Alerting nicht konfiguriert
2. 48h Stability Window nicht erfüllt
3. LiveExecutor nicht getestet
4. Emergency Procedures nicht dokumentiert
5. MEXC Testnet Verification ausstehend

**Estimated Time to Live:** 5-7 Tage (nach vollständiger Checklist-Abarbeitung)

**Owner:** TBD
**Last Updated:** 2026-01-10
