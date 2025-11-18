# Grafana Dashboard Guide – Claire de Binare Monitoring

**Version**: 1.1.0  
**Status**: ✅ Live für Phase 7 (7-Tage Paper Trading)  
**Dashboard**: `CLAIRE_DE_BINARE_DASHBOARD.json`  
**Zugriff**: http://localhost:3000 (admin / REDACTED_REDIS_PW$$)

---

## 📋 Executive Summary

Das Grafana Dashboard ist das **zentrale Monitoring-Interface** für alle Services während des 7-Tage Paper Trading Tests. Es visualisiert Real-Time Metriken, Alerts und Performance-Indikatoren.

**Kritische Panels**:
- ✅ **Order Flow** (Signal → Risk Check → Execution → Result)
- ✅ **Risk State** (Exposure, P&L, Circuit Breaker Status)
- ✅ **Service Health** (Uptime, CPU, Memory, Redis Connections)
- ✅ **Anomalien** (Slippage >1%, Latency >5s, Error Rate >5%)

**Dashboard-Zugriff**:
```bash
# Lokal
http://localhost:3000

# Credentials
Username: admin
Password: REDACTED_REDIS_PW$$

# Dashboard ID: claire_de_binare_overview
```

---

## 🏗️ Dashboard-Struktur (Top → Bottom)

### Row 1: System Overview (4 Panels)

| Panel | Metric | Threshold | Bedeutung |
|-------|--------|-----------|-----------|
| **Total Signals** | `rate(signals_received_total[1m])` | >0/min | Signal Engine aktiv? |
| **Orders Placed** | `rate(orders_placed_total[1m])` | >0/min | Execution Service funktioniert? |
| **Circuit Breaker** | `risk_circuit_breaker_active` | 0 = OK, 1 = AKTIV | Trading pausiert? |
| **Total Exposure** | `risk_total_exposure_usd` | <5000 USD | Kapitalschutz intakt? |

**Interpretation**:
```
✅ Normal:
- Signals: 5-10/min
- Orders: 2-5/min (60-80% Rejection normal)
- Circuit Breaker: 0 (inaktiv)
- Exposure: 2000-4000 USD (20-40% vom Balance)

⚠️ Anomalie:
- Signals: 0/min → WebSocket-Verbindung unterbrochen
- Orders: 0/min trotz Signals → Risk Manager blockiert
- Circuit Breaker: 1 → Daily Loss ≥ -500 USD
- Exposure: >4800 USD → Nahe am Limit (5000 USD)

🚨 Kritisch:
- Signals: >50/min → Flash-Crash oder Bug im Signal Engine
- Circuit Breaker: 1 für >2h → Manuelles Eingreifen nötig
- Exposure: >5000 USD → FEHLER (sollte nie passieren!)
```

---

### Row 2: Order Flow (3 Panels)

#### Panel: **Signal Quality**

**Query**:
```promql
# Durchschnittliche Confidence
avg(signal_confidence)

# Verteilung (Histogram)
histogram_quantile(0.5, signal_confidence_bucket)  # Median
histogram_quantile(0.95, signal_confidence_bucket) # P95
```

**Interpretation**:
```
✅ Normal:
- Avg Confidence: 0.7-0.85 (70-85%)
- Median: 0.75
- P95: 0.92

⚠️ Anomalie:
- Avg Confidence: <0.5 → Schwache Signale (mehr Rejections)
- P95 > 0.95 → Sehr aggressive Signale (Risk Manager sollte filtern)

🚨 Kritisch:
- Avg Confidence: <0.3 → Signal Engine Bug oder Markt extrem volatil
```

---

#### Panel: **Risk Check Success Rate**

**Query**:
```promql
sum(rate(risk_checks_passed_total[5m])) 
/ 
sum(rate(risk_checks_total[5m])) * 100
```

**Interpretation**:
```
✅ Normal:
- Success Rate: 20-40% (60-80% Rejection ist OK!)

⚠️ Anomalie:
- Success Rate: <10% → Zu strenge Limits oder Markt ungeeignet
- Success Rate: >80% → Zu lockere Limits (GEFAHR!)

🚨 Kritisch:
- Success Rate: 0% → Risk Manager down oder Bug
- Success Rate: 100% → Risk Checks deaktiviert (KRITISCH!)
```

---

#### Panel: **Order Execution Status**

**Query**:
```promql
sum by (status) (rate(orders_placed_total[5m]))
```

**Interpretation**:
```
✅ Normal:
- FILLED: 95-100%
- REJECTED: 0-5% (Balance, Timestamp, etc.)
- PARTIAL: 0% (MARKET Orders sollten immer voll gefüllt werden)

⚠️ Anomalie:
- FILLED: <90% → MEXC API Probleme oder Slippage hoch
- REJECTED: >10% → Balance zu niedrig oder API Errors

🚨 Kritisch:
- FILLED: 0% → Execution Service down oder API Credentials falsch
- REJECTED: 100% → MEXC Account Problem (Suspension?)
```

---

### Row 3: Risk State (4 Panels)

#### Panel: **Daily P&L**

**Query**:
```promql
risk_daily_pnl_usd
```

**Interpretation**:
```
✅ Normal:
- P&L: -200 bis +500 USD pro Tag
- Trend: Leicht positiv oder neutral

⚠️ Anomalie:
- P&L: <-400 USD → Nahe Circuit Breaker (-500 USD)
- P&L: >+1000 USD → Ungewöhnlich hoch (prüfen ob realistisch)

🚨 Kritisch:
- P&L: <-500 USD → Circuit Breaker MUSS aktiv sein
- P&L: 0.0 für >6h → Bug im P&L Tracking (Bug #4 nicht gefixt?)
```

---

#### Panel: **Exposure vs Limit**

**Query**:
```promql
risk_total_exposure_usd
/ 
(risk_test_balance * 0.50) * 100
```

**Interpretation**:
```
✅ Normal:
- Exposure: 30-70% vom Limit (1500-3500 USD)

⚠️ Anomalie:
- Exposure: >90% (>4500 USD) → Fast am Limit, neue Orders werden rejected

🚨 Kritisch:
- Exposure: >100% (>5000 USD) → FEHLER! Risk Manager Bug (Bug #3 nicht gefixt?)
```

---

#### Panel: **Open Positions Count**

**Query**:
```promql
risk_open_positions_count
```

**Interpretation**:
```
✅ Normal:
- Count: 3-7 Positionen (diversifiziert)

⚠️ Anomalie:
- Count: >10 → Zu viele kleine Positionen (Fees hoch)
- Count: 1 → Sehr undiversifiziert (Risiko!)

🚨 Kritisch:
- Count: 0 für >2h → Keine Trades (Signal Engine down?)
- Count: >20 → Bug oder Flash-Crash Response
```

---

#### Panel: **Circuit Breaker Timeline**

**Query**:
```promql
changes(risk_circuit_breaker_active[1d])
```

**Interpretation**:
```
✅ Normal:
- Aktivierungen: 0-1 pro Tag

⚠️ Anomalie:
- Aktivierungen: 2-3 → Sehr volatiler Tag oder Strategie zu aggressiv

🚨 Kritisch:
- Aktivierungen: >5 → Circuit Breaker Reset Bug (Bug #5 nicht gefixt?)
- Dauerhaft aktiv >4h → Manuelles Reset nötig
```

---

### Row 4: Service Health (5 Panels)

#### Panel: **Service Uptime**

**Query**:
```promql
up{job="claire_services"}
```

**Interpretation**:
```
✅ Normal:
- All Services: 1 (up)

🚨 Kritisch:
- Any Service: 0 (down)
  → Check Docker: docker ps
  → Check Logs: docker logs <service_name>
```

---

#### Panel: **CPU Usage**

**Query**:
```promql
rate(process_cpu_seconds_total[1m]) * 100
```

**Interpretation**:
```
✅ Normal:
- Signal Engine: 5-15% (WebSocket aktiv)
- Risk Manager: 1-5% (nur bei Order-Validierung aktiv)
- Execution Service: <1% (Test Mode idle)

⚠️ Anomalie:
- Any Service: >50% → Performance-Problem oder Bug

🚨 Kritisch:
- Any Service: >80% für >5min → OOM-Kill Risk (Check Memory)
```

---

#### Panel: **Memory Usage**

**Query**:
```promql
process_resident_memory_bytes / (1024^2)  # MB
```

**Interpretation**:
```
✅ Normal:
- Signal Engine: 100-200 MB
- Risk Manager: 50-100 MB
- Execution Service: 50-80 MB

⚠️ Anomalie:
- Steigend über Zeit → Memory Leak (Check Code)

🚨 Kritisch:
- >500 MB → Sofortiges Eingreifen (Restart + Debug)
```

---

#### Panel: **Redis Connections**

**Query**:
```promql
redis_connected_clients
```

**Interpretation**:
```
✅ Normal:
- Connections: 3 (1 pro Service)

⚠️ Anomalie:
- Connections: >10 → Connection Leak (Services nicht properl closed)

🚨 Kritisch:
- Connections: 0 → Redis down (docker restart redis)
```

---

#### Panel: **HTTP Response Time (P95)**

**Query**:
```promql
histogram_quantile(0.95, 
  rate(http_request_duration_seconds_bucket[5m])
)
```

**Interpretation**:
```
✅ Normal:
- /health: <100ms
- /status: <200ms
- /metrics: <500ms (größeres Payload)

⚠️ Anomalie:
- Any Endpoint: >1s → Datenbank Slow-Query oder CPU-Load

🚨 Kritisch:
- Any Endpoint: >5s → Service fast unresponsive (Check Logs)
```

---

### Row 5: Anomalien & Alerts (3 Panels)

#### Panel: **Slippage Distribution**

**Query**:
```promql
(execution_executed_price - signal_price) / signal_price * 100
```

**Interpretation**:
```
✅ Normal:
- Avg Slippage: 0.05-0.2% (MARKET Order Standard)
- P95: <0.5%

⚠️ Anomalie:
- Avg Slippage: >0.5% → Liquidität gering oder Flash-Crash

🚨 Kritisch:
- Slippage: >2% → MEXC API Problem oder Markt extrem volatil
```

---

#### Panel: **API Error Rate**

**Query**:
```promql
sum(rate(api_errors_total[5m])) by (error_code)
```

**Interpretation**:
```
✅ Normal:
- Error Rate: <1/min (vereinzelte Timeouts OK)

⚠️ Anomalie:
- -1003 (Rate Limit): >5/min → Rate Limiter nicht aktiv?
- -1021 (Timestamp): >0 → Server Time Sync fehlt

🚨 Kritisch:
- -2010 (Balance): >0 → Balance zu niedrig (Phase 7 sollte 10k USD haben!)
- -1002 (Auth): >0 → API Credentials falsch
```

---

#### Panel: **Data Silence Detection**

**Query**:
```promql
time() - max(signal_last_received_timestamp) > 30
```

**Interpretation**:
```
✅ Normal:
- Silence: <10s (ständig neue Market Data)

⚠️ Anomalie:
- Silence: 30-60s → WebSocket Reconnect oder Exchange Downtime

🚨 Kritisch:
- Silence: >2min → Signal Engine down (docker restart signal_engine)
```

---

## 🎯 Realistische Monitoring-Szenarien

### Szenario 1: Flash Crash (-10% in 5min)

**Erwartete Dashboard-Änderungen**:
```
1. Signal Quality:
   - Avg Confidence: 0.85 → 0.65 (unsichere Signale)
   - Signal Rate: 10/min → 30/min (mehr Chancen)

2. Risk Check Success Rate:
   - 30% → 10% (mehr Rejections wegen Volatility)

3. Daily P&L:
   - 0 USD → -450 USD (offene Positionen verlieren)

4. Circuit Breaker:
   - 0 → 1 (aktiviert bei -500 USD)

5. Orders Placed:
   - 5/min → 0/min (Trading pausiert)
```

**Action**:
```bash
# 1. Bestätige Circuit Breaker
curl http://localhost:8002/status | jq '.circuit_breaker_active'
# Expected: true

# 2. Warte bis Mitternacht UTC (Auto-Reset)
# Oder manuelles Reset (nur für Tests!):
curl -X POST http://localhost:8002/admin/reset_circuit_breaker
```

---

### Szenario 2: MEXC API Outage (5min)

**Erwartete Dashboard-Änderungen**:
```
1. Order Execution Status:
   - FILLED: 100% → 0%
   - REJECTED: 0% → 100% (alle Orders fehlschlagen)

2. API Error Rate:
   - -1000 (Server Error): 0/min → 20/min

3. Execution Time:
   - P95: 0.5s → 10s (Timeouts + Retries)

4. Service Health:
   - Execution Service: up (Service läuft, aber API down)
```

**Action**:
```bash
# 1. Check MEXC Status
curl https://www.mexc.com/api/platform/status

# 2. Wait for Recovery (Retries automatisch)
# Dashboard zeigt "FILLED" sobald API wieder erreichbar

# 3. Check für verlorene Orders (sollte nicht passieren!)
docker logs execution_service | grep "Order failed after"
```

---

### Szenario 3: Memory Leak (6h)

**Erwartete Dashboard-Änderungen**:
```
1. Memory Usage:
   - Signal Engine: 150 MB → 450 MB (stetig steigend)

2. CPU Usage:
   - Signal Engine: 10% → 25% (GC häufiger)

3. HTTP Response Time:
   - /health: 50ms → 300ms (GC Pauses)
```

**Action**:
```bash
# 1. Bestätige Memory Leak
docker stats signal_engine
# MEM USAGE steigt konstant

# 2. Restart Service
docker restart signal_engine

# 3. Debug (nach Restart)
docker logs signal_engine | grep "Memory"
# Suche nach großen Listen/Caches die nie clearen
```

---

## 🛠️ Dashboard Export/Import

### Export Current Dashboard

```bash
# 1. In Grafana UI:
Dashboard → Share → Export → Save to file

# 2. Via API:
curl -H "Authorization: Bearer <API_KEY>" \
     http://localhost:3000/api/dashboards/db/claire-de-binare-overview \
     > dashboard_backup.json
```

---

### Import Dashboard

```bash
# 1. In Grafana UI:
Dashboards → Import → Upload JSON file

# 2. Via API:
curl -X POST \
     -H "Authorization: Bearer <API_KEY>" \
     -H "Content-Type: application/json" \
     -d @CLAIRE_DE_BINARE_DASHBOARD.json \
     http://localhost:3000/api/dashboards/db
```

---

## 📝 Täglicher Check (Phase 7)

### Morgens (9:00 UTC):

```
1. ✅ Circuit Breaker Status
   → Check: risk_circuit_breaker_active = 0

2. ✅ Daily P&L Reset
   → Check: risk_daily_pnl_usd = 0 (nach Mitternacht)

3. ✅ Service Health
   → All Services: up = 1

4. ✅ Signal Rate
   → Check: signals_received_total > 0/min
```

---

### Mittags (15:00 UTC – US Market Open):

```
1. ✅ Order Flow
   → Check: orders_placed_total > 0/min (Trading aktiv?)

2. ✅ Slippage
   → Check: Avg Slippage < 0.3% (höher bei Market Open OK)

3. ✅ Exposure
   → Check: total_exposure < 4500 USD (90% vom Limit)
```

---

### Abends (21:00 UTC):

```
1. ✅ Daily P&L
   → Check: -200 bis +500 USD (realistisch?)

2. ✅ CPU/Memory
   → Check: Keine kontinuierliche Steigerung (Memory Leak?)

3. ✅ Logs Review
   → docker logs risk_manager | grep "ERROR"
   → docker logs execution_service | grep "CRITICAL"
```

---

## 🎯 Erfolgskriterien für 7-Tage-Test

**Must-Have (Dashboard-basiert)**:
- ✅ Circuit Breaker aktiviert mindestens 1x korrekt
- ✅ Daily P&L korrekt tracked (nicht konstant 0.0)
- ✅ Exposure-Limit nie überschritten (max 5000 USD)
- ✅ Service Uptime >99.5% (max 1h Downtime in 7 Tagen)
- ✅ API Error Rate <2% (max 2 Fehler pro 100 Requests)

**Nice-to-Have**:
- [ ] Slippage Avg <0.2%
- [ ] HTTP P95 <500ms
- [ ] Memory stabil (<10% Wachstum über 7 Tage)

---

## 📝 Änderungsprotokoll

| Datum | Änderung | Autor |
|-------|----------|-------|
| 2025-10-30 | Initial Dashboard-Guide erstellt | Copilot |
| 2025-10-30 | Alle Panels mit Thresholds dokumentiert | Copilot |
| 2025-10-30 | 3 Realistische Szenarien hinzugefügt | Copilot |
| 2025-10-30 | Täglicher Check-Workflow dokumentiert | Copilot |

---

**Ende des Dokuments** | **Letzte Aktualisierung**: 2025-10-30 | **Status**: Live für Phase 7
