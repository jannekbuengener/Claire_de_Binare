# Backup Automation Runbook

**Scope:** Scheduled local backups to `F:\Claire_Backups` plus optional SurrealDB sidecar capture
**Issue:** #1175

## Übersicht

- `infrastructure/scripts/backup_all.ps1` erstellt Postgres- und Redis-Backups als ZIP unter `F:\Claire_Backups`.
- Optional kann `backup_all.ps1 -IncludeSurrealDB` den lokalen SurrealDB-File-Backend-Volume-Stand physisch mit in dasselbe Archiv aufnehmen.
- `infrastructure/scripts/setup_backup_task.ps1` registriert den Windows Task `Claire_Hourly_Backup`.
- `infrastructure/scripts/backup_health_check.ps1` prüft auf ein aktuelles Archiv (`exit 0 = PASS`, `exit 1 = FAIL`).
- `infrastructure/scripts/daily_check.py` meldet in Section 6, ob in den letzten 24 Stunden ein Backup vorhanden war.

## Sidecar-Grenze

- Dieser Schnitt macht SurrealDB **nicht** zum Canonical Store.
- Trading State bleibt canonical in Postgres.
- Governance Docs und Ledger bleiben canonical in Git / Ledger-Artefakten.
- Der SurrealDB-Schnitt ist nur ein physischer Sidecar-/Mirror-Backup- und Restore-Pfad.

## Einmaliges Setup

Als Administrator ausführen:

```powershell
cd D:\Dev\Workspaces\Repos\Claire_de_Binare
.\infrastructure\scripts\setup_backup_task.ps1
```

Der Task `Claire_Hourly_Backup` läuft stündlich ab Mitternacht als `SYSTEM`, nutzt standardmäßig `F:\Claire_Backups` und bereinigt Archive älter als 14 Tage automatisch.

Der Standard-Task sichert nur die kanonischen Local-Store-Komponenten (Postgres, Redis). SurrealDB bleibt ein bewusster Opt-in-Schnitt und wird nur per manuellem Lauf mit `-IncludeSurrealDB` aufgenommen.

## Manueller Test

```powershell
Start-ScheduledTask -TaskName "Claire_Hourly_Backup"
Start-Sleep -Seconds 30
.\infrastructure\scripts\backup_health_check.ps1
```

Erwartet wird `PASS  Latest backup: ...`. Bei `FAIL` → Task-History und Failure Modes prüfen.

## Manueller SurrealDB-Schnitt

```powershell
.\infrastructure\scripts\backup_all.ps1 -IncludeSurrealDB
```

- Der SurrealDB-Schnitt kopiert den physischen Volume-Inhalt des File-Backends in dasselbe ZIP-/Manifest-Muster.
- Wenn `-IncludeSurrealDB` gesetzt ist und die Volume-Kopie fehlschlägt, endet der Lauf standardmäßig mit `exit 1`.
- `-AllowSurrealDBFailure` ist nur für Fälle gedacht, in denen das Archiv trotz Sidecar-Fehler als Canonical-Store-Backup weiterlaufen soll.
- Read-only Count-Evidence ist Best Effort. Die physische Kopie ist der eigentliche Backup-Artefakt; fehlende Count-Evidence allein macht den Lauf nicht rot.

## Verifikation

```powershell
Get-ScheduledTask -TaskName "Claire_Hourly_Backup" | Select-Object State, LastRunTime, LastTaskResult
dir F:\Claire_Backups\cdb_backup_*.zip | Sort-Object LastWriteTime -Descending | Select-Object -First 3
```

`LastTaskResult = 0` bedeutet erfolgreicher Lauf.
Im Task Scheduler: `Task Scheduler Library → Claire_Hourly_Backup → History`.

Bei manuellem SurrealDB-Lauf sollte `manifest.json` zusätzlich `Components.SurrealDB = true` und einen `Evidence.SurrealDB`-Block enthalten.

## Failure Modes

- `F:\Claire_Backups` nicht erreichbar → externes Laufwerk prüfen und Task erneut starten.
- `Docker is not running` → Docker starten und Task erneut auslösen.
- `cdb_postgres` oder `cdb_redis` läuft nicht → benötigte Container über den kanonischen lokalen Startpfad hochfahren, dann Task erneut starten.
- `-IncludeSurrealDB` gesetzt, aber `cdb_database_surrealdb_data` / Override-Volume fehlt → Sidecar-Stack bzw. Volume-Pfad prüfen.
- `-IncludeSurrealDB` gesetzt und Manifest zeigt `SurrealDB = false` → Volume-Kopie ist fehlgeschlagen; nur mit `-AllowSurrealDBFailure` tolerierbar.
- Task fehlt in `Get-ScheduledTask` → `setup_backup_task.ps1` erneut als Administrator ausführen.

## Restore-Drill (destruktiv)

```powershell
.\infrastructure\scripts\restore_all.ps1 -BackupName <name> -Force
```

- Wenn das Archiv SurrealDB enthält, leert `restore_all.ps1` das Ziel-Volume vor der Rückkopie bewusst vollständig. Ein Restore darf nicht durch noch intakte Alt-Daten "grün" werden.
- PASS:
  - Volume-Metriken passen zum Backup-Artefakt.
  - `cdb_surrealdb` startet wieder.
  - Health-Check auf `/health` ist grün.
  - Falls Count-Evidence im Manifest vorhanden ist, stimmen die post-restore Counts.
- FAIL:
  - `surrealdb_data` fehlt im Archiv.
  - Volume-Clear oder Rückkopie schlägt fehl.
  - Health-Check oder Count-Abgleich schlagen fehl.

Erwartete Evidence: ZIP-Archiv, `manifest.json`, Restore-Log mit Health-/Count-Resultat.

## Daily Check

`infrastructure/scripts/daily_check.py` prüft in Section 6, ob in den letzten 24 Stunden mindestens ein ZIP-Backup unter `F:\Claire_Backups` erstellt wurde.

## Retention

- Standard-Retention: 14 Tage
- Bereinigung erfolgt automatisch in `backup_all.ps1`
- Kein manuelles Cleanup erforderlich
