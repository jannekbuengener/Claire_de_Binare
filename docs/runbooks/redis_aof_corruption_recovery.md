# Runbook: Redis AOF Corruption Recovery (cdb_redis)

## Purpose

Document the 2026-05-29 `cdb_redis` AOF corruption incident, root-cause assessment, recovery procedure, and preventive controls. **Ops-only** — no live trading, no LR change.

**Live-Readiness:** NO-GO (unchanged). **Board stage:** trade-capable (unchanged).

## Evidence

Primary session log: [`knowledge/logs/sessions/2026-05-29-redis-aof-recovery.md`](../../knowledge/logs/sessions/2026-05-29-redis-aof-recovery.md).

| Item | Detail |
|------|--------|
| Symptom | `cdb_redis` restart loop (exit 1); dependent BLUE services degraded |
| Error | `Bad file format reading the append only file appendonly.aof.179.incr.aof` |
| Corruption | 3422-byte tail truncation in `appendonly.aof.179.incr.aof` (`ok_up_to=38757026` of `38760448`) |
| Repair tool | `redis-check-aof --fix` on `/data/appendonlydir/appendonly.aof.manifest` |
| Post-repair | `PONG`, `Ready to accept connections`, no AOF parse errors |
| Runtime config | `redis:7.4.9-alpine`, `--appendonly yes` in [`compose.blue.yml`](../../infrastructure/compose/compose.blue.yml) |
| Volume | `claire_de_binare_redis_data` → `/data` |
| Backup (2026-05-29) | `artifacts/redis_aof_recovery_20260529_004112/redis_data_full.tar.gz` (16 106 009 bytes) |
| Backup SHA256 | `5021085D8D39159633149656756D9F89DDEFF54DAA089E1B025F45B5D81697E6` |

Postgres persistence was unaffected. `mockx-valkey` is not CDB-canonical Redis.

## Probable cause

**Most likely: unclean Docker Desktop / host shutdown during AOF append.**

The incremental AOF file showed tail corruption (3422 bytes at EOF) consistent with a partial write interrupted mid-flush. No filesystem or OOM evidence was captured in the session log for the incident window.

## Alternatives (ranked lower)

| Hypothesis | Why lower |
|------------|-----------|
| Disk / filesystem error | No FS errors or SMART evidence in session log |
| OOM kill mid-write | No OOM/dmesg evidence recorded at recovery time |
| Manual volume tampering | No operator edits to `/data`; backup taken before repair |

## Remaining uncertainty

- Exact moment of corruption (host shutdown vs OOM) is **not provable** from repo evidence alone.
- The truncated **3422 bytes** may represent lost Redis writes (~2026-05-27 05:30 UTC per file timestamp).
- Streams and ephemeral Redis state may have gaps; Postgres remains authoritative for persisted events.

## Preventive actions

1. **Graceful stop** before host shutdown: `docker stop cdb_redis` (or `make docker-down`).
2. **Backup before repair:** `make backup` or DR scripts; never run `--fix` without a volume tarball.
3. **Monitor restart loops** and AOF parse errors in `cdb_redis` logs.
4. **Do not** run `redis-check-aof --fix` routinely — only after backup when Redis fails to start with AOF errors.

## Recovery procedure (reference only)

Do **not** re-run unless a new incident occurs. Steps from the 2026-05-29 recovery:

1. **Backup** the Redis volume to `artifacts/` (tar.gz + SHA256).
2. `docker stop cdb_redis`
3. Start a one-off container with the Redis data volume mounted:

   ```bash
   docker run --rm -v claire_de_binare_redis_data:/data redis:7.4.9-alpine \
     sh -c "yes y | redis-check-aof --fix /data/appendonlydir/appendonly.aof.manifest"
   ```

4. `docker start cdb_redis` — verify `PONG` and clean startup logs.
5. Restart dependent services in order: `cdb_db_writer` → candles/regime/allocation → signal → risk → execution → paper_runner → market services.
6. Run stack health checks (`.\tools\cdb.ps1 stack verify` or `make docker-health`).

## Non-goals

- No volume delete, no `docker compose down -v`
- No redirect to `mockx-valkey`
- No LR / live-trading / Echtgeld scope change
- No compose topology change as part of RCA closure

## Related follow-ups (closed elsewhere)

- **#2668 / #2669:** Stack verify logging default + Windows `docker-health` — fixed in PR #2670.
- **#2667:** This runbook closes the RCA documentation gap.
