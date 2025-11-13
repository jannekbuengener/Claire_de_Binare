# Backup automatisieren - Anleitung fuer Projektleiter

## Was du tun musst (5 Minuten)

### 1. Docker Desktop starten
- Doppelklick auf Docker Desktop Icon
- Warten bis gruen (Container running)

### 2. Task Scheduler einrichten
1. Windows-Taste druecken
2. "PowerShell" eingeben
3. **RECHTSKLICK** auf "Windows PowerShell"
4. "Als Administrator ausfuehren" waehlen
5. Diesen Befehl eingeben:
   ```
   C:\Users\janne\Documents\claire_de_binare\operations\backup\setup_backup_task.ps1
   ```
6. Enter druecken

### 3. Fertig!
Backup laeuft ab jetzt **automatisch jeden Tag um 3:00 Uhr**

## Backup manuell testen

Oeffne PowerShell (NICHT als Administrator):
```powershell
C:\Users\janne\Documents\claire_de_binare\operations\backup\daily_backup_full.ps1
```

## Was wird gesichert? (VOLLBACKUP!)

### 1. PostgreSQL Datenbank (~0.06 MB)
✅ Alle 10 Tabellen mit Trading-Daten:
- Signale, Orders, Trades
- Positionen, Balances
- Risk-Events, Metrics
- Health-Checks, Strategy-Params

### 2. Redis Cache (~0 MB)
✅ Aktuelle Signale und Message-Queue

### 3. KOMPLETTER Projektordner (~0.56 MB)
✅ 92 Dateien gesichert:
- Alle Python-Services (signal_engine, risk_manager)
- Komplette Dokumentation (backoffice/docs/)
- Docker-Konfiguration (docker-compose.yml, Dockerfile)
- Alle Skripte und Config-Dateien
- **AUSGENOMMEN:** logs, __pycache__, node_modules, .git, .env

### 4. Docker Volumes (~8.76 MB)
✅ Alle persistenten Container-Daten:
- PostgreSQL Volume (Datenbank-Files)
- Redis Volume (Persistence)
- Prometheus Volume (Metriken-Historie)
- Grafana Volume (Dashboard-Config)

### 5. Log-Dateien (falls vorhanden)
✅ Alle Log-Dateien als ZIP archiviert

---

## TOTAL: ~9.37 MB pro Backup

Das ist ein **ECHTES Vollbackup** - du kannst das komplette System wiederherstellen!

---

## Wo sind die Backups?

```
C:\Backups\claire_de_binare\
  ├── 20251022_0300\     (heute)
  │   ├── postgres_20251022_0300.sql       (Datenbank-Export)
  │   ├── redis_20251022_0300.rdb          (Redis-Snapshot)
  │   ├── project\                         (92 Code-Dateien)
  │   ├── logs_20251022_0300.zip          (Log-Archiv)
  │   └── docker_volumes\                  (4 Volume-Backups)
  ├── 20251021_0300\     (gestern)
  └── ...
```

## Wichtig!

- **Computer muss um 3:00 Uhr laufen**
- **Docker Desktop muss laufen**
- Alte Backups (>30 Tage) werden automatisch geloescht
- Bei 30 Tagen: ~281 MB Speicherplatz (9.37 MB × 30)

## Backup wiederherstellen (falls noetig)

**Ruf mich (Claude) im Chat!** Ich mache das fuer dich.

### Was ich dann mache:
1. Container stoppen
2. Datenbank wiederherstellen aus .sql File
3. Redis-Daten zurueckspielen
4. Docker Volumes wiederherstellen
5. Container neu starten
6. System testen

---

## Backup-Status pruefen

Im Windows Explorer oeffnen:
```
C:\Backups\claire_de_binare\
```

Du solltest sehen:
- Ordner mit Datum/Zeit (z.B. 20251022_1416)
- Jeder Ordner ~9-10 MB gross
- Mindestens 1 neues Backup pro Tag

---

**Du musst nichts coden. Nur PowerShell-Befehle kopieren und Enter druecken.**

