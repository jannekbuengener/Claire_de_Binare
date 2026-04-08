# Session: Soak Telemetry Sidecar (2026-04-01)

**Issue-Kontext**: #1420 (LR-040 Soak), disk_alerts.log DISK_UNAVAILABLE
**Ziel**: Ergaenzende Host-Telemetrie ohne Beruehrung des laufenden LR-040-Soaks

## Befund

- `soak_monitor.sh` laeuft im Docker-Container, `df /repo` schlaegt fehl (kein `/repo` Mount auf Windows-Host)
- `disk_alerts.log` zeigt wiederholt `DISK_UNAVAILABLE` — Host-Disk/RAM/CPU blind
- Aktiver Soak-Run: `artifacts/soak_test_20260401_114850/` (Start 2026-04-01T11:48:50Z, 72h-Ziel)

## Massnahmen

- `infrastructure/scripts/soak_telemetry_sidecar.sh` erstellt — host-seitiges Capture-Script
  - Dynamische Drive-Erkennung via `cygpath` (kein Hardcoding)
  - PowerShell als kanonische Windows-Disk-Quelle (`Get-PsDrive`)
  - Erfasst: Host-Disk, RAM, CPU, Docker system df, Docker stats
  - Run-ID-Aufloesung: Argument > Env > Pointer > Auto-Detect
  - Portabel: kein `grep -P`, `sed`/`awk` fuer Metrik-Extraktion
- `artifacts/run_soak_sidecar.cmd` erstellt — Windows-Launcher (analog `run_soak_monitor.cmd`)
  - `mkdir` vor Redirect gegen fehlenden Zielordner
- Windows Task Scheduler: `CDB_Soak_Sidecar` alle 15 Minuten aktiviert

## Artefakte

- Sidecar-Output: `artifacts/telemetry_sidecar/soak_test_20260401_114850/`
- README.md-Marker: non-canonical, safe to delete
- Erster Capture verifiziert: Disk 14,4%, RAM 87,7%, CPU 13%
- Kanonischer Run-Pfad: unveraendert (Timestamps verifiziert)

## Harte Constraints eingehalten

- `soak_monitor.sh` nicht geaendert
- `lr040_soak_gate_eval.py` nicht geaendert
- Kein Schreiben in `artifacts/soak_test_20260401_114850/`
- Kein Stack-Neustart
- Keine Kontamination der kanonischen LR-040-Evidence

## Offene Punkte

- Scheduler-Zyklus-Verifikation: erster automatischer Lauf bei ~15:56 pruefen
- Nach Soak-Ende: `schtasks /delete /tn "CDB_Soak_Sidecar" /f`
- Issue-Kommentar #1420 noch nicht gepostet (Text bereit)
- Kein Commit/PR erstellt (nur lokale neue Dateien)
