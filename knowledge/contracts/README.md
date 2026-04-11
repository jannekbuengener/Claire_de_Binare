# Knowledge Contracts

Aktive Contract-Flaeche fuer Nachrichten-, Adapter- und Strategie-Vertraege im Working Repo.

## Purpose

Dieses Verzeichnis dokumentiert die derzeit verwendeten Contract-Artefakte fuer:

- Markt- und Signal-Payloads (`market_data`, `signal`)
- Adapter-/Boundary-Verhalten
- `primary_breakout_v1`-Spezifikation und Validation-Pfad
- Replay-/Health-Vertragsflaechen

## Active Files

- `CONTRACTS.md` - Gesamtueberblick der Message Contracts
- `market_data.schema.json`, `signal.schema.json` - JSON Schemas
- `EXTERNAL_ADAPTERS.md` - Adapter- und Boundary-Canon
- `PRIMARY_BREAKOUT_V1.md` - Strategievertrag
- `PRIMARY_BREAKOUT_V1_VALIDATION.md` - deterministischer Validation-Vertrag
- `REPLAY_CONTRACT.md`, `HEALTH_CONTRACT.md` - Replay-/Health-Vertraege

## SSOT Boundary

Dieses Verzeichnis ist Contract-Wissen, nicht Status-SSOT.

- Repo-/Engineering-Status: `CURRENT_STATUS.md`
- Board-Stage/Fokus: `docs/runbooks/CONTROL_REGISTER.md`
- Live-Readiness Go/No-Go: `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
