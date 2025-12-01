# Paper Trading 14-Tage Test - Start-Anleitung

**Claire de Binare - Paper Trading Runner**

Datum: 2025-11-26
Status: ✅ Ready to Launch

---

## Voraussetzungen

### 1. Gmail App-Password einrichten

Email-Alerts benötigen ein Gmail App-Password (NICHT dein normales Passwort!):

1. Gehe zu: https://myaccount.google.com/security
2. **2-Step Verification** aktivieren (falls noch nicht)
3. **App Passwords** → Generate
4. Name: "Claire Trading Bot"
5. Kopiere das generierte 16-Zeichen-Passwort
6. Füge es in `.env` ein:
   ```bash
   ALERT_EMAIL_PASSWORD=xxxx xxxx xxxx xxxx
   ```

### 2. Email-Adressen in .env setzen

```bash
# .env Datei bearbeiten
ALERT_EMAIL_FROM=deine-email@gmail.com
ALERT_EMAIL_TO=deine-email@gmail.com
```

### 3. Task Scheduler für stündliche Backups einrichten

**Option A: Automatisches Setup** (empfohlen)

```powershell
# Als Administrator in PowerShell ausführen:
schtasks /create `
  /tn "Claire_Hourly_Backup" `
  /tr "powershell.exe -ExecutionPolicy Bypass -File C:\Users\janne\Documents\GitHub\Workspaces\Claire_de_Binare\backoffice\scripts\backup_postgres.ps1" `
  /sc hourly `
  /st 00:00 `
  /ru SYSTEM

# Validierung:
schtasks /query /tn "Claire_Hourly_Backup" /v
```

**Option B: Manuelle Einrichtung via GUI**

1. **Task Scheduler** öffnen (`taskschd.msc`)
2. **Create Task** (Aufgabe erstellen)
3. **General Tab**:
   - Name: `Claire_Hourly_Backup`
   - Description: `Stündliche PostgreSQL Backups für Claire de Binare`
   - Run whether user is logged on or not: ☑
   - Run with highest privileges: ☑
4. **Triggers Tab**:
   - New Trigger
   - Begin: On a schedule
   - Settings: Daily, repeat every **1 hour**, for a duration of **1 day**
   - Start time: **00:00:00** (Mitternacht)
5. **Actions Tab**:
   - New Action
   - Program: `powershell.exe`
   - Arguments: `-ExecutionPolicy Bypass -File "C:\Users\janne\Documents\GitHub\Workspaces\Claire_de_Binare\backoffice\scripts\backup_postgres.ps1"`
6. **Conditions Tab**:
   - Start only if computer is on AC power: ☐ (DEAKTIVIEREN)
7. **Settings Tab**:
   - Allow task to be run on demand: ☑
   - If task fails, restart every: 10 minutes, up to 3 times
8. **OK** → Administrator-Passwort eingeben

**Test-Backup manuell ausführen**:

```powershell
powershell.exe -ExecutionPolicy Bypass -File .\backoffice\scripts\backup_postgres.ps1
```

Erwartete Ausgabe:
```
✅ Backup directory ready: F:\Claire_Backups
✅ Sufficient disk space (XXX GB available)
✅ Docker OK - cdb_postgres running
✅ Backup created: XX.XX MB
✅ Compressed: XX.XX MB
✅ Backup completed successfully!
```

---

## Start-Prozedur

### Schritt 1: Docker-Stack starten

```bash
# Alle Container starten
docker compose up -d

# Warte 30s bis alle Services hochgefahren sind
timeout /t 30

# Status prüfen
docker compose ps
```

Erwartung: **10/10 Container** running (9 bestehende + 1 cdb_paper_runner)

### Schritt 2: Systemcheck durchführen

```bash
# Via Makefile (Linux/Mac)
make systemcheck

# Oder direkt (Windows)
python backoffice/scripts/systemcheck.py
```

Erwartung: **Alle Checks ✅** (7/7 passed)

Falls ein Check fehlschlägt:
- ENV-Variablen fehlen → `.env` prüfen
- Docker-Container unhealthy → Logs prüfen: `docker compose logs <service>`
- PostgreSQL Schema fehlt → DB-Init-Script laufen lassen
- Disk Space < 30 GB → Platz freimachen (F:\ Laufwerk!)

### Schritt 3: Paper Trading Runner starten

```bash
# Via Makefile (empfohlen)
make paper-trading-start

# Oder manuell
docker compose up -d cdb_paper_runner
```

### Schritt 4: Validierung

**Health-Check**:
```bash
curl http://localhost:8004/health
```

Erwartete Antwort:
```json
{
  "status": "ok",
  "service": "paper_trading_runner",
  "uptime_seconds": 45,
  "events_logged": 0,
  "last_health_check": "2025-11-26T10:00:00"
}
```

**Container-Logs verfolgen**:
```bash
docker compose logs -f cdb_paper_runner
```

Erwartete Log-Einträge:
```
✅ Redis connected
✅ PostgreSQL connected
📡 Subscribed to Redis channels: market_data, signals, orders, order_results, alerts
🚀 Paper Trading Runner started
🌐 Health endpoint: http://localhost:8004/health
```

**Email-Alert testen** (optional):
```bash
# Python-Console:
python
>>> from services.cdb_paper_runner.email_alerter import EmailAlerter
>>> alerter = EmailAlerter()
>>> alerter.test_connection()
```

Erwartung: Email sollte innerhalb 1 Minute ankommen

### Schritt 5: Monitoring öffnen

**Grafana Dashboard**:
- URL: http://localhost:3000
- Login: `admin` / (Passwort aus `.env`)
- Dashboard: Noch nicht erstellt (optional - kann später hinzugefügt werden)

**Prometheus Metrics**:
- URL: http://localhost:19090
- Targets: http://localhost:19090/targets

---

## Tägliche Routine (5 Min/Tag)

### Morgens (z.B. 09:00 Uhr)

```bash
# Daily-Check ausführen
python backoffice/scripts/daily_check.py
```

**Prüfe Report**:
- Gespeichert in: `logs/daily_reports/report_YYYYMMDD.md`
- Portfolio Equity > $100,000 ?
- Daily P&L positiv?
- Open Positions < 3 ?
- Disk Space > 30 GB ?
- Backups in letzten 24h vorhanden?

**Container-Status**:
```bash
docker compose ps
```

Alle 10 Container sollten "healthy" sein.

**Logs prüfen** (bei Bedarf):
```bash
# Paper Trading Runner Logs
docker compose logs cdb_paper_runner --tail=50

# Risk Manager Logs (falls Risk-Limit Hits)
docker compose logs cdb_risk --tail=50

# Execution Service Logs
docker compose logs cdb_execution --tail=50
```

---

## Bei Problemen

### Container crasht

```bash
# Container neu starten
docker compose restart cdb_paper_runner

# Logs prüfen
docker compose logs cdb_paper_runner --tail=100
```

### Keine Events werden geloggt

**Prüfen**:
1. Sind andere Services (cdb_ws, cdb_core) aktiv?
   ```bash
   curl http://localhost:8001/health  # cdb_core
   ```
2. Redis Pub/Sub funktioniert?
   ```bash
   docker exec cdb_redis redis-cli -a $REDIS_PASSWORD PING
   ```

### Email-Alerts kommen nicht an

**Prüfen**:
1. `.env` Variablen korrekt?
   - `ALERT_EMAIL_FROM`
   - `ALERT_EMAIL_TO`
   - `ALERT_EMAIL_PASSWORD` (Gmail App-Password!)
2. Gmail-Account: 2-Step-Verification aktiv?
3. App-Password erstellt?
4. Container-Logs:
   ```bash
   docker compose logs cdb_paper_runner | grep "Email"
   ```

### Backups fehlen

**Manuelles Backup**:
```powershell
powershell.exe -ExecutionPolicy Bypass -File .\backoffice\scripts\backup_postgres.ps1
```

**Task Scheduler prüfen**:
```powershell
schtasks /query /tn "Claire_Hourly_Backup" /v
```

**Letzte Task-Ausführung**:
```powershell
Get-ScheduledTask -TaskName "Claire_Hourly_Backup" | Get-ScheduledTaskInfo
```

---

## Test-Ende (Tag 15)

### Stoppen

```bash
# Paper Trading Runner stoppen
docker compose stop cdb_paper_runner

# Alle Container stoppen (optional)
docker compose down
```

### Final-Report

```bash
# Letzter Daily-Check
python backoffice/scripts/daily_check.py

# Letzte Statistiken
python backoffice/scripts/query_analytics.py --portfolio-summary
python backoffice/scripts/query_analytics.py --trade-statistics
```

### Daten exportieren

```bash
# CSV-Export (manuell via query_analytics.py oder direkt aus PostgreSQL)
docker exec cdb_postgres psql -U claire_user -d claire_de_binare -c "\copy trades TO '/tmp/trades_export.csv' CSV HEADER"
docker cp cdb_postgres:/tmp/trades_export.csv ./trades_14day.csv
```

### Final Backup

```powershell
# Finales Backup mit Zeitstempel
powershell.exe -ExecutionPolicy Bypass -File .\backoffice\scripts\backup_postgres.ps1

# Backup-Verzeichnis: F:\Claire_Backups\
# 336 stündliche Backups (~17 GB)
```

---

## Success-Kriterien

**Mindestanforderungen** (✅ = bestanden):
- [ ] System läuft 14 Tage durch (Uptime > 95%)
- [ ] Keine kritischen Fehler (Crashes, Data-Loss)
- [ ] Min. 100 Signals generiert
- [ ] Min. 10 Trades ausgeführt
- [ ] Risk-Engine blockiert 0 ungültige Trades
- [ ] PostgreSQL Persistierung 100% stabil
- [ ] Daily P&L korrekt berechnet
- [ ] 336 stündliche Backups vorhanden

**Nice-to-Have**:
- [ ] Win-Rate > 50%
- [ ] Max Drawdown < 5%
- [ ] Sharpe-Ratio > 1.0
- [ ] Email-Alerts bei allen Critical Events

---

## Kontakt & Support

**Bei Fragen oder Problemen**:
- Logs prüfen: `docker compose logs <service>`
- Systemcheck: `python backoffice/scripts/systemcheck.py`
- Daily-Check: `python backoffice/scripts/daily_check.py`
- Grafana: http://localhost:3000
- Health-Endpoints: http://localhost:800X/health

**Dokumentation**:
- Vollständiger Plan: `~/.claude/plans/goofy-meandering-fog.md`
- CLAUDE.md: Projekt-Übersicht & Standards
- PROJECT_STATUS.md: Live-Status

---

**Viel Erfolg mit dem 14-Tage Paper Trading Test! 🚀**
