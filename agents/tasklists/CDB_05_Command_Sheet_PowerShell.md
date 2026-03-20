# CDB Command Sheet (PowerShell)
Stand: 2026-03-19

## Zweck
Schneller Einstieg ins Working Repo.

Autoritativer PowerShell-Index:
- `tools/README.md`

## 1. Working Repo
```powershell
$WORKING = "D:\Dev\Workspaces\Repos\Claire_de_Binare"
Set-Location $WORKING
git status
```

## 2. Canonical v1 Front Door
- `.\tools\cdb.ps1 secrets init`
- `.\tools\cdb.ps1 runtime up`
- `.\tools\cdb.ps1 stack verify`
- `.\tools\cdb.ps1 service logs -ServiceName cdb_risk -Lines 100`
- `.\tools\cdb.ps1 runtime smoke`

Hinweis:
- `smoke_test.ps1` validiert aktuell den BLUE-Core-Pfad, nicht pauschal den gesamten BLUE+RED-Stack.
- `bootstrap_local.ps1` und `bootstrap_local.sh` bleiben Secondary Convenience Wrapper und sind nicht die kanonische Front Door.

## 3. Operative Front Door
`Makefile` ist fuer viele Standardablaeufe die operative Front Door, aber nicht selbst Teil der PowerShell-v1-Toolchain.

```powershell
make docker-up
make docker-health
make docker-down
```

## 4. Repo Snapshot
```powershell
git branch
git status
git log -1 --oneline
git ls-files --others --exclude-standard
```

## 5. Safety Reminder
- Kein Live-Trading aktivieren
- Keine Secrets committen
- Hardening = erst Report, dann Diff

## 6. LR-040 Boundary
- Der echte LR-040-72h-Soak hat **keinen** nativen PowerShell-Ausfuehrungspfad.
- Normativer Ausfuehrungspfad: Linux-Shell (`native Linux` oder `WSL2`) gemaess `docs/operations/72H_SOAK_TEST_RUNBOOK.md`.
- Vor einem echten LR-040-Run zuerst in der Linux-Shell ausfuehren:
  - `bash infrastructure/scripts/check_lr040_runtime_env.sh`
- Kein LR-040-Start aus `powershell.exe`, `cmd.exe` oder Git Bash improvisieren.
