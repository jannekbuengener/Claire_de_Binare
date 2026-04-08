# Session: Issue #1409 — ARCHITECTURE_MAP + SERVICE_CATALOG Reconcile

**Datum:** 2026-04-01
**Issue:** #1409
**Branch:** chore/session-22-close

## Befund

- SERVICE_CATALOG.md führte Loki/Promtail/Alertmanager mit Status **AKTIV** — obwohl diese Services in `logging.yml` (separates Overlay) definiert sind, nicht in compose.blue.yml oder compose.red.yml
- ARCHITECTURE_MAP.md und SERVICE_CATALOG.md beschrieben die Overlay-Aktivierung als `-Logging Flag` — irreführend, tatsächlich ist es `-f infrastructure/compose/logging.yml` im compose-Befehl
- CDB_DOCKER_STACK_INVENTORY.md fehlte `logging.yml` in der Compose-Layers-Tabelle komplett

## Durchgeführte Änderungen

- `knowledge/governance/SERVICE_CATALOG.md`
  - Status-Definition **OVERLAY** ergänzt (separates Compose-Overlay, nicht Teil des Standard-BLUE/RED-Starts)
  - Loki/Promtail/Alertmanager: Status AKTIV → OVERLAY
  - Sektionsüberschrift präzisiert: "separates Overlay, nicht Teil des Standard-BLUE/RED-Starts"
  - Aktivierungsbefehl explizit als compose-Kommando (`-f logging.yml`) dokumentiert
  - Compose-Architektur-Notation: `[kanonisch]` / `[separates Overlay]` ergänzt

- `knowledge/ARCHITECTURE_MAP.md`
  - Aktivierungsspalte: `-Logging Flag` → Spaltenname "Compose-Datei" + Wert "logging.yml"
  - Aktivierungsbefehl als compose-Kommando über der Tabelle ergänzt
  - Section 7 Compose Layer Referenz: `[kanonisch]` / `[separates Overlay]` ergänzt

- `knowledge/CDB_DOCKER_STACK_INVENTORY.md`
  - `logging.yml` als "Optional overlay — nicht Teil des Standard-BLUE/RED-Starts" in Compose-Layers-Tabelle eingetragen

## Ergebnis

- BLUE/RED-Grenze ist jetzt scharf: nur compose.blue.yml + compose.red.yml = Standard-Runtime
- Logging Overlay ist eindeutig als separat und nicht-standard beschriftet
- Keine der drei Dateien kann mehr als zweiter Runtime-Canon gelesen werden
- CDB_DOCKER_STACK_INVENTORY.md ist vollständig gegenüber den vorhandenen Compose-Dateien
