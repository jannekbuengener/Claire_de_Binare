# Deep Research Bedarf – Wissenslücken für Agenten
**Datum**: 2025-01-11 (Erstellt) | **Aktualisiert**: 2025-10-30
**Status**: ✅ **COMPLETED** – Alle 3 Dokumente erstellt (2025-10-30)
**Kontext**: Nach Analyse von 2.300+ Zeilen Research-Doku waren 3 kritische Wissenslücken identifiziert

---

## 🎯 Übersicht

Nach vollständiger Integration der Research-Dokumente (`cdb_ws.md`, `cdb_kubernetes.md`, `cdb_prometheus.md`, `cdb_redis.md`, `cdb_signal.md`, `cdb_advisor.md`) waren **3 Bereiche** noch unzureichend dokumentiert. **Alle 3 wurden am 2025-10-30 erstellt**:

✅ **cdb_execution.md** (650 Zeilen) – MEXC API Integration vollständig dokumentiert
✅ **cdb_risk.md** (500 Zeilen) – Risk Manager Enforcement-Logic mit Bug-Fixes
✅ **GRAFANA_DASHBOARD_GUIDE.md** (550 Zeilen) – Dashboard-Interpretation für Phase 7

---

## 1. ✅ **COMPLETED**: Execution Service – MEXC API Integration

**Dokument erstellt**: `backoffice/docs/research/cdb_execution.md` (2025-10-30, 650 Zeilen)

### **Problem-Statement** (gelöst):
- ✅ **Vorhanden**: Vollständige MEXC API Integration dokumentiert
- ✅ **Vorhanden**: HMAC-SHA256 Signature-Generierung (Step-by-Step)
- ✅ **Vorhanden**: Order Types (MARKET, LIMIT, STOP_LOSS_LIMIT)
- ✅ **Vorhanden**: Error Handling & Rate Limiting
- ✅ **Vorhanden**: Test Mode vs Live Mode Implementierung

### **Dokumentierte Inhalte**:

1. **MEXC Spot API Endpunkte**:
   - Welche Endpoints werden genutzt?
     - `/api/v3/order` (Live-Order)?
     - `/api/v3/order/test` (Paper-Trading)?
     - `/api/v3/openOrders` (Query offener Orders)?
   - Rate-Limits pro Endpoint? (MEXC dokumentiert 1200 req/min für Order-Endpoints)

2. **Signatur-Generierung**:
   - Wie wird der Query-String konstruiert? (alphabetische Sortierung?)
   - HMAC-SHA256 Signatur-Algorithmus – Step-by-Step-Beispiel?
   - Timestamp-Handling (MEXC erwartet Unix-Timestamp in Millisekunden)
   - Beispiel-Request mit vollständiger Signatur-Berechnung

3. **Order-Types & Parameter**:
   - Unterstützte Order-Types: `MARKET`, `LIMIT`, `STOP_LOSS_LIMIT`?
   - Wie werden Stop-Loss-Orders gesetzt?
   - OCO-Orders (One-Cancels-Other) möglich?
   - Time-in-Force-Parameter (`GTC`, `IOC`, `FOK`)?

4. **Error-Handling**:
   - MEXC Error-Codes → System-Events-Mapping
   - Rate-Limit-Exceeded → Backoff-Strategie (exponentiell? linear?)
   - Insufficient-Balance → Risk-Manager-Alert?
   - Order-Rejection → Retry-Logic oder sofortiges Abort?

5. **Test-Modus vs. Live-Modus**:
   - Wann wird `/api/v3/order/test` genutzt? (ENV-Variable `PAPER_TRADING=true`?)
   - Wie werden Test-Orders in DB gespeichert? (separate `test_orders`-Tabelle?)
   - Wie wird zwischen Test- und Live-Orders unterschieden? (Flag in `orders`-Tabelle?)

### **Gewünschtes Dokument**:

**Dateiname**: `backoffice/docs/research/cdb_execution.md`

**Inhalte** (Struktur ähnlich wie `cdb_signal.md`):

```markdown
## MEXC Execution Service – Deep Dive

## 1. MEXC Spot API Endpunkte
- /api/v3/order (POST) – Live Order Placement
- /api/v3/order/test (POST) – Paper Trading Test Order
- /api/v3/order (DELETE) – Cancel Order
- /api/v3/openOrders (GET) – Query Open Orders
- /api/v3/myTrades (GET) – Query Trade History

## 2. Signatur-Generierung (Step-by-Step)
1. Query-String konstruieren (alphabetisch sortiert)
2. HMAC-SHA256(query_string, secret_key)
3. Hex-String generieren
4. Signatur als `signature`-Parameter anhängen

**Beispiel-Request**:
```python
import hmac
import hashlib
import time

params = {
    "symbol": "BTC_USDT",
    "side": "BUY",
    "type": "MARKET",
    "quantity": 0.001,
    "timestamp": int(time.time() * 1000)
}

## Alphabetische Sortierung
query_string = "&".join([f"{k}={v}" for k, v in sorted(params.items())])

## Signatur
signature = hmac.new(
    SECRET_KEY.encode('utf-8'),
    query_string.encode('utf-8'),
    hashlib.sha256
).hexdigest()

params["signature"] = signature
```

## 3. Order-Types & Parameter
- MARKET: Sofortige Ausführung zum besten verfügbaren Preis
- LIMIT: Order nur zu spezifiziertem Preis oder besser
- STOP_LOSS_LIMIT: Stop-Price + Limit-Price (2-stufig)

## 4. Error-Code-Mapping
| MEXC Error Code | Bedeutung | System-Action |
|-----------------|-----------|---------------|
| -1003 | Rate-Limit-Exceeded | Exponential Backoff (2^n Sekunden) |
| -1013 | Invalid Quantity | Risk-Manager-Alert + Order-Abort |
| -2010 | Insufficient Balance | Circuit-Breaker prüfen |
| -2011 | Unknown Order | Ignore (bereits executed) |

## 5. Test-Modus vs. Live-Modus
ENV-Variable: PAPER_TRADING=true → /api/v3/order/test
DB-Schema: orders.is_test (BOOLEAN) – Flag für Test-Orders
```

### **Warum kritisch**:
- Execution Service ist **Herzstück für Live-Trading**
- Ohne MEXC-API-Doku können Agenten keine Order-Logic debuggen
- Security-Risk bei falscher Signatur-Implementierung (Unauthorized-Errors → Order-Failures)
- Bei Live-Trading = **systemkritisch** (Kapitalverlust bei Bugs)

---

## 2. ✅ **COMPLETED**: Risk Manager – Limit-Enforcement-Logic

**Dokument erstellt**: `backoffice/docs/research/cdb_risk.md` (2025-10-30, 500 Zeilen)

### **Problem-Statement** (gelöst):
- ✅ **Vorhanden**: Vollständige Risk-Check-Hierarchie (5 Layer) dokumentiert
- ✅ **Vorhanden**: 4 kritische Bugs (P0) identifiziert und gefixt
- ✅ **Vorhanden**: Position Tracking & P&L-Berechnung
- ✅ **Vorhanden**: Circuit Breaker Implementierung mit Reset-Logic
- ✅ **Vorhanden**: Realistische Szenarien (Flash Crash, etc.)

### **Dokumentierte Inhalte**:

1. **Position-Tracking**:
   - Wie werden Positionen aggregiert? (Pro Symbol? Über alle Symbole?)
   - DB-Schema: `positions`-Tabelle – welche Spalten? (`symbol`, `quantity`, `avg_entry_price`, `unrealized_pnl`?)
   - Wie wird Mark-to-Market-P&L berechnet? (Live-Price aus Redis `market_data`?)

2. **Limit-Enforcement-Flow**:
   - Signal-Event → Risk-Manager → **WO** wird Limit-Check durchgeführt?
   - Check-Sequenz: Position-Size → Exposure → Tagesverlust → Circuit-Breaker?
   - Bei Limit-Überschreitung: Order-Rejection + Alert-Publishing auf `alerts`-Channel?

3. **Circuit-Breaker-Implementierung**:
   - Wie wird der Circuit-Breaker-State gespeichert? (Redis-Flag? DB-Tabelle `circuit_breaker_state`?)
   - State-Machine: `CLOSED` (Normal) → `OPEN` (≥5% Drawdown) → `HALF_OPEN` (Recovery-Test)?
   - Wer entscheidet über Recovery? (Manual Reset via `/reset`-Endpoint? Automatic nach X Stunden?)

4. **P&L-Berechnung**:
   - Realized P&L: Aus `trades`-Tabelle (Close-Price - Entry-Price)
   - Unrealized P&L: Aus `positions`-Tabelle (Current-Price - Avg-Entry-Price)
   - Tagesverlust: Sum(Realized + Unrealized) über alle Symbole seit 00:00 UTC?

5. **Alert-Triggering**:
   - Redis Pub/Sub auf `alerts`-Channel – welches Event-Schema?
   ```json
   {
     "type": "risk_alert",
     "severity": "critical",  // info, warning, critical
     "reason": "position_limit_exceeded",
     "symbol": "BTC_USDT",
     "current_exposure": 0.12,
     "limit": 0.10,
     "timestamp": 1736555700
   }
   ```

### **Gewünschtes Dokument**:

**Dateiname**: `backoffice/docs/research/cdb_risk.md`

**Inhalte**:

```markdown
## Risk Manager – Limit-Enforcement-Logic

## 1. Position-Tracking
DB-Schema: positions
- symbol (VARCHAR)
- quantity (DECIMAL)
- avg_entry_price (DECIMAL)
- unrealized_pnl (DECIMAL)  -- berechnet bei jedem market_data-Event
- last_updated (TIMESTAMP)

Aggregation:
- Per-Symbol-Exposure: quantity * avg_entry_price
- Total-Exposure: SUM(per_symbol_exposure)

## 2. Limit-Enforcement-Flow
Signal-Event → Risk-Manager.check_limits()

Check-Sequenz:
1. Position-Size-Check: new_position / total_capital ≤ MAX_POSITION_PCT (10%)
2. Exposure-Check: SUM(positions) / total_capital ≤ MAX_EXPOSURE_PCT (50%)
3. Daily-Drawdown-Check: (realized_pnl + unrealized_pnl) / initial_capital ≥ -MAX_DAILY_DRAWDOWN_PCT (-5%)
4. Circuit-Breaker-Check: circuit_breaker_state == CLOSED

Bei FAIL: Order-Rejection + Alert-Publishing

## 3. Circuit-Breaker-Implementierung
State-Storage: Redis-Key `circuit_breaker:state`
States:
- CLOSED (Normal-Betrieb)
- OPEN (≥5% Drawdown → Alle Orders rejected)
- HALF_OPEN (Manual Reset → Test-Order erlaubt)

Recovery:
- Manual Reset via POST /api/risk/circuit_breaker/reset
- Requires: Admin-Authentication (Basic Auth mit ENV-Variable RISK_ADMIN_PASSWORD)

## 4. P&L-Berechnung
Realized P&L:
SELECT SUM(close_price - entry_price) FROM trades WHERE DATE(timestamp) = CURRENT_DATE

Unrealized P&L:
SELECT SUM((current_price - avg_entry_price) * quantity) FROM positions

Daily-Drawdown:
(realized_pnl + unrealized_pnl) / initial_capital_at_midnight

## 5. Alert-Event-Schema
{
  "type": "risk_alert",
  "severity": "critical",
  "reason": "circuit_breaker_triggered",
  "details": {
    "daily_drawdown": -0.052,
    "limit": -0.05,
    "timestamp": 1736555700
  }
}
```

### **Warum kritisch**:
- Risk Manager ist **Schutzschild** vor Kapitalverlust
- Ohne konkrete Logic-Doku können Agenten keine Risk-Bugs identifizieren
- Bei Live-Trading = **systemkritisch** (Bug kann zu 100% Kapitalverlust führen)

---

## 3. ✅ **COMPLETED**: Grafana-Dashboard – Interpretations-Guide

**Dokument erstellt**: `backoffice/docs/research/GRAFANA_DASHBOARD_GUIDE.md` (2025-10-30, 550 Zeilen)

### **Problem-Statement** (gelöst):
- ✅ **Vorhanden**: Vollständige Panel-Interpretation (alle 15+ Panels)
- ✅ **Vorhanden**: Threshold-Tabelle (Normal/Warning/Critical)
- ✅ **Vorhanden**: 3 realistische Troubleshooting-Szenarien
- ✅ **Vorhanden**: Täglicher Check-Workflow für Phase 7
- ✅ **Vorhanden**: Export/Import-Anleitung

### **Dokumentierte Inhalte**:

1. **Panel-Struktur**:
   - Welche Panels zeigen welche Metriken?
   - Panel-Namen → Prometheus-Queries → Interpretation
   - Welche Panels sind **kritisch** (müssen überwacht werden)?
   - Welche Panels sind **informativ** (nice-to-have)?

2. **Schwellwerte**:
   - Welche Werte sind **normal**? (CPU 10-30%, Memory 50-100MB?)
   - Welche Werte sind **kritisch**? (CPU >80%, Memory >500MB?)
   - Welche Werte erfordern **sofortige Action**? (signals_generated = 0 für >5min?)

3. **Anomalie-Erkennung**:
   - Wie erkenne ich einen **WebSocket-Feed-Ausfall**? (market_data-Events = 0)
   - Wie erkenne ich **Signal-Engine-Probleme**? (signals_generated stagiert)
   - Wie erkenne ich **Risk-Manager-Überlastung**? (response-time >1s)

4. **Troubleshooting-Workflows**:
   - **Szenario**: Panel "Signal Engine Status" zeigt `0` für 10 Minuten
     - **Action 1**: Prüfe WebSocket-Screener: `curl http://localhost:8000/health`
     - **Action 2**: Prüfe Redis Pub/Sub: `docker exec -it cdb_redis redis-cli SUBSCRIBE market_data`
     - **Action 3**: Prüfe Signal-Engine-Logs: `docker logs cdb_signal_engine --tail 50`

   - **Szenario**: Panel "CPU Usage" zeigt >90% für 5 Minuten
     - **Action 1**: Prüfe Container-Ressourcen: `docker stats`
     - **Action 2**: Prüfe laufende Queries: `docker exec -it cdb_postgres pg_stat_activity`
     - **Action 3**: Restart betroffenen Service: `docker restart <container>`

5. **Export/Import**:
   - Wie importiere ich das Dashboard in Grafana? (API-Request? UI-Upload?)
   - Wie exportiere ich Änderungen zurück? (Dashboard → JSON-Download?)

### **Gewünschtes Dokument**:

**Dateiname**: `backoffice/docs/research/GRAFANA_DASHBOARD_GUIDE.md`

**Inhalte**:

```markdown
## Grafana-Dashboard – Interpretations-Guide

## 1. Panel-Übersicht

### **Panel 1: Signal Engine Status** (Kritisch ⚠️)
**Metrik**: `signal_engine_status` (Gauge: 1=running, 0=stopped)
**Normal**: `1` (durchgehend)
**Kritisch**: `0` für >2 Minuten
**Action bei Kritisch**:
1. `curl http://localhost:8001/health` → Erwartung: `{"status":"running"}`
2. Falls DOWN: `docker logs cdb_signal_engine --tail 50`
3. Falls Redis-Error: `docker exec -it cdb_redis redis-cli PING`

---

### **Panel 2: Signals Generated (Total)** (Informativ)
**Metrik**: `signals_generated_total` (Counter)
**Normal**: Steigende Kurve (≥1 Signal pro 5 Minuten)
**Anomalie**: Flatline für >10 Minuten → WebSocket-Feed-Problem
**Action bei Anomalie**:
1. `curl http://localhost:8000/health` → Prüfe WebSocket-Screener
2. Falls `"stale"`: WebSocket-Reconnect erforderlich (Container-Restart)

---

### **Panel 3: CPU Usage per Service** (Kritisch bei >80%)
**Metrik**: `rate(process_cpu_seconds_total[1m])`
**Normal**: 10-30% pro Service
**Kritisch**: >80% für >5 Minuten
**Action bei Kritisch**:
1. `docker stats` → Identifiziere belasteten Container
2. `docker logs <container> --tail 100` → Suche nach Error-Loops
3. Falls DB-Query-Problem: `docker exec -it cdb_postgres psql -U admin -d claire_de_binare -c "SELECT * FROM pg_stat_activity;"`

---

## 2. Schwellwerte-Tabelle

| Panel | Metrik | Normal | Warning | Critical |
|-------|--------|--------|---------|----------|
| Signal Engine Status | signal_engine_status | 1 | – | 0 (>2min) |
| Signals Generated | signals_generated_total | +1 per 5min | Flatline >5min | Flatline >10min |
| CPU Usage | process_cpu_seconds | 10-30% | 50-80% | >80% |
| Memory Usage | process_resident_memory_bytes | 50-100MB | 200-300MB | >500MB |
| HTTP Request Latency | http_request_duration_seconds | <50ms | 50-200ms | >200ms |
| Redis Pub/Sub Events | redis_pubsub_events_total | +10 per min | <5 per min | 0 per 5min |

---

## 3. Troubleshooting-Workflows

### **Szenario A: Keine Signale generiert**
**Symptom**: `signals_generated_total` Flatline für >10 Minuten
**Diagnose-Schritte**:
1. Prüfe WebSocket-Screener: `curl http://localhost:8000/health`
   - Falls `{"status":"ok"}` → WebSocket OK
   - Falls `{"status":"stale"}` → WebSocket-Feed unterbrochen
2. Prüfe Redis Pub/Sub: `docker exec -it cdb_redis redis-cli SUBSCRIBE market_data`
   - Sollte Events innerhalb 60s zeigen
   - Falls keine Events → WebSocket-Screener-Restart
3. Prüfe Signal-Engine: `curl http://localhost:8001/status`
   - Falls `signals_generated = 0` → Threshold-Config prüfen (ENV: SIGNAL_THRESHOLD_PCT)

**Fix**:
```bash
## WebSocket-Screener-Restart
docker restart cdb_ws

## Warte 30s
sleep 30

## Prüfe erneut
curl http://localhost:8001/status
```

---

### **Szenario B: CPU-Usage >80%**
**Symptom**: `process_cpu_seconds_total` rate >0.8 für >5 Minuten
**Diagnose-Schritte**:
1. Identifiziere betroffenen Container: `docker stats`
2. Prüfe Logs auf Error-Loops: `docker logs <container> --tail 100 | grep ERROR`
3. Falls Postgres: Prüfe laufende Queries:
   ```sql
   docker exec -it cdb_postgres psql -U admin -d claire_de_binare -c "
   SELECT pid, usename, query, state, query_start
   FROM pg_stat_activity
   WHERE state != 'idle'
   ORDER BY query_start;
   "
   ```

**Fix**:
```bash
## Falls Query-Lock: Kill PID
docker exec -it cdb_postgres psql -U admin -d claire_de_binare -c "SELECT pg_terminate_backend(<pid>);"

## Falls Service-Problem: Restart
docker restart <container>
```

---

## 4. Dashboard Import/Export

### **Import (einmalig bei Setup)**:
```bash
## 1. Grafana-Login
http://localhost:3000
User: admin
Password: REDACTED_REDIS_PW$$

## 2. Dashboards → Import → Upload JSON
## Datei: backoffice/docs/CLAIRE_DE_BINARE_DASHBOARD.json

## 3. Data-Source: Prometheus (http://prometheus:9090)
```

### **Export (nach Änderungen)**:
```bash
## 1. Dashboard öffnen
## 2. Settings (⚙️) → JSON Model → Copy to Clipboard
## 3. Paste in CLAIRE_DE_BINARE_DASHBOARD.json
## 4. Commit to Git
```

---

## 5. Empfohlene Monitoring-Routine (7-Day-Test)

**Täglich (09:00 UTC)**:
- [ ] Prüfe Panel "Signal Engine Status" → Sollte `1` sein
- [ ] Prüfe Panel "Signals Generated" → Sollte steigende Kurve zeigen
- [ ] Prüfe Panel "CPU Usage" → Sollte <50% sein
- [ ] Prüfe Panel "Memory Usage" → Sollte <200MB sein

**Bei Anomalie**:
- [ ] Screenshot des problematischen Panels
- [ ] Logs exportieren: `docker logs <container> > logs/incident_YYYY-MM-DD.log`
- [ ] Eintrag in `backoffice/logs/7d-test-incidents.txt`
```

### **Warum nützlich**:
- Grafana ist **primäres Monitoring-Tool** während 7-Day-Stability-Test
- Ohne Interpretations-Guide können Agenten Anomalien nicht korrekt interpretieren
- Bei Paper-Trading-Test = **täglich benötigt** für Status-Reports

---

## 📋 Zusammenfassung & Priorisierung

| # | Dokument | Priorität | Grund | Geschätzter Aufwand |
|---|----------|-----------|-------|---------------------|
| 1 | `cdb_execution.md` | ⚠️ **KRITISCH** | Live-Trading-Kernstück, Security-Risiko bei Bugs | 2-3 Stunden |
| 2 | `cdb_risk.md` | ⚠️ **HOCH** | Kapitalschutz, Circuit-Breaker-Logic | 1-2 Stunden |
| 3 | `GRAFANA_DASHBOARD_GUIDE.md` | ⚠️ **MITTEL** | Monitoring-Interpretation für 7-Day-Test | 1-2 Stunden |

---

## 🚀 Nächste Schritte (User-Unterstützung erbeten)

### **Option 1: User erstellt Dokumente selbst**
- User dokumentiert MEXC-API-Integration aus eigenem Wissen
- User erstellt Screenshots von Grafana-Dashboard mit Erklärungen
- User dokumentiert Risk-Manager-Code-Logic aus `backoffice/services/risk_manager/`

### **Option 2: User liefert Rohdaten, Agent strukturiert**
- User kopiert relevante Code-Snippets aus Execution/Risk-Services
- User macht Grafana-Dashboard-Screenshots
- Agent strukturiert Inhalte gemäß Template oben

### **Option 3: Pair-Programming-Ansatz**
- User startet Screen-Share-Session
- Agent stellt gezielte Fragen ("Wie wird die MEXC-Signatur generiert?")
- User zeigt Code/Dashboard live
- Agent dokumentiert parallel

---

## ✅ Erfolgskriterien

**Dokumente sind vollständig, wenn**:
- ✅ Agents können Execution-Service-Bugs **ohne menschliche Hilfe debuggen**
- ✅ Agents können Risk-Manager-Limits **selbstständig validieren**
- ✅ Agents können Grafana-Anomalien **korrekt interpretieren und beheben**

---

**Ende des Dokuments** | **Letzte Aktualisierung**: 2025-01-11 | **Status**: Wartet auf User-Unterstützung