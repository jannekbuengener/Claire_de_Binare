# Redis Wire-Level Debug (2025-12-25)

## TL;DR
`KEYS "*"` kann leer sein, obwohl Pub/Sub Traffic läuft. Pub/Sub ist kein Keyspace.

## Quick Checks
```powershell
docker exec cdb_redis redis-cli PING
docker exec cdb_redis redis-cli INFO server | Select-String redis_version
```

## Pub/Sub prüfen (live)
```powershell
docker exec -it cdb_redis redis-cli
SUBSCRIBE order_results
```

## Streams prüfen
```powershell
docker exec cdb_redis redis-cli XLEN stream.fills
docker exec cdb_redis redis-cli XRANGE stream.fills - + COUNT 5
```

## "Warum ist Redis leer?"
- Wenn euer System nur Pub/Sub macht, entstehen keine Keys.
- Streams (`XADD`) erzeugen Keys. Wenn `stream.fills` leer ist, ist der Flow idle oder XADD ist aus.
