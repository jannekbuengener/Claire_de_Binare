# Human-in-the-Loop (HITL) Operations Runbook

**Zweck**: Operativer Leitfaden für manuelle Überwachung und Eingriffe in Claire de Binare Trading Operations.

**Status**: ✅ Implementiert (Issue #244)
**Zuletzt aktualisiert**: 2025-12-27

---

## Überblick

### Was ist HITL?

**Human-in-the-Loop (HITL)** ist ein Kontrollmechanismus, bei dem Menschen kritische Entscheidungen treffen und in automatisierte Prozesse eingreifen können.

**Für Claire de Binare bedeutet das:**
- Menschen überwachen alle Trading-Aktivitäten in Echtzeit
- Menschen können jederzeit eingreifen (Kill-Switch, Order-Cancellations)
- Alle Eingriffe werden vollständig protokolliert
- Eskalationsprozesse sind definiert und dokumentiert

---

## Zugriff auf HITL Control Center

### Grafana Dashboard aufrufen

```powershell
# 1. Stack starten (falls nicht läuft)
make docker-up

# 2. Warten bis alle Services healthy
make docker-health

# 3. Grafana öffnen
# URL: http://localhost:3000
# Login: admin
# Password: siehe .env GRAFANA_PASSWORD
```

### Dashboard Navigation

1. Nach Login: Menü (☰) → Dashboards
2. Ordner: "Claire Trading Bot"
3. Dashboard: "Claire - HITL Control Center"

**Alternativ**: Direktlink `http://localhost:3000/d/claire_hitl_v1`

---

## Dashboard Übersicht

### Kritische Status-Panels (Obere Reihe)

| Panel | Normal | Kritisch | Action |
|-------|--------|----------|--------|
| **🚨 Kill-Switch** | ✅ INACTIVE (grün) | 🚨 ACTIVE (rot) | Siehe Emergency Stop SOP |
| **⚙️ Trading Mode** | 📄 PAPER (blau) | 💰 LIVE (rot) | Verifizieren authorisiert |
| **⚡ Circuit Breaker** | ✅ SAFE (grün) | ⚠️ TRIPPED (orange) | Logs prüfen, Root Cause |
| **📊 Daily P&L** | > 0% (grün) | < -5% (rot) | Circuit Breaker aktiviert |

### Monitoring Panels (Mittlere Reihe)

- **💰 Portfolio Value**: Gesamtwert in USDT, Verlauf letzte Stunde
- **📈 Daily P&L Trend**: P&L% mit Circuit-Breaker-Limit (-5%) als rote Linie

### Risk & Control Panels (Untere Reihe)

- **🔒 Active Risk Limits**: Konfigurierte Limits (Daily Loss, Exposure, Position Size)
- **📜 Recent Manual Interventions**: Aktivierungen/Deaktivierungen der letzten 24h
- **🎯 Active Orders**: Anzahl aktiver Orders
- **💸 Total Exposure**: Summe aller offenen Positionen in USDT
- **⏱️ Service Uptime**: Status aller Services (UP/DOWN)
- **⚠️ HITL Controls**: Anweisungen für manuelle Eingriffe

---

## Manuelle Eingriffsprozeduren

### 1. Emergency Stop (Kill-Switch Activation)

**Wann aktivieren:**
- Ungewöhnliche Marktaktivität (Flash Crash, extreme Volatilität)
- Verdacht auf Systemfehlfunktion
- Unerwartete Verluste
- Verdacht auf Sicherheitsvorfall
- Jede Situation, in der Trading gestoppt werden sollte

**Wie aktivieren:**

```powershell
# Option 1: Über Python (empfohlen)
python -c "from core.safety import activate_kill_switch, KillSwitchReason; activate_kill_switch(KillSwitchReason.MANUAL, 'Grund für Stop', 'operator@example.com')"

# Option 2: Über Makefile (wenn implementiert)
make kill-switch-activate

# Option 3: Siehe EMERGENCY_STOP_SOP.md
```

**Nach Aktivierung:**
1. Dashboard prüfen: Kill-Switch Panel sollte 🚨 ACTIVE (rot) zeigen
2. Logs überprüfen: `docker logs cdb_risk --tail 50`
3. Root Cause identifizieren
4. Problem beheben
5. Deaktivierung nur nach Genehmigung (siehe EMERGENCY_STOP_SOP.md)

---

### 2. Trading Mode Wechsel (PAPER → STAGED → LIVE)

**KRITISCH**: Nur mit expliziter Genehmigung!

**Voraussetzungen für LIVE Mode:**
- ✅ 14-Tage Paper Trading erfolgreich abgeschlossen
- ✅ Alle E2E Tests bestehen
- ✅ Risk Limits konfiguriert und getestet
- ✅ Emergency Stop SOP verstanden
- ✅ Monitoring 24/7 verfügbar
- ✅ Genehmigte Freigabe von System Owner

**Wechsel durchführen:**

```powershell
# 1. Stack stoppen
make docker-down

# 2. .env bearbeiten
# SIGNAL_STRATEGY_ID=paper  → SIGNAL_STRATEGY_ID=live
# MEXC_TESTNET=true         → MEXC_TESTNET=false (NUR für LIVE!)
# DRY_RUN=true              → DRY_RUN=false (NUR für LIVE!)

# 3. LIVE_TRADING_CONFIRMED Flag setzen
# LIVE_TRADING_CONFIRMED=true

# 4. Stack neu starten
make docker-up

# 5. Dashboard überprüfen
# Trading Mode Panel sollte 💰 LIVE (rot) zeigen

# 6. INTENSIV überwachen für erste 24h!
```

**Warnung**: Im LIVE Mode wird echtes Geld gehandelt! Jeder Fehler kann zu Verlusten führen!

---

### 3. Risk Limit Anpassung

**Wann anpassen:**
- Nach Review der Performance-Daten
- Nach Änderung der Portfolio-Größe
- Nach Marktregime-Wechsel
- Als Reaktion auf Volatilitäts-Änderungen

**Limits anpassen:**

```powershell
# 1. Risk Service Config bearbeiten
# services/risk/config.py

# Beispiel:
# MAX_DAILY_LOSS_PERCENT = 5.0  → 3.0 (konservativer)
# MAX_EXPOSURE_PERCENT = 30.0   → 20.0 (konservativer)

# 2. Risk Service neu starten
docker restart cdb_risk

# 3. Dashboard überprüfen
# "Active Risk Limits" Panel sollte neue Werte zeigen

# 4. Logs prüfen
docker logs cdb_risk --tail 20 | grep "LIMIT"
```

**Best Practice**: Limits nur in kleinen Schritten ändern (z.B. 5% → 4% → 3%)

---

### 4. Manuelle Order Cancellation

**Wann canceln:**
- Order hängt (nicht executed nach >5 Minuten)
- Fehlerhafte Order erkannt
- Market Conditions geändert (z.B. Exchange Downtime)

**Order canceln:**

```powershell
# 1. Order ID identifizieren
docker logs cdb_execution | grep "ORDER_ID"

# 2. Order Status prüfen
docker exec cdb_postgres psql -U claire_user -d claire_de_binare -c "SELECT * FROM orders WHERE order_id = 'ORDER_ID';"

# 3. Cancel via Execution Service API (wenn verfügbar)
curl -X POST http://localhost:8003/cancel -d '{"order_id":"ORDER_ID"}'

# 4. Alternativ: Direkter DB Update (NOTFALL!)
# NUR wenn API nicht verfügbar!
docker exec cdb_postgres psql -U claire_user -d claire_de_binare -c "UPDATE orders SET status = 'CANCELLED' WHERE order_id = 'ORDER_ID';"

# 5. Logs überprüfen
docker logs cdb_execution --tail 30
```

---

## Monitoring Best Practices

### Tägliche Routine

**Morgens (vor Marktöffnung):**
1. ✅ Dashboard aufrufen: Alle Panels grün?
2. ✅ Service Health Check: `make docker-health`
3. ✅ Logs auf Errors prüfen: `docker logs cdb_risk --since 24h | grep ERROR`
4. ✅ Daily P&L Review: Gestern im Budget?
5. ✅ Kill-Switch Status: Sollte INACTIVE sein

**Während Trading-Stunden:**
1. 📊 Dashboard alle 15-30 Min checken
2. 📉 Bei P&L < -3%: erhöhte Aufmerksamkeit
3. 🚨 Bei P&L < -4.5%: Vorbereitung auf Circuit Breaker
4. ⚠️ Bei ungewöhnlichen Patterns: Root Cause Analysis

**Abends (nach Marktschluss):**
1. ✅ Daily P&L Review: Ziel erreicht?
2. ✅ Open Positions Review: Overnight Risk akzeptabel?
3. ✅ Logs auf Warnings prüfen: `docker logs cdb_risk --since 24h | grep WARN`
4. ✅ Manual Interventions Review: Warum nötig gewesen?

---

### Alert Thresholds

| Metric | Green | Yellow | Red | Action |
|--------|-------|--------|-----|--------|
| **Daily P&L** | > 0% | -2% to 0% | < -2% | Monitor |
| **Circuit Breaker** | - | - | Triggered | Investigate Root Cause |
| **Active Orders** | 0-10 | 10-50 | > 50 | Check for stuck orders |
| **Exposure** | < 20% | 20-30% | > 30% | Reduce positions |
| **Service Uptime** | ALL UP | 1 DOWN | >1 DOWN | Check logs, restart |

---

## Eskalationsprozess

### Stufe 1: Operator (Selbst)

**Befugnis:**
- Dashboard Monitoring
- Logs Einsicht
- Kill-Switch Aktivierung bei Emergency
- Order Cancellation (einzelne Orders)

**Kann NICHT:**
- Trading Mode wechseln (PAPER → LIVE)
- Risk Limits dauerhaft ändern
- Kill-Switch deaktivieren ohne Justification

---

### Stufe 2: Senior Operator / Risk Manager

**Befugnis:**
- Alles von Stufe 1
- Risk Limits temporär anpassen
- Kill-Switch deaktivieren (mit Begründung)
- Manual Trading (via API)

**Kann NICHT:**
- Trading Mode LIVE aktivieren ohne Owner Approval
- System-kritische Config ändern

---

### Stufe 3: System Owner

**Befugnis:**
- Alles von Stufe 1 + 2
- Trading Mode LIVE aktivieren
- System-kritische Config ändern
- Deployment Genehmigungen
- Emergency Shutdown

**Eskalations-Kontakt**: Siehe EMERGENCY_STOP_SOP.md

---

## Audit Trail

### Was wird protokolliert?

**Automatisch:**
- Jede Kill-Switch Aktivierung/Deaktivierung
- Jede Order Execution/Cancellation
- Jede Circuit Breaker Activation
- Service Starts/Stops/Crashes
- Config Changes (via Git)

**Manuell zu dokumentieren:**
- Grund für manuelle Eingriffe
- Operator Name/ID
- Timestamp
- Auswirkung der Aktion

---

### Audit Log Zugriff

```powershell
# Kill-Switch Events
cat .cdb_kill_switch.state

# Redis Audit Stream
docker exec cdb_redis redis-cli -a $env:REDIS_PASSWORD XRANGE audit_trail - +

# Postgres Audit Table (wenn vorhanden)
docker exec cdb_postgres psql -U claire_user -d claire_de_binare -c "SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT 20;"

# Service Logs (letzte 100 Zeilen)
docker logs cdb_risk --tail 100
docker logs cdb_execution --tail 100
docker logs cdb_core --tail 100
```

---

## Troubleshooting

### Dashboard zeigt keine Daten

**Symptom**: Alle Panels leer oder "No Data"

**Lösung**:
```powershell
# 1. Prometheus prüfen
docker ps | grep prometheus
curl http://localhost:9090/-/healthy

# 2. Grafana Datasource prüfen
# Grafana UI → Configuration → Data Sources → Prometheus → Test

# 3. Services neu starten
docker restart cdb_prometheus cdb_grafana
```

---

### Kill-Switch lässt sich nicht deaktivieren

**Symptom**: `deactivate()` returns `False`

**Lösung**: Siehe EMERGENCY_STOP_SOP.md → Troubleshooting → Kill-Switch Won't Deactivate

---

### Dashboard lädt sehr langsam

**Symptom**: Panels brauchen >10s zum Laden

**Lösung**:
```powershell
# 1. Prometheus Query Performance prüfen
# Grafana → Query Inspector → Stats

# 2. Time Range reduzieren
# Dashboard Settings → Time Range → Last 30m statt Last 3h

# 3. Refresh Interval erhöhen
# Dashboard Settings → Auto-refresh → 30s statt 10s
```

---

## Metrics Mapping

Siehe separate Datei: `docs/HITL_METRICS_MAPPING.md`

---

## Referenzen

- **Dashboard JSON**: infrastructure/monitoring/grafana/dashboards/claire_hitl_control_v1.json
- **Emergency Stop SOP**: docs/EMERGENCY_STOP_SOP.md
- **Trading Modes**: docs/TRADING_MODES.md
- **Health Contract**: docs/HEALTH_CONTRACT.md
- **Stack Lifecycle**: docs/STACK_LIFECYCLE.md
- **Issue**: #244 (HITL Control Center)

---

**Genehmigt von**: [Pending]
**Review Datum**: [Pending]
**Version**: 1.0
