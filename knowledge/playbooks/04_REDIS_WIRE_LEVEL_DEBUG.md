# 04 — Redis Wire-Level Debug (Pub/Sub, Streams, Mythen)

## TL;DR
- **Pub/Sub speichert nichts** → `KEYS "*"` kann leer sein und trotzdem fließt Traffic.
- Beweisführung geht über **SUBSCRIBE** und **PUBSUB NUMSUB**, nicht über KEYS.

## Proof Commands (Canonical)
### Channels + Subscriber Counts
```powershell
docker exec cdb_redis redis-cli PUBSUB CHANNELS
docker exec cdb_redis redis-cli PUBSUB NUMSUB orders order_results
```

### Wire-Tap: Subscriber
```powershell
docker exec -it cdb_redis redis-cli SUBSCRIBE order_results
```

### Trigger: Order Injection
```powershell
docker exec cdb_redis redis-cli PUBLISH orders "{\"order_id\":\"test-001\",\"symbol\":\"BTC/USDT\",\"side\":\"BUY\",\"quantity\":0.001}"
```

## Streams (wenn Replay/Persistenz)
### Letzte Events ansehen
```powershell
docker exec cdb_redis redis-cli XREVRANGE stream.fills + - COUNT 3
```
### Stream existiert?
```powershell
docker exec cdb_redis redis-cli EXISTS stream.fills
docker exec cdb_redis redis-cli XLEN stream.fills
```

## Typische Fehlerbilder
### 1) Subscriber sieht nichts
- Channel name mismatch (config)
- Producer publisht nie
- Consumer subscribed nicht

Check:
```powershell
docker exec cdb_redis redis-cli PUBSUB NUMSUB order_results
docker compose logs --no-color --tail 200 cdb_execution
```

### 2) Producer publisht, aber Consumer droppt
- Schema mismatch / parse error
- Type filtering (z.B. `type != "order_result"`)
→ Immer Logging + raw payload dump.
