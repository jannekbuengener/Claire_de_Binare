# 03 — DB Migrations & Init (Postgres) — Canonical Playbook

## CRITICAL — Init-Skripte laufen nur einmal
Alles unter `/docker-entrypoint-initdb.d/` wird **nur beim ersten Start** ausgeführt, wenn das Datadir (Volume) leer ist.

Das ist der häufigste Grund für:
- `relation "orders" does not exist`
- “Schema liegt im Repo, aber DB hat nix”

## Quick Verify (1 Minute)
```powershell
docker exec cdb_postgres psql -U claire_user -d claire_de_binare -c "\dt"
```
Erwartung: u.a. `orders`, `trades`.

## Dev: Force Schema Reload (wipes all data)
```powershell
docker compose down -v
docker compose up -d
```
Alternative (falls Volume Name fix ist):
```powershell
docker volume rm claire_de_binare_postgres_data
```
> Nur nutzen, wenn Daten egal sind.

## Prod-like: Schema manuell anwenden (preserves data)
```powershell
# Base schema
Get-Content infrastructure/database/schema.sql |
  docker exec -i cdb_postgres psql -U claire_user -d claire_de_binare

# Migration 002 (Beispiel)
Get-Content infrastructure/database/migrations/002_orders_price_nullable.sql |
  docker exec -i cdb_postgres psql -U claire_user -d claire_de_binare
```

## Diagnose: Warum wurden Skripte nicht ausgeführt?
1) Prüfe, ob die Dateien im Container sind:
```powershell
docker exec cdb_postgres ls -la /docker-entrypoint-initdb.d/
```
Erwartung: `01-schema.sql`, `02-migration-*.sql` usw.

2) Prüfe Postgres Logs (Init-Aktivität):
```powershell
docker logs cdb_postgres | Select-String "initdb"
docker logs cdb_postgres | Select-String "docker-entrypoint-initdb.d"
```
Erwartung: Logzeilen, dass Skripte “running …”

## Schema Drift Prevention
- Column Names sind Contract: Services schreiben exakt die Spaltennamen aus schema.sql.
- Constraints beachten (z.B. lowercase side/status).
- Neue Migrationen: lexicographic order + idempotent patterns wo sinnvoll:
  - `CREATE TABLE IF NOT EXISTS`
  - `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`
  - `CREATE INDEX IF NOT EXISTS`

## DoD (DB Fix)
- Fresh init (`down -v`) → Tabellen da
- Existing volume: manual apply dokumentiert
- Keine `relation does not exist` Errors in Logs
