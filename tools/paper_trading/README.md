# Paper Trading Runner (`cdb_paper_runner`)

BLUE-Stack-Service für automatisierten Paper-Trading-Lauf (Default: 14 Tage). Implementierung liegt unter `tools/paper_trading/`, nicht unter `services/`.

## Current-main Scope

- Subscribiert Redis-Events (`market_data`, `signals`, `orders`, `order_results`).
- Persistiert Event-Logs (JSONL) und periodische Postgres-Snapshots.
- Health auf Port **8004** (`/health`, `/status`).
- Shadow/Paper-only — kein Live-Kapital, kein LR-Go.

## Runtime Surface

- Container: `cdb_paper_runner` in [`compose.blue.yml`](../../infrastructure/compose/compose.blue.yml)
- Entry: `python tools/paper_trading/service.py`
- Port: `8004`

Start:

```powershell
docker compose -f infrastructure/compose/compose.blue.yml up -d cdb_paper_runner
```

Makefile-Helfer (wenn Stack läuft): `make paper-trading-start` / `make paper-trading-logs` / `make paper-trading-stop`

## Key Config

- `PAPER_TRADING_DURATION_DAYS` (Default `14`)
- `LOG_LEVEL`, Redis/Postgres via Compose secrets (wie übrige BLUE-Services)

## Canonical References

- [`service.py`](service.py)
- [`knowledge/systems/PAPER_TRADING_ARCHITECTURE.md`](../../knowledge/systems/PAPER_TRADING_ARCHITECTURE.md)
- [`knowledge/operating_rules/`](../../knowledge/operating_rules/)
- [`services/risk/README.md`](../services/risk/README.md)

## SSOT boundary

LR **NO-GO** — `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`. Paper-Runner-Evidenz ist kein Echtgeld-Go.
