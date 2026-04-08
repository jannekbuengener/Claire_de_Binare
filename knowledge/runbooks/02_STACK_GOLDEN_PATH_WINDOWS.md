# Stack Golden Path

## Start (Canonical — BLUE + RED)
```powershell
docker network create cdb_network 2>$null
docker compose -f infrastructure/compose/compose.blue.yml up -d
docker compose -f infrastructure/compose/compose.red.yml up -d
docker compose -f infrastructure/compose/compose.blue.yml ps
docker compose -f infrastructure/compose/compose.red.yml ps
```

## Stop (RED zuerst, dann BLUE)
```powershell
docker compose -f infrastructure/compose/compose.red.yml down
docker compose -f infrastructure/compose/compose.blue.yml down
```

## DB Reset (WIPES DATA) — nur wenn DB-Init nicht gelaufen ist
```powershell
docker compose -f infrastructure/compose/compose.red.yml down
docker compose -f infrastructure/compose/compose.blue.yml down
docker volume rm claire_de_binare_postgres_data
docker compose -f infrastructure/compose/compose.blue.yml up -d
docker compose -f infrastructure/compose/compose.red.yml up -d
```
