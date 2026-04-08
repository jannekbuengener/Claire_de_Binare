# Session 2026-04-04 — Issue #1420 Soak-Abschluss + Issue #1427 Disk-Evidence-Fix

## Kontext
- LR-040 Soak-Run `artifacts/soak_test_20260401_114850` war bei 72h formal abgeschlossen
- Evidence-Auswertung und operativer Abschluss standen aus

## Ergebnisse

### Issue #1420 — LR-040 Soak-Run Abschluss
- Vollständige Evidence-Auswertung durchgeführt
- SUT-Befund: PASS — 0 Restarts in 69 belegten Checkpoints, 12/12 Services, Shadow-Betrieb aktiv
- Evidence-Qualität: PASS mit dokumentierten Monitor-Lücken (3/72 Checkpoints fehlen)
- Abschlusskommentar gepostet, Issue geschlossen

### Issue #1427 — Disk-Evidence-Fallback
- Root Cause: Console/Alert-Logik prüfte nur `df /repo`, ignorierte valide Docker-Disk-Evidence
- Fix in `infrastructure/scripts/soak_monitor.sh`: neue Variable `DOCKER_DF_VALID`, drei Pfade (Host-FS da / Host-FS fehlt+Docker da / beide fehlen)
- Wenn Host-FS fehlt und Docker-Evidence vorhanden: gelbe Konsole-Warnung, kein Eintrag in `disk_alerts.log`
- Fail-closed erhalten: beide fehlen → `DISK_UNAVAILABLE` in `disk_alerts.log`
- Commit `5741c9ba` auf Branch `fix/1427-soak-monitor-disk-evidence-fallback`
- PR #1429 erstellt, Issue-Kommentar gepostet

## Offene Punkte
- PR #1429 wartet auf CI + Merge
- `/repo`-Mount-Problem selbst ist ein separates Deployment-/Compose-Thema (nicht in dieser Session adressiert)
