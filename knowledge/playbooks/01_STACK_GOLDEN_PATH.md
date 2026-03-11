# 01 — Stack Golden Path (Canonical Runbook)

## Zweck
Ein stabiler Standardablauf, um den Stack reproduzierbar zu starten, zu verifizieren und bei Problemen schnell zu isolieren, ob es ein:
- Infra-Problem (Docker/Compose/Ports)
- Flow-Problem (Orders/Execution/Redis)
- DB-Problem (Schema/Migrations)
ist.

## Voraussetzungen
- Windows 11 + Docker Desktop (WSL2 backend)
- PowerShell 7+
- Docker Compose v2 (`docker compose`)

## Canonical Start (No Drama)
1) **Repo Root**
```powershell
cd C:\Users\<you>\Documents\GitHub\Workspaces\Claire_de_Binare
```

2) **Compose validieren (frühe Fehler rausziehen)**
```powershell
docker compose config > .\_compose.rendered.yml
```
Erwartung: keine Fehler, Datei entsteht.

3) **Build (nur wenn Custom Images)**
```powershell
docker compose build
```

4) **Up**
```powershell
docker compose up -d
```

5) **Status**
```powershell
docker ps --format "table {{.Names}}\t{{.Status}}"
```
Erwartung: kein “Restarting” in Kernservices.

## Golden Checks (2-Minuten Proof)
### A) Redis Wire-Level Proof (Pub/Sub)
**Wichtig:** Pub/Sub erzeugt **keine Keys**. `redis-cli KEYS "*"` darf leer sein.

Terminal A (Subscriber):
```powershell
docker exec -it cdb_redis redis-cli SUBSCRIBE order_results
```

Terminal B (Injection):
```powershell
docker exec cdb_redis redis-cli PUBLISH orders "{\"order_id\":\"test-001\",\"symbol\":\"BTC/USDT\",\"side\":\"BUY\",\"quantity\":0.001}"
```

Erwartung:
- Subscriber sieht JSON Payload
- `cdb_execution` Logs zeigen Verarbeitung + Publish

### B) Stream Proof (optional, wenn aktiv)
```powershell
docker exec cdb_redis redis-cli XRANGE stream.fills - + COUNT 3
```

### C) DB Proof (nach #254/#256)
```powershell
docker exec cdb_postgres psql -U claire_user -d claire_de_binare -c "\dt"
docker exec cdb_postgres psql -U claire_user -d claire_de_binare -c "select count(*) from orders;"
docker exec cdb_postgres psql -U claire_user -d claire_de_binare -c "select count(*) from trades;"
```

## Canonical Stop
```powershell
docker compose down
```

## Dev-Only Hard Reset (löscht Daten!)
```powershell
docker compose down -v
docker compose up -d
```

## Debug Decision Tree (schnell)
### 1) Stack healthy, aber “nichts passiert”
- Problem ist oft: kein Producer. Beweise es mit Injection (oben).
- Wenn Injection geht: Producer-Chain (signals → orders) ist die Baustelle, nicht Execution.

### 2) Injection liefert `PUBLISH ... (integer) 1`, aber Subscriber sieht nichts
- Channel mismatch oder Execution subscribed nicht.
Checks:
```powershell
docker exec cdb_redis redis-cli PUBSUB NUMSUB orders order_results
docker compose logs --no-color --tail 200 cdb_execution
```

### 3) DB Errors `relation ... does not exist`
→ Playbook **03_DB_MIGRATIONS_AND_INIT.md**.

### 4) “Spooky” Zustände
Wenn du nicht mehr weißt, was der Stack gerade macht:
```powershell
docker compose ps
docker compose logs --no-color --tail 200
```
Dann erst handeln, nicht vorher.
