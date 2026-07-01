# Session Log: 2026-07-01 — Issue #3606 Redis Exporter Health

## Auftrag

Diagnose und Fix für `cdb_redis_exporter` unhealthy nach Redis 8.8 Rebuild (#3594). Autonomer Slice: Fix, PR, Merge, Issue close.

## Root Cause

`redis_healthy_but_exporter_probe_wrong`

- Exporter liefert Metriken (`:9121/metrics` HTTP 200, Logs ohne Auth-Fehler)
- Docker-Healthcheck: `nc -z localhost 9121`
- `bitnami/redis-exporter:latest` hat **kein** `nc`, `wget`, oder `curl`
- Health-Log: `/bin/sh: line 1: nc: command not found` (FailingStreak 1768+)

## Fix

`infrastructure/compose/base.yml` + `compose.red.yml`:

```yaml
test: ["CMD-SHELL", "bash -c 'exec 3<>/dev/tcp/127.0.0.1/9121' || exit 1"]
```

Bash `/dev/tcp` ist im Image verfügbar und prüft Port 9121 ohne externe Tools.

## Runtime Validation

| Check | Ergebnis |
|---|---|
| Recreate | `docker compose -p claire_de_binare -f compose.red.yml up -d --force-recreate --no-deps cdb_redis_exporter` |
| Exporter | **healthy** (ExitCode 0) |
| `cdb_redis` | `redis:8.8.0-alpine` healthy (unverändert) |
| `cdb_postgres` | `postgres:18.4-alpine` healthy (unverändert) |
| stack verify | 10/10 core services |

## GitHub

- Issue: #3606 CLOSED
- PR: #3607 MERGED (`498c8b5a`)

## Boundaries

- LR NO-GO unchanged
- Nur `cdb_redis_exporter` recreated; keine Redis/Postgres-Mutation
