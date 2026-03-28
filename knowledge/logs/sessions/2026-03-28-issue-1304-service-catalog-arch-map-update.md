# Session Log — 2026-03-28 — Issue #1304 SERVICE_CATALOG + ARCHITECTURE_MAP Update

**Topic:** Drift-Fix: SERVICE_CATALOG.md + ARCHITECTURE_MAP.md auf BLUE/RED-Realität
**Issue:** #1304
**Status:** ABGESCHLOSSEN
**Branch:** main

---

## Gelesene Quellen

- `infrastructure/compose/compose.blue.yml`
- `infrastructure/compose/compose.red.yml`
- `infrastructure/compose/logging.yml`
- `services/signal/config.py`, `services/risk/config.py`, `services/execution/config.py`
- `services/candles/config.py`, `services/candles/service.py`
- `services/db_writer/db_writer.py`
- `services/market/service.py`
- `services/risk/service.py`

---

## Durchgeführte Korrekturen

### SERVICE_CATALOG.md
- `cdb_candles` (Port 8007) ergänzt — fehlte komplett
- `cdb_market`, `cdb_regime`, `cdb_allocation` von "BEREIT (deaktiviert)" auf AKTIV korrigiert mit Ports (8009, 8008, 8006)
- RED-Stack komplett ergänzt: `cdb_reports`, `cdb_postgres_exporter` (9187), `cdb_redis_exporter` (9121), `cdb_cadvisor`
- Optionaler Logging-Stack (logging.yml) als eigene Sektion ergänzt: `cdb_alertmanager`, `cdb_loki`, `cdb_promtail`
- Compose-Architektur auf BLUE/RED umgestellt; altes `base.yml + dev.yml`-Primärmodell als legacy markiert
- Stack-Start-Befehl auf kanonischen `.\tools\cdb.ps1 runtime up` aktualisiert

### ARCHITECTURE_MAP.md
- `cdb_candles` in Service-Map und Core-Pipeline-Diagramm ergänzt
- `cdb_market`, `cdb_regime`, `cdb_allocation` mit korrekten Ports und Funktionen eingetragen
- RED-Stack-Services komplett ergänzt
- Core-Pipeline-Diagramm auf echte Redis-Channel-Namen aktualisiert (`market_data`, `signals`, `orders`, `order_results`)
- `candles → regime → allocation → risk`-Flow korrekt dargestellt
- market_state-Ownership post-Cutover #1201 dokumentiert (mit compose.blue.yml-Evidenz)
- Redis-Tabelle auf verifizierte Einträge beschränkt — drei Korrekturen nach Nachschärfung:
  - `stream.regime_signals`: cdb_candles als Subscriber entfernt (nur one-shot XREVRANGE-Lookup, kein persistenter Consumer)
  - `alerts`: Publisher nur cdb_risk (cdb_execution-Nutzung in service.py nicht belegt)
  - `stream.bot_shutdown`: Publisher cdb_risk, Subscriber cdb_execution (nicht beidseitig)
- Interne Streams ohne bekannte Subscriber in Hinweis-Zeile ausgelagert
- Compose-Layer auf BLUE/RED umgestellt; alte Drifts-Sektion entfernt
- Stack-Start auf `.\tools\cdb.ps1 runtime up` aktualisiert

---

## Offene Restunsicherheiten

- `stream.signals`, `stream.orders`, `stream.orders_blocked`, `stream.fills`: Publisher belegt, Subscriber nicht vollständig kartiert
- `cdb_candles` macht einen XREVRANGE-Lookup auf `stream.regime_signals` — ob das als "Consumer" dokumentiert werden sollte, bleibt offen für separate Entscheidung
- `alerts`-Kanal: cdb_execution hat TOPIC_ALERTS in config.py definiert, aber Nutzung in service.py nicht gefunden — konservativ weggelassen

---

## CURRENT_STATUS-Änderungen

Keine Änderungen an CURRENT_STATUS.md notwendig — dieser Fix ändert keinen Engineering-/LR-Status.
