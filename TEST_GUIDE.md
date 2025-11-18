# Test Guide – Claire de Binaire

## Ziel
Anleitung zum Ausführen von Tests, Systemchecks und Validierungen während der N1-Paper-Test-Phase.

## ENV-Validation
```bash
backoffice/automation/check_env.ps1
```

## Docker-Systemcheck
1. Start:
```bash
docker compose up -d cdb_redis cdb_postgres cdb_prometheus cdb_grafana
docker compose up -d cdb_ws cdb_core cdb_risk cdb_execution
```

2. Status:
```bash
docker compose ps
```

3. Health:
```bash
curl -fsS http://localhost:8001/health
curl -fsS http://localhost:8002/health
curl -fsS http://localhost:8003/health
```

## Pytests
```bash
pytest -v
```
