# Backup Automation Runbook

**Scope:** Scheduled local backups to `F:\Claire_Backups`
**Issue:** #1175

## Übersicht

- `infrastructure/scripts/backup_all.ps1` erstellt Postgres- und Redis-Backups als ZIP unter `F:\Claire_Backups`.
- `infrastructure/scripts/setup_backup_task.ps1` registriert den Windows Task `Claire_Hourly_Backup`.
- `infrastructure/scripts/backup_health_check.ps1` prüft auf ein aktuelles Archiv (`exit 0 = PASS`, `exit 1 = FAIL`).
- `infrastructure/scripts/daily_check.py` meldet in Section 6, ob in den letzten 24 Stunden ein Backup vorhanden war.

## Einmaliges Setup

Als Administrator ausführen:

```powershell
cd D:\Dev\Workspaces\Repos\Claire_de_Binare
.\infrastructure\scripts\setup_backup_task.ps1
```

Der Task `Claire_Hourly_Backup` läuft stündlich ab Mitternacht als `SYSTEM`, nutzt standardmäßig `F:\Claire_Backups` und bereinigt Archive älter als 14 Tage automatisch.

## Manueller Test

```powershell
Start-ScheduledTask -TaskName "Claire_Hourly_Backup"
Start-Sleep -Seconds 30
.\infrastructure\scripts\backup_health_check.ps1
```

Erwartet wird `PASS  Latest backup: ...`. Bei `FAIL` → Task-History und Failure Modes prüfen.

## Verifikation

```powershell
Get-ScheduledTask -TaskName "Claire_Hourly_Backup" | Select-Object State, LastRunTime, LastTaskResult
dir F:\Claire_Backups\cdb_backup_*.zip | Sort-Object LastWriteTime -Descending | Select-Object -First 3
```

`LastTaskResult = 0` bedeutet erfolgreicher Lauf.
Im Task Scheduler: `Task Scheduler Library → Claire_Hourly_Backup → History`.

## Failure Modes

- `F:\Claire_Backups` nicht erreichbar → externes Laufwerk prüfen und Task erneut starten.
- `Docker is not running` → Docker starten und Task erneut auslösen.
- `cdb_postgres` oder `cdb_redis` läuft nicht → benötigte Container über den kanonischen lokalen Startpfad hochfahren, dann Task erneut starten.
- Task fehlt in `Get-ScheduledTask` → `setup_backup_task.ps1` erneut als Administrator ausführen.

## Daily Check

`infrastructure/scripts/daily_check.py` prüft in Section 6, ob in den letzten 24 Stunden mindestens ein ZIP-Backup unter `F:\Claire_Backups` erstellt wurde.

## Retention

- Standard-Retention: 14 Tage
- Bereinigung erfolgt automatisch in `backup_all.ps1`
- Kein manuelles Cleanup erforderlich
