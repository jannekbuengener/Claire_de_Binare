# Stack Golden Path — Windows 11 / PowerShell

## TL;DR
**Ein Startpfad**. **Ein Stop-Pfad**. Debug in 30 Sekunden. Keine kreativen Varianten.

## Start (Canonical — BLUE + RED)
```powershell
docker network create cdb_network 2>$null
docker compose -f infrastructure/compose/compose.blue.yml up -d
docker compose -f infrastructure/compose/compose.red.yml up -d
docker compose -f infrastructure/compose/compose.blue.yml ps
docker compose -f infrastructure/compose/compose.red.yml ps
```

## Stop (Canonical — RED zuerst, dann BLUE)
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

## Minimal Health Checklist
```powershell
docker compose ps
docker logs cdb_execution --tail 200
docker logs cdb_risk --tail 200
docker exec cdb_redis redis-cli PING
docker exec cdb_postgres pg_isready -U claire_user
```

## Debug Decision Tree (30 Sekunden)
1) Service restarting → `docker compose logs <svc> --tail 200`
2) Tabellen fehlen → Runbook `03_DB_SCHEMA_INIT_AND_MIGRATIONS.md`
3) Redis "leer" → Pub/Sub ≠ Keys → Runbook `05_REDIS_WIRE_LEVEL_DEBUG.md`
