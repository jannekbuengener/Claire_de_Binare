# Stack Golden Path (2025-12-25)

```powershell
cd infrastructure/compose
docker compose -f base.yml -f dev.yml up -d
docker compose ps
docker compose -f base.yml -f dev.yml down
```

Dev reset (wipes data):
```powershell
cd infrastructure/compose
docker compose -f base.yml -f dev.yml down
docker volume rm claire_de_binare_postgres_data
docker compose -f base.yml -f dev.yml up -d
```
