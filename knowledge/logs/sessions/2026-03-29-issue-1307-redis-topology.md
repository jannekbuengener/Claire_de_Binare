# Session Log — Issue #1307: Redis Stream/Topic Topology

**Datum:** 2026-03-29
**Branch:** fix/1311-dual-delivery-approved-cleanup
**Scope:** Redis-Topologie-Aufklaerung + ARCHITECTURE_MAP.md Haertung

---

## Befund

ARCHITECTURE_MAP.md war seit 2025-12-28 nicht aktualisiert worden. Drei Kategorien von Drifts:

- **Section 2 falsch**: cdb_allocation, cdb_regime, cdb_market als "Deaktiviert" gelistet — alle aktiv (Ports 8006/8008/8009 in compose.blue.yml)
- **Section 4 unvollstaendig**: market_data-Subscriber fehlten (cdb_candles, cdb_market); gesamter Redis-Stream-Layer (8 Streams) nicht dokumentiert
- **Section 6 veraltet**: prod.yml + tls.yml Naming-Drifts laengst behoben; CLAUDE.md Port-Eintrag falsch zugeordnet

## Verifizierte Topologie (Kurzform)

**Pub/Sub Channels (6):**
- `market_data` → cdb_signal, cdb_candles, cdb_market
- `signals` → cdb_risk, cdb_db_writer
- `orders` → cdb_execution, cdb_db_writer
- `order_results` → cdb_risk, cdb_db_writer
- `portfolio_snapshots` → cdb_db_writer
- `alerts` → kein Subscriber in Service-Code verifiziert (siehe unten)

**Streams (8):**
- `stream.candles_1m`, `stream.regime_signals`, `stream.allocation_decisions`, `stream.fills`, `stream.bot_shutdown` — aktiv mit belegten Consumern
- `stream.signals`, `stream.orders`, `stream.orders_blocked` — write-only Audit-Logs, kein xread-Consumer

## Restunsicherheiten

- `alerts` Publisher: risk/service.py:2011 aktiv belegt; execution/config.py:53 konfiguriert, aber execution/service.py enthaelt keinen Publish-Call
- `alerts` Subscriber: db_writer.py:83 listet "alerts" nicht; kein anderer Service subscribet

## Aenderungen

- `knowledge/ARCHITECTURE_MAP.md` — 5 Deltas + Changelog-Eintrag

## Side-Issue-Kandidaten

- **A**: `alerts` channel — kein Subscriber + execution Publish-Call Dead Code
- **B**: `services/signal/README.md` Port-Drift (8001 vs. 8005)
- **C**: `CLAUDE.md` Dataflow-Terminologie (`risk_requests`/`approved_orders` statt `signals`/`orders`)
