# 3-Tage-Test: Continuous Adaptive Intensity System

**Status:** ✅ **DEPLOYMENT READY**
**Datum:** 2025-11-30
**Ziel:** Testen des kontinuierlichen, proportionalen Adaptive Intensity Systems über 72 Stunden

---

## 🎯 Was wird getestet?

Das neue **Continuous Adaptive Intensity System** passt Trading-Parameter **in Echtzeit** basierend auf der Performance der letzten 300 Trades an:

- **Performance Score** (0.0 - 1.0) berechnet aus:
  - Winrate × 40%
  - Profit Factor × 40%
  - Drawdown × 20%

- **Dynamische Parameter** (linear interpoliert):
  - Signal Threshold: 3.0% (schlecht) → 1.5% (perfekt)
  - RSI Threshold: 60 (konservativ) → 40 (aggressiv)
  - Max Exposure: 40% (schlecht) → 80% (perfekt)
  - Max Position: 8% (schlecht) → 12% (perfekt)

- **Smooth Transitions**: Max 5% Score-Änderung pro Update (alle 30s)

---

## 📋 Pre-Deployment Checklist

### 1. ✅ Code & Tests

- [x] **25 Unit Tests** - alle bestanden (13 Dynamic Adjuster + 12 Integration)
- [x] Signal Engine Integration komplett
- [x] Risk Manager Integration komplett
- [x] Docker Compose konfiguriert
- [x] ENV-Variablen validiert

### 2. ✅ Services Konfiguriert

**Neue Services:**
- `cdb_adaptive_intensity` (Port 8005) - Continuous Update Loop

**Modifizierte Services:**
- `cdb_core` (Signal Engine) - konsumiert dynamische Parameter
- `cdb_risk` (Risk Manager) - konsumiert dynamische Parameter

**Bestehende Services:**
- `cdb_ws` - Market Data Screener
- `cdb_execution` - Paper Trading Execution
- `cdb_db_writer` - PostgreSQL Persistence
- `cdb_postgres` - Trade History (letzte 300 Trades)
- `cdb_redis` - Parameter Broadcasting

### 3. ⚠️ Wichtige ENV-Variablen

Überprüfe in `.env`:

```bash
# Adaptive Intensity Service
ADAPTIVE_PORT=8005
ADAPTIVE_UPDATE_INTERVAL_SEC=30  # 30s Updates!
ADAPTIVE_LOOKBACK_TRADES=300

# Score Gewichtung
ADAPTIVE_WINRATE_WEIGHT=0.4
ADAPTIVE_PF_WEIGHT=0.4
ADAPTIVE_DD_WEIGHT=0.2

# Parameter Ranges (Min bei Score=0.0, Max bei Score=1.0)
ADAPTIVE_THRESHOLD_MIN=3.0
ADAPTIVE_THRESHOLD_MAX=1.5
ADAPTIVE_RSI_MIN=60.0
ADAPTIVE_RSI_MAX=40.0
ADAPTIVE_VOLUME_MIN=2.0
ADAPTIVE_VOLUME_MAX=0.5
ADAPTIVE_POSITION_MIN=0.08
ADAPTIVE_POSITION_MAX=0.12
ADAPTIVE_EXPOSURE_MIN=0.40
ADAPTIVE_EXPOSURE_MAX=0.80

# Smooth Transitions
ADAPTIVE_MAX_CHANGE=0.05  # Max 5% Score-Änderung pro Update

# Risk Manager (für Paper Trading)
MAX_EXPOSURE_PCT=1.00  # 100% für Paper-Trading ✅
MAX_POSITION_PCT=0.10
MAX_DAILY_DRAWDOWN_PCT=0.05
```

---

## 🚀 Deployment Steps

### Schritt 1: System stoppen (falls läuft)

```bash
docker-compose down
```

### Schritt 2: Images neu bauen

```bash
docker-compose build cdb_adaptive_intensity
docker-compose build cdb_core
docker-compose build cdb_risk
```

### Schritt 3: System starten

```bash
docker-compose up -d
```

**Service-Reihenfolge** (automatisch durch depends_on):
1. `cdb_redis` + `cdb_postgres`
2. `cdb_prometheus` + `cdb_grafana`
3. `cdb_ws` (Market Data)
4. `cdb_core` (Signal Engine)
5. `cdb_risk` (Risk Manager)
6. `cdb_execution` (Execution Service)
7. `cdb_db_writer` (DB Writer)
8. `cdb_adaptive_intensity` (Adaptive Intensity)

### Schritt 4: Health-Checks

Warte 30-60 Sekunden, dann:

```bash
# Alle Services
docker-compose ps

# Health-Check Endpoints
curl http://localhost:8000/health  # cdb_ws
curl http://localhost:8001/health  # cdb_core
curl http://localhost:8002/health  # cdb_risk
curl http://localhost:8003/health  # cdb_execution
curl http://localhost:8005/health  # cdb_adaptive_intensity ✨ NEU
```

**Erwartete Antwort (cdb_adaptive_intensity):**
```json
{
  "status": "ok",
  "service": "adaptive_intensity",
  "version": "0.1.0"
}
```

### Schritt 5: Initiale Parameter-Check

```bash
curl http://localhost:8005/status | jq
```

**Erwartete Antwort (bei < 50 Trades):**
```json
{
  "status": "insufficient_data",
  "message": "Not enough trades for dynamic adjustment",
  "current_parameters": {
    "signal_threshold_pct": "2.00% (ENV fallback)",
    "max_exposure_pct": "50% (ENV fallback)"
  }
}
```

**Nach 50+ Trades:**
```json
{
  "status": "active",
  "performance_score": {
    "overall": "55.2%",
    "winrate": "52.0%",
    "profit_factor": "60.0%",
    "drawdown": "70.0%",
    "interpretation": "⚖️ Moderate - Balanced"
  },
  "current_parameters": {
    "signal_threshold_pct": "2.33%",
    "rsi_threshold": "52.4",
    "max_exposure_pct": "56%"
  },
  "raw_metrics": {
    "winrate": "52.0%",
    "profit_factor": "1.20",
    "max_drawdown": "3.0%",
    "trade_count": 156
  }
}
```

---

## 📊 Monitoring während des 3-Tage-Tests

### 1. Adaptive Intensity Dashboard

**Wichtige Metriken:**

```bash
# Aktueller Performance Score
curl http://localhost:8005/status | jq '.performance_score.overall'

# Aktuelle Parameter
curl http://localhost:8005/parameters | jq

# Prometheus Metriken
curl http://localhost:8005/metrics
```

**Key Prometheus Metrics:**
```prometheus
# Performance Score (0.0 - 1.0)
adaptive_intensity_performance_score

# Dynamische Parameter
adaptive_intensity_signal_threshold_pct
adaptive_intensity_rsi_threshold
adaptive_intensity_max_exposure_pct
adaptive_intensity_max_position_pct

# Update Performance
adaptive_intensity_update_duration_seconds
```

### 2. Signal Engine Logs

```bash
docker logs -f cdb_core | grep "Dynamic params updated"
```

**Erwartete Log-Einträge:**
```
[INFO] 🔄 Dynamic params updated: Threshold=2.33%, RSI=52.4
[INFO] ✨ Signal generiert: BTCUSDT BUY @ $50123.45 (+2.45%, Confidence: 0.82, Threshold: 2.33%)
```

### 3. Risk Manager Logs

```bash
docker logs -f cdb_risk | grep "Dynamic params updated"
```

**Erwartete Log-Einträge:**
```
[INFO] 🔄 Dynamic params updated: Max Position=10.5%, Max Exposure=56.0%
[INFO] 🚀 Risk-Manager gestartet
[INFO]    Max Position: 10.5% (DYNAMIC)
[INFO]    Max Exposure: 56.0% (DYNAMIC)
```

### 4. Grafana Dashboards

**URL:** http://localhost:3000

**Wichtige Panels:**

1. **Performance Score Over Time**
   ```promql
   adaptive_intensity_performance_score
   ```
   → Zeigt Score-Entwicklung (0.0 - 1.0)

2. **Dynamic Threshold Trend**
   ```promql
   adaptive_intensity_signal_threshold_pct
   ```
   → Zeigt wie aggressiv/konservativ der Bot handelt

3. **Correlation: Score vs. Trades**
   ```promql
   # Score (linke Y-Achse)
   adaptive_intensity_performance_score

   # Trades per Hour (rechte Y-Achse)
   rate(execution_orders_filled_total[1h]) * 3600
   ```
   → Zeigt ob höherer Score = mehr Trades

4. **Exposure Utilization**
   ```promql
   risk_total_exposure_value / (adaptive_intensity_max_exposure_pct * 100000)
   ```
   → Zeigt % der maximal erlaubten Exposure

---

## 🎯 Erwartete Verhaltensweisen

### Szenario 1: Winning Streak (Performance steigt)

**Tag 1 (Score 0.45):**
```
Threshold: 2.75%  (konservativ)
Exposure:  58%    (niedrig)
→ Weniger Signale, kleinere Positionen
```

**Tag 2 (Score steigt auf 0.60):**
```
Threshold: 2.35%  (aggressiver)
Exposure:  64%    (höher)
→ Mehr Signale, größere Positionen
```

**Tag 3 (Score steigt auf 0.70):**
```
Threshold: 1.95%  (sehr aggressiv)
Exposure:  72%    (hoch)
→ Deutlich mehr Signale, größere Exposure
```

**Erwartung:**
- Bot wird graduell aggressiver
- Handelsfrequenz steigt kontinuierlich
- Exposure wächst proportional

### Szenario 2: Losing Streak (Performance fällt)

**Tag 1 (Score 0.65):**
```
Threshold: 2.02%
Exposure:  66%
```

**Tag 2 (Score fällt auf 0.50):**
```
Threshold: 2.25%
Exposure:  60%
→ System bremst ab
```

**Tag 3 (Score fällt auf 0.35):**
```
Threshold: 2.52%
Exposure:  54%
→ System wird sehr konservativ
```

**Erwartung:**
- Bot wird graduell konservativer
- Handelsfrequenz sinkt
- Exposure reduziert sich

### Szenario 3: Stabile Performance (Score konstant)

**Über 3 Tage: Score schwankt 0.55 - 0.60**
```
Threshold: 2.30% - 2.35%
Exposure:  62% - 64%
```

**Erwartung:**
- Parameter bleiben relativ stabil
- Kleine Anpassungen innerhalb der Range
- Smooth Transitions verhindern Thrashing

---

## ⚠️ Troubleshooting

### Problem 1: "insufficient_data" trotz >300 Trades

**Diagnose:**
```bash
# Prüfe Trade-Count in DB
docker exec -it cdb_postgres psql -U claire_user -d claire_de_binare -c "SELECT COUNT(*) FROM trades;"
```

**Lösung:**
- Wenn < 50 Trades: Warte bis mehr Trades vorhanden
- Wenn > 50 Trades: Prüfe `ADAPTIVE_LOOKBACK_TRADES` in ENV

### Problem 2: Signal Engine verwendet keine dynamischen Parameter

**Diagnose:**
```bash
# Prüfe Redis
docker exec -it cdb_redis redis-cli -a $REDIS_PASSWORD GET "adaptive_intensity:current_params"
```

**Erwartete Ausgabe:**
```json
{"timestamp":"2025-11-30T12:34:56","performance_score":0.55,"signal_threshold_pct":2.33,...}
```

**Lösung:**
- Wenn leer: Adaptive Intensity Service neustart
- Wenn vorhanden: Signal Engine Logs prüfen auf "Failed to fetch dynamic params"

### Problem 3: Score springt zu stark

**Diagnose:**
```bash
# Prüfe max_change Einstellung
echo $ADAPTIVE_MAX_CHANGE
```

**Lösung:**
- Sollte 0.05 sein (5% max Änderung)
- Bei zu großen Sprüngen: ENV überprüfen

### Problem 4: Service startet nicht

**Diagnose:**
```bash
docker logs cdb_adaptive_intensity
```

**Häufige Fehler:**
- PostgreSQL nicht erreichbar: Warte auf `cdb_postgres` Health
- Redis nicht erreichbar: Warte auf `cdb_redis` Health
- ENV-Variable fehlt: Prüfe `.env` Datei

---

## 📈 Success Criteria für 3-Tage-Test

### Minimum Success (Must-Have)

✅ **System läuft stabil über 72h**
- Keine Container-Restarts durch Crashes
- Health-Checks bleiben grün

✅ **Parameter-Updates funktionieren**
- Score wird alle 30s neu berechnet
- Redis wird updated
- Signal Engine + Risk Manager konsumieren Updates

✅ **Proportionale Anpassung nachweisbar**
- Score steigt → Parameter werden aggressiver
- Score fällt → Parameter werden konservativer
- Smooth Transitions funktionieren (max 5% Änderung)

### Target Success (Should-Have)

✅ **Höhere Handelsfrequenz bei guter Performance**
- Signale/Tag steigen bei Score > 0.60
- Exposure steigt proportional

✅ **Selbst-Regulierung bei schlechter Performance**
- System bremst automatisch ab bei Score < 0.45
- Drawdown bleibt unter Kontrolle

✅ **Keine Zero-Activity-Incidents**
- Mindestens 10 Paper-Trades pro Tag
- Kontinuierlicher Signal-Flow

### Optimal Success (Nice-to-Have)

✅ **Performance verbessert sich über 3 Tage**
- Winrate steigt oder bleibt stabil
- Profit Factor > 1.0
- Drawdown < 5%

✅ **System findet optimalen Betriebspunkt**
- Score stabilisiert sich bei 0.55 - 0.70
- Parameter konvergieren zu "sweet spot"

---

## 📝 Daily Check-Liste

### Jeden Tag um 09:00, 15:00, 21:00:

1. **Health-Check aller Services**
   ```bash
   docker-compose ps
   ```

2. **Adaptive Intensity Status**
   ```bash
   curl http://localhost:8005/status | jq
   ```

3. **Trade Count prüfen**
   ```bash
   docker exec -it cdb_postgres psql -U claire_user -d claire_de_binare \
     -c "SELECT COUNT(*) as trades_today FROM trades WHERE DATE(timestamp) = CURRENT_DATE;"
   ```

4. **Performance Score Trend**
   ```bash
   curl http://localhost:8005/status | jq '.performance_score.overall'
   ```

5. **Log-Check auf Errors**
   ```bash
   docker logs cdb_adaptive_intensity --tail 50 | grep -i error
   docker logs cdb_core --tail 50 | grep -i error
   docker logs cdb_risk --tail 50 | grep -i error
   ```

---

## 🎬 Start-Kommando für 3-Tage-Test

```bash
# 1. System stoppen (falls läuft)
docker-compose down

# 2. Services neu bauen
docker-compose build cdb_adaptive_intensity cdb_core cdb_risk

# 3. System starten
docker-compose up -d

# 4. Logs verfolgen (erste 5 Minuten)
docker-compose logs -f cdb_adaptive_intensity cdb_core cdb_risk

# 5. Health-Check
sleep 60
curl http://localhost:8005/health
curl http://localhost:8001/health
curl http://localhost:8002/health

# 6. Initiale Metriken
curl http://localhost:8005/status | jq
```

---

## 📊 Daten-Sammlung für Post-Test-Analyse

**Am Ende des 3-Tage-Tests:**

```bash
# 1. Alle Trades exportieren
docker exec -it cdb_postgres psql -U claire_user -d claire_de_binare \
  -c "COPY (SELECT * FROM trades WHERE timestamp >= NOW() - INTERVAL '3 days') TO STDOUT WITH CSV HEADER;" \
  > 3_day_test_trades.csv

# 2. Performance Score History (aus Prometheus)
curl 'http://localhost:19090/api/v1/query_range?query=adaptive_intensity_performance_score&start=<START_TIMESTAMP>&end=<END_TIMESTAMP>&step=30' \
  > 3_day_test_score_history.json

# 3. Parameter History
curl 'http://localhost:19090/api/v1/query_range?query=adaptive_intensity_signal_threshold_pct&start=<START_TIMESTAMP>&end=<END_TIMESTAMP>&step=30' \
  > 3_day_test_threshold_history.json

# 4. Service Logs
docker logs cdb_adaptive_intensity > 3_day_test_adaptive_logs.txt
docker logs cdb_core > 3_day_test_signal_logs.txt
docker logs cdb_risk > 3_day_test_risk_logs.txt
```

---

## ✅ Status: DEPLOYMENT READY!

**Alle Systeme bereit für 3-Tage-Test:**

- ✅ 25 Tests bestanden (13 Unit + 12 Integration)
- ✅ Docker Compose konfiguriert
- ✅ ENV-Variablen validiert
- ✅ Services integriert
- ✅ Monitoring vorbereitet
- ✅ Troubleshooting-Guide erstellt

**Viel Erfolg beim Test! 🚀**
