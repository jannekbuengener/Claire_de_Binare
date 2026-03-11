# DB Schema Init & Migrations (2025-12-25)

Init scripts run only on first startup with empty volume.

Dev reload (wipe data):
```powershell
cd infrastructure/compose
docker compose -f base.yml -f dev.yml down
docker volume rm claire_de_binare_postgres_data
docker compose -f base.yml -f dev.yml up -d
```

Prod apply (preserve data):
```powershell
Get-Content infrastructure/database/schema.sql | docker exec -i cdb_postgres psql -U claire_user -d claire_de_binare
Get-Content infrastructure/database/migrations/002_orders_price_nullable.sql | docker exec -i cdb_postgres psql -U claire_user -d claire_de_binare
```
