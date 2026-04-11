# Risk Service (`cdb_risk`)

Deterministischer, fail-closed Risk-Gate-Service zwischen Signal und Execution.

## Current-main Scope

- Prueft eingehende Signale gegen harte Limits und Reason-Code-Regeln.
- Publiziert Orders nur bei explizitem `ALLOW`; Default ist `BLOCK`.
- Schreibt Block-Ereignisse als eigene Artefakte (`stream.orders_blocked`).
- Bleibt orthogonal zu Live-Readiness: Stage `trade-capable` ist keine Live-Freigabe.

## Topics / Streams

- Input Topics: `signals`, `order_results`
- Output Topics: `orders`, `alerts`
- Input Streams: `stream.regime_signals`, `stream.allocation_decisions`, `stream.bot_shutdown`
- Output Streams: `stream.orders`, `stream.orders_blocked`

## Runtime Surface

- Endpoint-Port: `RISK_PORT` (Default `8002`)
- HTTP Endpoints: `/health`, `/status`, `/metrics`

Start im BLUE-Stack:

```powershell
docker compose -f infrastructure/compose/compose.blue.yml up -d cdb_risk
```

## Key Config

- `MAX_POSITION_PCT`
- `MAX_TOTAL_EXPOSURE_PCT` / `MAX_EXPOSURE_PCT`
- `MAX_DAILY_DRAWDOWN_PCT`
- `EARLY_LIVE_MAX_ALLOC`
- `USE_LIVE_BALANCE`, `USE_REAL_BALANCE`

## Canonical References

- `services/risk/service.py`
- `services/risk/config.py`
- `core/contracts/decision_contract_v1.py`
- `docs/governance/MARKET_STATE_CONTRACT_V1.md`
