# Session: Issue #1334 — services/validation Inventory Clarity

**Datum:** 2026-03-29
**Branch:** fix/1334-validation-inventory-clarity
**Issue:** #1334
**PR:** #1340

## Ziel

`services/validation/` eindeutig klassifizieren, damit aktive Inventar-Sweeps nicht weiter raten müssen.

## Befund

- `services/validation/` ist eine Library/CLI-Komponente (72h-Validierungs-Gate-Logik)
- Kein Compose-Service, kein Dockerfile, kein HTTP-Endpoint
- CLI-Runner mit `argparse` und `__main__`
- `validation_data` Volume in compose.blue gemounted an `cdb_risk:/app/data`, nicht an einen validation-Container
- Kein Import durch laufende Services; `runner.py` importiert *aus* `services.risk`, nicht umgekehrt
- Unit + Integration-Tests existieren
- SYSTEM_INVARIANTS referenziert `gate_evaluator.py` als LR-Gate-Logik
- PROJECT_STATUS.md klassifiziert bereits korrekt als `UTILITY LIBRARY`

## Klassifikation

`inactive-dormant-but-intentionally-retained`

## Root Cause

LR-002 Stack Map listete `validation` ohne Qualifikation neben echten Compose-Services → Inventar-Sweeps interpretierten es als fehlenden Container.

## Änderungen

- `docs/live-readiness/LR-002-STACK-SNAPSHOT.md`: validation-Eintrag qualifiziert als "library/CLI, not compose-wired", Zähler korrigiert (11 compose-wired + 1 library/CLI)

## Status

- PR #1340 offen, mergebar
- Issue #1334 offen, Befund-Kommentar als Persistenzanker gepostet
- Schließen nach Merge von #1340
