# Redis Wire-Level Debug (2025-12-25)

Pub/Sub is not keyspace.

```powershell
docker exec cdb_redis redis-cli XLEN stream.fills
docker exec cdb_redis redis-cli PUBSUB NUMSUB order_results orders
docker exec cdb_redis redis-cli XRANGE stream.fills - + COUNT 5
```
