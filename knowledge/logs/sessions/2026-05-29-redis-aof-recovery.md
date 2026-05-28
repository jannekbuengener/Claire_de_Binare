# Session Log: Redis AOF Recovery + Stack Stabilization

**Date:** 2026-05-29 (Europe/Berlin)  
**Scope:** Plan-GO Redis-AOF-Recovery (read/write ops on Docker runtime only; no LR/trading change)  
**Git:** `main` @ `d8432dc569b88cf0e361c9dab9f917bbc96c8394` (clean worktree)  
**Gordon:** `GORDON_NOT_AVAILABLE` (no CDB Gordon MCP/agent integration). Recovery proceeded under explicit Plan-GO with backup-before-repair and log-backed root cause.

---

## Ausgangslage

- `cdb_redis` in Restart-Loop (Exit 1).
- Redis-abhängige Kerndienste (signal, risk, execution, candles, paper_runner, market) degraded oder Restart-Loop.
- Postgres, WS, Monitoring weiterhin up.

## Root Cause (Runtime-Evidence)

Redis Multi-Part-AOF inkrementelle Datei korrupt:

```
Bad file format reading the append only file appendonly.aof.179.incr.aof
```

`redis-check-aof` identifizierte 3422 Bytes Tail-Korruption in `appendonly.aof.179.incr.aof` (ok_up_to=38757026 von 38760448).

## Phase 0 — Backup

| Feld | Wert |
|------|------|
| Volume | `claire_de_binare_redis_data` → `/data` |
| Backup-Pfad | `artifacts/redis_aof_recovery_20260529_004112/` |
| Artefakt | `redis_data_full.tar.gz` |
| Größe | 16 106 009 bytes (~15.4 MiB) |
| SHA256 | `5021085D8D39159633149656756D9F89DDEFF54DAA089E1B025F45B5D81697E6` |

Kein Volume gelöscht. Kein `docker compose down -v`.

## Phase 1 — AOF Repair

1. `docker stop cdb_redis`
2. One-off `redis:7.4.9-alpine` mit Volume-Mount
3. Befehl:

```bash
yes y | redis-check-aof --fix /data/appendonlydir/appendonly.aof.manifest
```

**Output (Kern):**

- BASE AOF `appendonly.aof.179.base.rdb`: valid (13 keys)
- INCR AOF format error → truncated 3422 bytes
- `All AOF files and manifest are valid`
- Incr-Datei: 38760448 → 38757026 bytes

4. `docker start cdb_redis`
5. Validierung: `PONG`, Log `Ready to accept connections`, kein AOF-Parse-Error

## Phase 2 — Service Recovery

Sequentieller `docker restart`:

`cdb_db_writer` → `cdb_candles` → `cdb_regime` → `cdb_allocation` → `cdb_signal` → `cdb_risk` → `cdb_execution` → `cdb_paper_runner` → `cdb_market` → `cdb_market_eth`

## Phase 3 — Validierung

| Check | Ergebnis |
|-------|----------|
| `redis-cli PING` | PONG |
| `http://127.0.0.1:8009/health` | 200 |
| Compose BLUE+RED core | alle healthy |
| signal logs | price buffer / market data (kein Redis-Fehler) |
| risk logs | regime updates, `/health` 200 |
| execution logs | MOCK mode, `/health` 200 |
| market logs | `Redis connected at cdb_redis` |
| `.\tools\cdb.ps1 stack verify` | 10/12 healthy — **cdb_loki/cdb_promtail missing** (pre-existing, nicht Teil dieser Recovery) |
| `make docker-health` | FAIL (Windows: `grep` nicht verfügbar im Makefile-Target) |

## Stack-Health (post-recovery)

| Service | Status |
|---------|--------|
| cdb_redis | healthy |
| cdb_postgres | healthy |
| cdb_ws | healthy |
| cdb_market | healthy |
| cdb_market_eth | healthy |
| cdb_candles | healthy |
| cdb_regime | healthy |
| cdb_allocation | healthy |
| cdb_signal | healthy |
| cdb_risk | healthy |
| cdb_execution | healthy (MOCK) |
| cdb_db_writer | healthy |
| cdb_paper_runner | healthy |
| cdb_prometheus / grafana / exporters | healthy |

## Verbleibende Risiken

- **3422 Bytes** am Ende des INCR-AOF verworfen — möglicherweise letzte Redis-Writes vor Crash (~2026-05-27 05:30 UTC laut Datei-Timestamp).
- Streams/ephemeral state in Redis können Lücken haben; Postgres-Persistenz unberührt.
- `mockx-valkey` läuft parallel, ist **nicht** CDB-Canon-Redis.
- Loki/Promtail fehlen im lokalen Stack (optional logging layer).

## Governance

- **LR:** NO-GO (unverändert)
- **Board-Stage:** trade-capable (unverändert)
- **Kein Live-Trading**, Execution weiterhin MOCK/DRY_RUN
- **Kein Redirect** auf mockx-valkey

## Follow-up (optional)

- Issue: AOF-Korruption Root-Cause (unclean shutdown / disk / OOM?) unklar
- Issue: `make docker-health` Windows-kompatibel machen (grep-Abhängigkeit)
- Issue: Loki/Promtail Stack-Drift vs. `stack verify` Erwartung klären
