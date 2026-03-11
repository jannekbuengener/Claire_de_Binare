# DB Schema Init & Migrations (2025-12-25)

## TL;DR
Init Scripts in `/docker-entrypoint-initdb.d/` laufen **nur beim ersten Start**, wenn `postgres_data` **leer** ist.

## Symptome
- `relation "orders" does not exist`
- `relation "trades" does not exist`
- `column ... does not exist`

## Dev: Force Schema Reload (wipes data)
```powershell
cd infrastructure/compose
docker compose -f base.yml -f dev.yml down
docker volume rm claire_de_binare_postgres_data
docker compose -f base.yml -f dev.yml up -d
```

## Prod: Apply Manually (preserves data)
```powershell
Get-Content infrastructure/database/schema.sql | docker exec -i cdb_postgres psql -U claire_user -d claire_de_binare
Get-Content infrastructure/database/migrations/002_orders_price_nullable.sql | docker exec -i cdb_postgres psql -U claire_user -d claire_de_binare
```

## Verify Tables
```powershell
docker exec cdb_postgres psql -U claire_user -d claire_de_binare -c "\dt"
```

## Troubleshooting
```powershell
docker logs cdb_postgres | Select-String "initdb"
# Look for "running /docker-entrypoint-initdb.d/01-schema.sql"
```
If schema didn't load:
- Volume war nicht leer → Dev Reset durchführen.
