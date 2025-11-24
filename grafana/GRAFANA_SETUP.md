# Grafana Setup Guide - Claire de Binare Paper Trading

**Version**: 1.0
**Datum**: 2025-11-23
**Zweck**: Monitoring für 7-Tage Paper-Trading Run

---

## 📋 Inhaltsverzeichnis

1. [Quick Start](#1-quick-start)
2. [PostgreSQL Datasource konfigurieren](#2-postgresql-datasource-konfigurieren)
3. [Dashboard importieren](#3-dashboard-importieren)
4. [Alert Rules einrichten](#4-alert-rules-einrichten)
5. [Troubleshooting](#5-troubleshooting)

---

## 1. Quick Start

### 1.1 Grafana öffnen

```bash
# 1. Container starten (falls nicht läuft)
docker compose up -d cdb_grafana

# 2. Browser öffnen
http://localhost:3000
```

**Login-Daten**:
- **Username**: `admin`
- **Password**: Aus `.env` → `GRAFANA_PASSWORD` (Standard: siehe `.env.example`)

### 1.2 Übersicht der 9 Dashboard-Panels

| Panel | Typ | Zweck | Threshold |
|-------|-----|-------|-----------|
| 1. Equity Curve | Time Series | Kapitalverlauf über Zeit | - |
| 2. Daily Drawdown % | Gauge | Täglicher Drawdown | 🟡 3% / 🔴 4.5% |
| 3. Total Exposure % | Gauge | Gesamt-Exposure | 🟡 20% / 🔴 28% |
| 4. Open Positions | Stat | Anzahl offene Positionen | 🟡 2 / 🔴 3 |
| 5. Total PnL | Stat | Gesamt-Profit/Loss | 🔴 < 0 / 🟢 ≥ 0 |
| 6. Trades per Day | Bar Chart | Trades pro Tag | - |
| 7. Win Rate % | Gauge | Gewinn-Rate | 🔴 < 45% / 🟢 ≥ 55% |
| 8. Recent Trades | Table | Letzte 50 Trades | - |
| 9. Daily PnL | Bar Chart | Tägl. Profit/Loss | - |

---

## 2. PostgreSQL Datasource konfigurieren

### 2.1 Datasource hinzufügen

**Navigation**: `Configuration (⚙️) → Data sources → Add data source`

**Wähle**: PostgreSQL

**Konfiguration**:

```yaml
Name: PostgreSQL-Claire
Host: cdb_postgres:5432
Database: claire_de_binare
User: claire_user
Password: <AUS .env: POSTGRES_PASSWORD>
SSL Mode: disable
PostgreSQL details:
  Version: 16
  TimescaleDB: false
```

**Erweiterte Einstellungen**:
```yaml
Max open connections: 10
Max idle connections: 2
Max connection lifetime: 14400  # 4 Stunden
```

**Test & Save**:
- Klick auf **"Save & test"**
- Erwartung: ✅ "Database Connection OK"

### 2.2 UID anpassen (wichtig!)

Nach dem Speichern:
1. Gehe zurück zu **Settings** der Datasource
2. Kopiere die **UID** (z. B. `abc123xyz`)
3. Öffne `grafana/dashboards/claire-paper-trading.json`
4. Suche & Ersetze:
   ```json
   "uid": "postgres-uid"
   ```
   mit
   ```json
   "uid": "abc123xyz"  // Deine echte UID
   ```
5. Speichere die Datei

---

## 3. Dashboard importieren

### 3.1 Import via UI

**Navigation**: `Dashboards (+) → Import`

**Variante A: JSON direkt**:
1. Klick auf **"Upload JSON file"**
2. Wähle: `grafana/dashboards/claire-paper-trading.json`
3. Klick **"Load"**
4. Wähle Datasource: **PostgreSQL-Claire**
5. Klick **"Import"**

**Variante B: JSON kopieren**:
1. Klick auf **"Import via panel json"**
2. Öffne `claire-paper-trading.json` in Editor
3. Kopiere gesamten JSON-Inhalt
4. Paste in Textfeld
5. Klick **"Load"** → **"Import"**

### 3.2 Dashboard-URL

Nach Import:
```
http://localhost:3000/d/claire-paper-trading/claire-de-binare-paper-trading
```

**Bookmark** diese URL für schnellen Zugriff!

### 3.3 Auto-Refresh einstellen

Oben rechts:
- Klick auf Refresh-Icon (🔄)
- Wähle: **10 Sekunden**
- Dashboard aktualisiert sich nun alle 10s automatisch

### 3.4 Time Range anpassen

Oben rechts:
- Klick auf Time-Range (z. B. "Last 7 days")
- Für Paper-Run:
  - **From**: `now-7d` (letzte 7 Tage)
  - **To**: `now`
  - **Timezone**: `UTC`

---

## 4. Alert Rules einrichten

### 4.1 Alert Channels konfigurieren

**Navigation**: `Alerting (🔔) → Notification channels → New channel`

**Kanal 1: Email** (optional):
```yaml
Name: Claire-Alerts-Email
Type: Email
Email addresses: <DEINE EMAIL>
Send on all alerts: ✅
Include image: ✅
```

**Kanal 2: Webhook** (optional):
```yaml
Name: Claire-Alerts-Webhook
Type: Webhook
URL: http://localhost:8080/alerts  # Falls Webhook-Service existiert
HTTP Method: POST
```

### 4.2 Alert Rules erstellen

#### Alert 1: Daily Drawdown > 4.5%

**Panel**: Daily Drawdown %

**Alert Config**:
```yaml
Name: High Daily Drawdown
Evaluate every: 1m
For: 2m

Conditions:
  WHEN: last()
  OF: query(A, 1m, now)
  IS ABOVE: 4.5

No Data & Error Handling:
  If no data or all values are null: SET STATE TO NoData
  If execution error or timeout: SET STATE TO Alerting

Notifications:
  Send to: Claire-Alerts-Email
  Message: ⚠️ Daily Drawdown exceeds 4.5%! Current: ${value}%
```

**Schritte zum Erstellen**:
1. Öffne Dashboard → Panel "Daily Drawdown %"
2. Edit (Stift-Icon)
3. Tab: **Alert**
4. **Create Alert**
5. Eingaben wie oben
6. **Save** (Disketten-Icon oben)

#### Alert 2: Total Exposure > 28%

**Panel**: Total Exposure %

**Alert Config**:
```yaml
Name: High Total Exposure
Evaluate every: 1m
For: 2m

Conditions:
  WHEN: last()
  OF: query(A, 1m, now)
  IS ABOVE: 28

Notifications:
  Send to: Claire-Alerts-Email
  Message: ⚠️ Total Exposure exceeds 28%! Current: ${value}%
```

#### Alert 3: Open Positions > 2

**Panel**: Open Positions

**Alert Config**:
```yaml
Name: Too Many Open Positions
Evaluate every: 30s
For: 1m

Conditions:
  WHEN: last()
  OF: query(A, 1m, now)
  IS ABOVE: 2

Notifications:
  Send to: Claire-Alerts-Email
  Message: ⚠️ More than 2 open positions! Current: ${value}
```

#### Alert 4: No New Signals > 1h

**Erstelle neues Panel** (optional):

**Panel Config**:
```sql
SELECT
  EXTRACT(EPOCH FROM (NOW() - MAX(timestamp))) / 60 AS "Minutes Since Last Signal"
FROM signals
```

**Alert Config**:
```yaml
Name: Signal Inactivity
Evaluate every: 5m
For: 10m

Conditions:
  WHEN: last()
  OF: query(A, 5m, now)
  IS ABOVE: 60  # 60 Minuten

Notifications:
  Send to: Claire-Alerts-Email
  Message: ⚠️ No signals received for 1 hour!
```

### 4.3 Alert-Status prüfen

**Navigation**: `Alerting (🔔) → Alert Rules`

**Erwartung**:
- Alle Rules: Status **OK** (grün)
- Falls **ALERTING** (rot): Sofort reagieren (siehe RUNBOOK_PAPER_TRADING.md)

---

## 5. Troubleshooting

### 5.1 "Database Connection Failed"

**Problem**: Grafana kann nicht zu PostgreSQL verbinden

**Lösung**:
```bash
# 1. PostgreSQL läuft?
docker compose ps cdb_postgres
# Erwartung: "healthy"

# 2. Von Grafana-Container aus testen
docker exec -it cdb_grafana ping cdb_postgres
# Erwartung: Ping erfolgreich

# 3. Credentials prüfen
cat .env | grep POSTGRES_PASSWORD
# Wert muss mit Datasource-Config übereinstimmen

# 4. PostgreSQL Logs prüfen
docker compose logs cdb_postgres | grep ERROR
```

**Häufige Ursachen**:
- PostgreSQL-Container nicht gestartet
- Falsches Passwort in Datasource
- Host `cdb_postgres` statt `localhost` vergessen

### 5.2 "No Data" in Panels

**Problem**: Panels zeigen "No data" trotz laufendem System

**Checkliste**:
```bash
# 1. Daten vorhanden?
docker exec -it cdb_postgres psql -U claire_user -d claire_de_binare -c "SELECT COUNT(*) FROM signals;"
# Erwartung: > 0

# 2. Time Range korrekt?
# Dashboard: Oben rechts Time Range prüfen → z. B. "Last 7 days"

# 3. Query testen
# Panel → Edit → Query Inspector → Refresh
# Fehler im Query-Output?

# 4. Datasource UID korrekt?
# Panel → Edit → Query → Datasource sollte "PostgreSQL-Claire" sein
```

**Query manuell testen**:
```sql
-- In PostgreSQL:
SELECT
  timestamp AS "time",
  equity_usd AS "Equity"
FROM portfolio_snapshots
WHERE timestamp > NOW() - INTERVAL '7 days'
ORDER BY timestamp ASC;

-- Wenn leer: Keine Daten im Zeitraum!
```

### 5.3 Panels laden langsam

**Problem**: Dashboard braucht > 5s zum Laden

**Optimierungen**:

**1. Query-Optimierung**:
```sql
-- ❌ Langsam (Full Table Scan)
SELECT * FROM trades WHERE timestamp > NOW() - INTERVAL '7 days';

-- ✅ Schneller (mit Index)
SELECT timestamp, pnl FROM trades
WHERE timestamp > NOW() - INTERVAL '7 days'
ORDER BY timestamp DESC
LIMIT 1000;
```

**2. Indexes erstellen**:
```sql
-- In PostgreSQL:
CREATE INDEX IF NOT EXISTS idx_signals_timestamp ON signals(timestamp);
CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp);
CREATE INDEX IF NOT EXISTS idx_portfolio_timestamp ON portfolio_snapshots(timestamp);
CREATE INDEX IF NOT EXISTS idx_positions_status ON positions(status);
```

**3. Auto-Refresh reduzieren**:
- Statt 10s → 30s oder 1min
- Dashboard → Refresh-Icon → 30s

### 5.4 Alerts feuern nicht

**Problem**: Alert Rule konfiguriert, aber keine Notification

**Checkliste**:

**1. Alert State prüfen**:
```
Alerting → Alert Rules → "High Daily Drawdown"
Status: OK / PENDING / ALERTING?
```

**2. Condition erfüllt?**:
```sql
-- Manuell prüfen:
SELECT
  ABS((MIN(equity_usd) - (SELECT equity_usd FROM portfolio_snapshots WHERE DATE(timestamp) = CURRENT_DATE ORDER BY timestamp ASC LIMIT 1)) / (SELECT equity_usd FROM portfolio_snapshots WHERE DATE(timestamp) = CURRENT_DATE ORDER BY timestamp ASC LIMIT 1) * 100) AS daily_drawdown
FROM portfolio_snapshots
WHERE DATE(timestamp) = CURRENT_DATE;

-- Wenn < 4.5% → Alert feuert nicht (korrekt)
```

**3. Notification Channel aktiv?**:
```
Alerting → Notification channels → "Claire-Alerts-Email"
Test: "Send Test"
Email erhalten? → Channel funktioniert
```

**4. Alert "For" Dauer abwarten**:
```yaml
# Alert Config:
For: 2m  # Bedeutet: Condition muss 2 Min lang erfüllt sein

# Wenn Drawdown nur kurz > 4.5% war → Alert feuert NICHT
```

### 5.5 Grafana Login vergessen

**Problem**: Admin-Passwort vergessen

**Lösung**:
```bash
# 1. Container neu starten mit Reset
docker compose stop cdb_grafana
docker compose up -d cdb_grafana

# 2. Im Container: Admin-Passwort zurücksetzen
docker exec -it cdb_grafana grafana-cli admin reset-admin-password <NEUES_PASSWORT>

# 3. Erneut einloggen
# Username: admin
# Password: <NEUES_PASSWORT>

# 4. In .env aktualisieren
GRAFANA_PASSWORD=<NEUES_PASSWORT>
```

---

## 6. Best Practices

### 6.1 Dashboard-Varianten

**Für Daily Review**:
- Time Range: `Last 24 hours`
- Refresh: `10s`
- Fokus auf: Daily Drawdown, Total Exposure, Recent Trades

**Für Wochen-Übersicht**:
- Time Range: `Last 7 days`
- Refresh: `1m`
- Fokus auf: Equity Curve, Daily PnL, Win Rate

**Für Incident-Response**:
- Time Range: `Last 1 hour`
- Refresh: `5s`
- Fokus auf: Alle Panels, besonders Alerts

### 6.2 Snapshot für Reports

**Navigation**: `Dashboard → Share (Icon oben) → Snapshot`

**Konfiguration**:
```yaml
Snapshot name: Paper-Run Day 3 Evening Review
Expire: Never
Timeout: 60 seconds
```

**Export to PNG**:
```yaml
Dashboard → Share → Link → Render image
Width: 1920
Height: 1080
Save as: reports/day_3_dashboard.png
```

**Verwendung**:
- Daily Reports
- Post-Run Analysis
- Incident Documentation

### 6.3 Dashboard-Backup

**Regelmäßig exportieren**:
```bash
# 1. Dashboard öffnen
http://localhost:3000/d/claire-paper-trading

# 2. Settings (Zahnrad-Icon oben)
Dashboard Settings → JSON Model

# 3. JSON kopieren
# Speichern als: backups/dashboard_backup_$(date +%Y%m%d).json
```

**Automatisches Backup** (optional):
```bash
# Script: backup_grafana_dashboard.sh
#!/bin/bash
curl -u admin:$GRAFANA_PASSWORD \
  http://localhost:3000/api/dashboards/uid/claire-paper-trading \
  | jq '.dashboard' \
  > backups/dashboard_backup_$(date +%Y%m%d).json
```

---

## 7. Anhang

### 7.1 Panel SQL Queries (Referenz)

**Equity Curve**:
```sql
SELECT
  timestamp AS "time",
  equity_usd AS "Equity"
FROM portfolio_snapshots
WHERE $__timeFilter(timestamp)
ORDER BY timestamp ASC
```

**Daily Drawdown**:
```sql
WITH today_start AS (
  SELECT equity_usd AS start_equity
  FROM portfolio_snapshots
  WHERE DATE(timestamp) = CURRENT_DATE
  ORDER BY timestamp ASC
  LIMIT 1
),
today_min AS (
  SELECT MIN(equity_usd) AS min_equity
  FROM portfolio_snapshots
  WHERE DATE(timestamp) = CURRENT_DATE
)
SELECT
  ABS((today_min.min_equity - today_start.start_equity) / today_start.start_equity * 100) AS "Daily Drawdown"
FROM today_start, today_min
```

**Total Exposure**:
```sql
SELECT
  total_exposure_pct AS "Total Exposure"
FROM portfolio_snapshots
ORDER BY timestamp DESC
LIMIT 1
```

**Win Rate**:
```sql
SELECT
  COUNT(CASE WHEN pnl > 0 THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0) AS "Win Rate"
FROM trades
WHERE $__timeFilter(timestamp)
```

### 7.2 Nützliche Links

- **Grafana Docs**: https://grafana.com/docs/grafana/latest/
- **PostgreSQL Datasource**: https://grafana.com/docs/grafana/latest/datasources/postgres/
- **Alert Rules**: https://grafana.com/docs/grafana/latest/alerting/
- **Panel Types**: https://grafana.com/docs/grafana/latest/panels/

---

**Ende des Setup-Guides**

**Version**: 1.0
**Letzte Aktualisierung**: 2025-11-23
**Nächster Review**: Nach erstem Paper-Run
