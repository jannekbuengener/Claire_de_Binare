# Branching, Release, Rollback (2025-12-25)

## TL;DR
Für risk/guard changes: **immer Branch + PR**. Direct-to-main nur, wenn branch protections + required checks enforced sind.

## Canonical Branch Naming
- `feat/<issue>-<slug>`
- `fix/<issue>-<slug>`

## Rollback Commands
```powershell
# Wenn merged:
git revert <SHA>
git push

# Stack neu starten
cd infrastructure/compose
docker compose -f base.yml -f dev.yml down
docker compose -f base.yml -f dev.yml up -d
```
