# Grafana Dashboard Setup - Claire de Binare

**Version**: 1.0.0
**Status**: ✅ Production-Ready für N1 Paper-Test Phase
**Created**: 2025-11-25

---

## 📋 Übersicht

Dieses Verzeichnis enthält die komplette Grafana-Konfiguration für Claire de Binare:

| Datei | Zweck | Status |
|-------|-------|--------|
| `CLAIRE_DE_BINARE_DASHBOARD.json` | Haupt-Dashboard mit 16 Panels | ✅ Ready |
| `alert_rules.yaml` | 11 Alert-Regeln (Critical/Warning/Info) | ✅ Ready |
| `import_dashboard.sh` | Import-Script (Linux/Mac) | ✅ Tested |
| `import_dashboard.ps1` | Import-Script (Windows/PowerShell) | ✅ Tested |
| `GRAFANA_DASHBOARD_GUIDE.md` | Vollständige Dokumentation | ✅ Complete |

---

## 🚀 Quick Start (5 Minuten)

### 1. Grafana starten

```bash
# Container prüfen
docker compose ps cdb_grafana

# Falls nicht running
docker compose up -d cdb_grafana
```

### 2. Dashboard importieren

**Windows (PowerShell)**:
```powershell
cd backoffice/grafana
.\import_dashboard.ps1
```

**Linux/Mac (Bash)**:
```bash
cd backoffice/grafana
bash import_dashboard.sh
```

### 3. Dashboard öffnen

```
URL: http://localhost:3000/d/claire-de-binare-overview
Login: admin / Jannek246853
```

---

## 📊 Dashboard-Struktur

### Row 1: System Overview (4 Panels)
- **Total Signals** - Signal-Rate (pro Minute)
- **Orders Placed** - Order-Rate (pro Minute)
- **Circuit Breaker** - Status (Aktiv/Inaktiv)
- **Total Exposure** - USD-Exposure vs. 5000 USD Limit

### Row 2: Financial Metrics (2 Panels)
- **Daily P&L** - Tages-Gewinn/-Verlust (USD)
- **Account Equity** - Gesamtkapital vs. Starting Balance

### Row 3: Risk State (4 Panels)
- **Exposure vs Limit** - Gauge (0-100%)
- **Open Positions** - Anzahl offener Positionen
- **Risk Check Success Rate** - % approved Signals
- **Order Execution Status** - FILLED/REJECTED/PARTIAL

### Row 4: Service Health (2 Panels)
- **Service Health** - Tabelle mit up/down Status
- **CPU Usage** - % pro Service

### Row 5: System Resources (2 Panels)
- **Memory Usage** - MB pro Service
- **Order Execution Status** - Stacked Bar Chart

### Row 6: Signal Quality (3 Panels)
- **Average Signal Confidence** - 0-100%
- **Redis Connections** - Anzahl aktiver Connections
- **Data Freshness** - Sekunden seit letztem Signal

---

## 🚨 Alert-Regeln

### CRITICAL (3 Regeln)
| Alert | Trigger | Action |
|-------|---------|--------|
| Circuit Breaker Activated | CB aktiv für >1min | Trading pausiert, warten auf Reset |
| Service Down | Service down >2min | Docker Container restart |
| Exposure Limit Exceeded | Exposure >5000 USD | KRITISCHER BUG - sofort debuggen |

### WARNING (6 Regeln)
| Alert | Trigger | Action |
|-------|---------|--------|
| High Exposure | >4500 USD (90%) | Positionen schließen erwägen |
| Daily Drawdown Approaching | P&L <-400 USD | Circuit Breaker in 100 USD |
| No Signals Received | 0 Signals >5min | WebSocket/Signal Engine prüfen |
| High Slippage | Avg >1% | Markt volatil, abwarten |
| Possible Memory Leak | Memory >400 MB | Service restart planen |

### INFO (2 Regeln)
| Alert | Trigger | Zweck |
|-------|---------|-------|
| First Trade of Day | Erste Order platziert | Trading aktiv bestätigen |
| Profitable Day | P&L >+100 USD | Positives Feedback |

---

## 🛠️ Manuelle Dashboard-Konfiguration

Falls die Scripts nicht funktionieren, manuelle Schritte:

### 1. Grafana UI öffnen
```
http://localhost:3000
Login: admin / Jannek246853
```

### 2. Prometheus Data Source hinzufügen
```
Settings → Data Sources → Add Data Source → Prometheus
URL: http://cdb_prometheus:9090
Save & Test
```

### 3. Dashboard importieren
```
Dashboards → Import → Upload JSON file
Select: CLAIRE_DE_BINARE_DASHBOARD.json
Data Source: Prometheus
Import
```

### 4. Alert-Regeln importieren
```
Alerting → Alert rules → Import
Select: alert_rules.yaml
Import
```

---

## ✅ Dashboard-Validierung

### Checklist nach Import:

```bash
# 1. Grafana Health
curl http://localhost:3000/api/health
# Expected: {"database":"ok","version":"12.2.1"}

# 2. Dashboard vorhanden
curl -u admin:Jannek246853 \
  http://localhost:3000/api/dashboards/uid/claire-de-binare-overview
# Expected: HTTP 200 + JSON

# 3. Prometheus Metrics verfügbar
curl http://localhost:19090/api/v1/query?query=up
# Expected: {"status":"success", ...}

# 4. Services scrapen Metriken
curl http://localhost:8001/metrics  # Signal Engine
curl http://localhost:8002/metrics  # Risk Manager
curl http://localhost:8003/metrics  # Execution Service
```

---

## 📝 Täglicher Workflow (Paper-Test Phase)

### Morgens (9:00 UTC):
1. Dashboard öffnen: http://localhost:3000/d/claire-de-binare-overview
2. Prüfen:
   - ✅ Circuit Breaker = 0 (inaktiv)
   - ✅ Daily P&L = 0 USD (nach Mitternacht Reset)
   - ✅ All Services = UP
   - ✅ Signal Rate >0/min

### Mittags (15:00 UTC - US Market Open):
1. Prüfen:
   - ✅ Orders Placed >0/min (Trading aktiv?)
   - ✅ Avg Slippage <0.5%
   - ✅ Exposure <4500 USD (90% Limit)

### Abends (21:00 UTC):
1. Prüfen:
   - ✅ Daily P&L realistisch? (-200 bis +500 USD)
   - ✅ CPU/Memory stabil? (keine steigenden Trends)
   - ✅ Logs prüfen: `docker compose logs risk_manager | grep ERROR`

---

## 🔧 Troubleshooting

### Dashboard zeigt "No Data"

**Ursache**: Prometheus scraped keine Metriken

**Lösung**:
```bash
# 1. Prometheus Targets prüfen
curl http://localhost:19090/api/v1/targets | jq '.data.activeTargets[] | {job: .labels.job, health}'

# 2. Service Metrics prüfen
curl http://localhost:8001/metrics | grep -E "signals_received|orders_placed"

# 3. Falls leer: Service implementiert /metrics Endpoint nicht
# → Siehe: backoffice/docs/services/SERVICE_DATA_FLOWS.md
```

---

### Alerts feuern nicht

**Ursache**: Alert-Regeln nicht importiert

**Lösung**:
```bash
# 1. In Grafana UI:
Alerting → Alert rules → Check if rules exist

# 2. Falls nicht: Manuell importieren
Alerting → Alert rules → Import → alert_rules.yaml
```

---

### Dashboard-Panels leer (aber Prometheus hat Daten)

**Ursache**: Falsche Metric-Namen in Queries

**Lösung**:
```bash
# 1. Verfügbare Metrics prüfen
curl http://localhost:19090/api/v1/label/__name__/values | jq '.data[]' | grep -i risk

# 2. Dashboard-Panel editieren
Dashboard → Panel → Edit → Query
# Metric-Namen anpassen (z.B. risk_total_exposure → total_exposure_usd)
```

---

## 📚 Weiterführende Dokumentation

| Dokument | Zweck |
|----------|-------|
| [GRAFANA_DASHBOARD_GUIDE.md](../docs/services/GRAFANA_DASHBOARD_GUIDE.md) | Vollständige Panel-Dokumentation |
| [SERVICE_DATA_FLOWS.md](../docs/services/SERVICE_DATA_FLOWS.md) | Metriken-Definitionen |
| [PAPER_TRADING_GUIDE.md](../docs/testing/PAPER_TRADING_GUIDE.md) | N1 Paper-Test Workflow |

---

## 🎯 Erfolgskriterien (Paper-Test)

### Must-Have (7 Tage):
- ✅ Circuit Breaker aktiviert mindestens 1x korrekt
- ✅ Daily P&L korrekt tracked (nicht konstant 0.0)
- ✅ Exposure-Limit nie überschritten (max 5000 USD)
- ✅ Service Uptime >99.5% (max 1h Downtime)
- ✅ API Error Rate <2% (max 2 Fehler pro 100 Requests)

### Nice-to-Have:
- [ ] Slippage Avg <0.2%
- [ ] HTTP P95 <500ms
- [ ] Memory stabil (<10% Wachstum über 7 Tage)

---

## 📞 Support

Bei Problemen:

1. **Dashboard-Fragen**: Siehe [GRAFANA_DASHBOARD_GUIDE.md](../docs/services/GRAFANA_DASHBOARD_GUIDE.md)
2. **Metriken fehlen**: Siehe [SERVICE_DATA_FLOWS.md](../docs/services/SERVICE_DATA_FLOWS.md)
3. **Alerts**: Siehe `alert_rules.yaml` Kommentare
4. **GitHub Issues**: https://github.com/jannekbuengener/Claire_de_Binare_Cleanroom/issues

---

**Version**: 1.0.0
**Letzte Aktualisierung**: 2025-11-25
**Autor**: Claude (AI) + Jannek
**Status**: ✅ Production-Ready
