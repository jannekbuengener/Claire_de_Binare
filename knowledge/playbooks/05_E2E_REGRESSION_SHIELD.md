# 05 — E2E Regression Shield (#255) — Canonical Spec

## Ziel
Ein schneller E2E-Test, der den wichtigsten “Business Wire” schützt:
**Order → Execution → order_results**

**Scope (Minimum Viable)**
- Publish `orders`
- Receive `order_results` via Pub/Sub (wire-level)
- Validate payload contract (type + timestamp + essential fields)
- Optional: Stream persistence (stream.fills) prüfen

**Non-Goals (für MVP)**
- Keine DB-Abhängigkeit (DB wurde separat gefixt; MVP bleibt robust)
- Keine echten Exchange Calls (paper / mock only)

## Architekturentscheidungen
- Test nutzt Redis direkt, weil Redis der Messaging Backplane ist.
- Test ist “black box”: er validiert Verhalten, nicht Implementierungsdetails.
- Diagnostics-first: bei Fail werden Status/Logs mitgeliefert.

## Env-Konfiguration (CI-ready)
Der Test liest folgende Environment Variablen (Defaults in Klammern):
- `CDB_REDIS_HOST` (`localhost`)
- `CDB_REDIS_PORT` (`6379`)
- `CDB_REDIS_PASSWORD` (leer)
- `CDB_TOPIC_ORDERS` (`orders`)
- `CDB_TOPIC_ORDER_RESULTS` (`order_results`)
- `CDB_STREAM_FILLS` (`stream.fills`)
- `CDB_E2E_TIMEOUT_SECONDS` (`8`)
- `CDB_E2E_REQUIRE_STREAM` (`0`) — wenn `1`, dann muss ein Stream-Entry existieren

## DoD
- Test läuft lokal reproduzierbar (mit laufendem Stack)
- Test läuft in CI (Stack wird vorher gestartet)
- Bei Fail: klare Hinweise (NUMSUB, recent logs)

## Failure Diagnostics (Minimum)
Bei Timeout / No message:
- `PUBSUB NUMSUB orders order_results`
- `docker compose ps`
- `docker compose logs --tail 200 cdb_execution`

## Files in diesem Pack
- `tests/e2e/test_paper_trading_regression_shield.py` (MVP Test)
- `scripts/run_e2e_regression_shield.ps1` (lokaler Runner)
