# Session: Issue #1426 — cdb_market unhealthy (503) Healthcheck-Fix

**Datum:** 2026-04-04
**Issue:** #1426 `[MARKET][HEALTH] cdb_market meldet unhealthy (503) ohne Restart im LR-040-Preflight`
**PR:** #1430
**Branch:** `fix/1426-market-healthcheck-start-period`
**Commit:** `f5f60ff4`

---

## Befund

- `cdb_market` Health-Endpoint (`/health`) liefert HTTP 503, wenn `_redis_connected` oder `_subscription_active` noch nicht gesetzt sind
- Flask startet auf Daemon-Thread bevor `_subscription_active = True` gesetzt wird (Startup-Race-Window)
- Docker-Healthcheck in `compose.blue.yml` hatte kein `start_period` — Failures zaehlen ab erster Pruefung
- Beobachtet im LR-040-Preflight: `knowledge/logs/sessions/2026-03-22-lr040-soak-start.md:72`

## Umgesetzter Fix

- `infrastructure/compose/compose.blue.yml`: `start_period: 30s` zum `cdb_market`-Healthcheck hinzugefuegt
- Einzelne Zeile, kein Service-Code geaendert
- Validierung: `docker compose config` bestanden

## Scope-Entscheidung

- Nur Fix 1 (Compose-seitig, `start_period`) umgesetzt
- Fix 2 (Redis-Startup-Retry in `services/market/service.py`) bewusst nicht mitgezogen — im LR-040-Befund nicht als tatsaechliche Ursache belegt

## Side-Issue-Kandidaten

- Permanenter Degraded-Mode ohne Recovery in `services/market/service.py:352-355`: kein Reconnect-Versuch bei Redis-Startup-Failure
- Andere Services (`cdb_candles`, `cdb_regime`, `cdb_allocation`) haben ebenfalls kein `start_period` — gleiche Klasse, separater Sweep-Kandidat

## Status

- PR #1430 gemergt (`7793c028`), Issue #1426 geschlossen
- Status: `erledigt`
