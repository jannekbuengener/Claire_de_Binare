# CDB Office Pack — Command Sheet (PowerShell)
Stand: 2025-12-16

## Zweck
In **< 60 Sekunden startklar** sein: Repos finden, Status prüfen, Tasks ausführen.

---

## 1. Repos finden
```powershell
$ROOT = "C:\Users\janne\Documents\GitHub\Workspaces"

# Working Repo
$WORKING = "C:\Users\janne\Documents\GitHub\Workspaces\Claire_de_Binare"
cd $WORKING
git status

# Docs Hub Repo finden
Get-ChildItem $ROOT -Directory | Where-Object {
  Test-Path (Join-Path $_.FullName "DOCS_HUB_INDEX.md")
} | Select-Object FullName
```

---

## 2. Baseline Snapshot (beide Repos)
```powershell
git branch
git status
git log -1 --oneline
git ls-files --others --exclude-standard
```

---

## 3. Standard Workflows
### Docker
```powershell
make docker-up
make docker-health
make docker-down
```

### Tests
```powershell
make test
```

---

## 4. Papertrading Smoke-Checks
```powershell
docker ps
docker compose ps
docker compose logs --tail=50
```

---

## 5. Git Hygiene
```powershell
git fetch --all --prune
git status
```

---

## 6. Safety Reminder
- Kein Live-Trading aktivieren
- Keine Secrets committen
- Hardening = erst Report, dann Diff
