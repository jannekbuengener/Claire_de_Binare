---
status: archived
source: backoffice/docs/7D_PAPER_TRADING_TEST.md
## migrated_to: backoffice/PROJECT_STATUS.md

# 7-Tage Paper-Trading Test - Anleitung

**Start**: 2025-10-26 23:00 UTC (bereit zum Start)
**Ende**: 2025-11-02 23:00 UTC
**Status**: 🟢 Bereit zur Durchführung

---

## 🎯 Ziel

System-Stabilität über 7 Tage kontinuierlichen Betriebs validieren. Keine Code-Änderungen, kein Restart – nur Monitoring und Datensammlung.

---

## ✅ Voraussetzungen (alle erfüllt)

- [x] Alle 9 Container running & healthy
- [x] Prometheus Scraping aktiv (4/4 Targets)
- [x] Grafana Dashboard konfiguriert
- [x] Alert-Rules aktiv
- [x] Database-Persistenz funktioniert
- [x] docker-compose.yml validiert

---

## 🚀 Test starten

### 1. Finale Pre-Flight Checks

```powershell
## Container-Status prüfen
docker compose ps

## Erwartung: 9/9 running, 9/9 healthy

## Prometheus Targets prüfen
curl -s http://localhost:9090/api/v1/targets | Select-String '"health":"up"'

## Erwartung: 4 Matches (signal_engine, risk_manager, execution_service, prometheus)

## Grafana Dashboard öffnen
Start-Process "http://localhost:3000/d/ea75044d-8038-4e04-bd15-87a1858f4559"
```

### 2. Baseline-Metriken notieren

**Datum/Zeit**: 2025-10-26 23:00 UTC

```powershell
## In Datei speichern
@"
=== BASELINE METRICS (Start) ===
Timestamp: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss UTC')
Containers: $(docker compose ps --format '{{.Name}}:{{.Status}}' | Out-String)
Prometheus Targets: $(curl -s http://localhost:9090/api/v1/targets | ConvertFrom-Json | Select-Object -ExpandProperty data | Select-Object -ExpandProperty activeTargets | Measure-Object | Select-Object -ExpandProperty Count)
"@ | Out-File "logs/7d-test-baseline.txt"
```

### 3. Test offiziell starten

```powershell
## Marker setzen
Write-Host "`n7-TAGE TEST GESTARTET: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss UTC')`n" -ForegroundColor Green
```

**System läuft nun unbeaufsichtigt für 7 Tage.**

---

## 📊 Tägliche Checks (5 Min/Tag)

### Tägliche Routine (morgens/abends)

```powershell
## Quick Health Check
docker compose ps --format "table {{.Name}}\t{{.Status}}"

## Erwartung: Alle "Up X hours/days (healthy)"

## Grafana Dashboard öffnen und prüfen:
## - Container Health: Alle grün?
## - Orders Received: Stabil?
## - Risk Blocks: Normal?
## - Keine roten Alerts?
```

### Wenn alles grün → nichts tun

Das ist der Sinn des Tests: **System soll von selbst laufen.**

---

## 🚨 Was tun bei Problemen?

### Container Down

```powershell
## Logs prüfen
docker compose logs <container-name> --tail 100

## In Datei speichern
docker compose logs <container-name> --tail 500 > "logs/incident-$(Get-Date -Format 'yyyyMMdd-HHmmss').txt"

## Container restart (nur bei kritischem Fehler)
docker compose restart <container-name>

## WICHTIG: Incident dokumentieren in logs/7d-test-incidents.txt
```

### Hohe Order-Rejection

- **Normal**: <10% Rejection-Rate
- **Warnung**: 10-25% → Beobachten
- **Kritisch**: >25% → Risk-Manager Logs prüfen

```powershell
docker compose logs risk_manager --tail 200 | Select-String "REJECT"
```

### Grafana Alerts

- Alert-Dashboard öffnen: http://localhost:3000/d/dd0cd515-b6ae-4510-9093-a705ed1d9608
- Rote Alerts → Logs des betroffenen Services prüfen
- Alert-Details notieren (Zeitstempel, Service, Grund)

---

## 📝 Logging während des Tests

### Automatisches Logging (bereits aktiv)

- **Prometheus**: Speichert alle Metriken (15s Intervall)
- **Grafana**: Visualisiert Timeline
- **Docker Logs**: Persistent im Volume

### Manuelles Daily-Log (optional)

```powershell
## Täglicher Snapshot (ca. 2 Min)
$day = (Get-Date).DayOfWeek
@"
=== DAY $day SNAPSHOT ===
Date: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss UTC')
Uptime: $(docker inspect cdb_execution --format '{{.State.StartedAt}}')
Health: $(docker compose ps --format '{{.Name}}:{{.Status}}' | Out-String)
Orders: $(curl -s http://localhost:8003/status | ConvertFrom-Json | Select-Object -ExpandProperty stats | Out-String)
Prometheus Targets: $(curl -s http://localhost:9090/api/v1/targets | ConvertFrom-Json | Select-Object -ExpandProperty data | Select-Object -ExpandProperty activeTargets | Where-Object {$_ .health -eq 'up'} | Measure-Object | Select-Object -ExpandProperty Count)/4
"@ | Out-File "logs/7d-test-day-$day.txt"
```

---

## 🏁 Test beenden (nach 7 Tagen)

### 1. Finale Metriken sammeln

```powershell
## Endzeit notieren
$endTime = Get-Date -Format 'yyyy-MM-dd HH:mm:ss UTC'

## Status-Report generieren
@"
=== 7-TAGE TEST ABGESCHLOSSEN ===
Start:  2025-10-26 23:00 UTC
Ende:   $endTime
Dauer:  7 Tage

CONTAINER STATUS:
$(docker compose ps --format 'table {{.Name}}\t{{.Status}}\t{{.Ports}}')

EXECUTION SERVICE STATS:
$(curl -s http://localhost:8003/status | ConvertFrom-Json | ConvertTo-Json -Depth 5)

PROMETHEUS TARGETS:
$(curl -s http://localhost:9090/api/v1/targets | ConvertFrom-Json | Select-Object -ExpandProperty data | Select-Object -ExpandProperty activeTargets | Select-Object job,health,lastError | Out-String)
"@ | Out-File "logs/7d-test-final-report.txt"
```

### 2. Grafana Export

```powershell
## Dashboard-Screenshots speichern (manuell)
## Main Dashboard → Share → Export → Save JSON
## Alerts Dashboard → Share → Export → Save JSON
```

### 3. Logs archivieren

```powershell
## Alle relevanten Logs sichern
$archive = "7d-test-archive-$(Get-Date -Format 'yyyyMMdd').zip"
Compress-Archive -Path "logs/*" -DestinationPath $archive
Write-Host "Archive erstellt: $archive" -ForegroundColor Green
```

---

## 📈 Erfolgs-Kriterien

| Kriterium | Ziel | Status |
|-----------|------|--------|
| Uptime | >99% (max 1.68h Downtime) | ⏳ Läuft |
| Container Restarts | <3 gesamt | ⏳ Läuft |
| Kritische Errors | 0 | ⏳ Läuft |
| Orders verarbeitet | >0 (wenn Signale da) | ⏳ Läuft |
| Prometheus Scraping | 100% Success-Rate | ⏳ Läuft |
| Database Integrity | Keine Corruptions | ⏳ Läuft |

**Test bestanden wenn**: Alle Kriterien erfüllt ✅

---

## 🔄 Nach dem Test

### 1. Analyse (ca. 2h)

- Logs durchsehen auf Patterns/Anomalien
- Grafana-Timeline analysieren
- Performance-Metriken bewerten
- Incident-Report schreiben (falls Vorfälle)

### 2. Lessons Learned

- Was lief gut?
- Was muss verbessert werden?
- Welche Alerts waren hilfreich?
- Welche Metriken fehlen?

### 3. Entscheidung: Live-Trading

**Wenn Test erfolgreich** → Phase 8: Live-Trading Vorbereitung
**Wenn Issues** → Fixes implementieren, erneuter Test

---

## 📚 Dokumentation

- **Baseline**: `logs/7d-test-baseline.txt`
- **Daily Logs**: `logs/7d-test-day-*.txt`
- **Incidents**: `logs/7d-test-incidents.txt`
- **Final Report**: `logs/7d-test-final-report.txt`
- **Archive**: `7d-test-archive-YYYYMMDD.zip`

---

## 🆘 Support

Bei Fragen oder unerwarteten Problemen:

1. Logs prüfen (siehe oben)
2. Grafana Alert-Dashboard checken
3. Incident dokumentieren
4. System stabilisieren (Restart falls nötig)
5. Test fortsetzen

**Wichtig**: Nicht aufgeben! Auch Incidents sind wertvolle Daten für Stabilisierung.

---

**Viel Erfolg beim 7-Tage Test! 🚀**

---

**Erstellt**: 2025-10-26
**Maintainer**: Claude (IT-Chef)
**Review**: Gordon (Server-Admin)