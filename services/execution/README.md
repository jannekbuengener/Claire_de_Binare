# Execution Service (`cdb_execution`)

Order-Execution-Service: konsumiert freigegebene Orders vom Risk Service und publiziert Fills/Results.

## Current-main Scope

- Subscribes `orders` (Pub/Sub) nur nach Risk-`ALLOW`.
- Default: `MOCK_TRADING=true`, `DRY_RUN=true` — kein unkontrolliertes Live-Trading.
- Publiziert `order_results` und schreibt in `stream.fills` (kanonisch für Persistenz via `cdb_db_writer`).
- Kill-Switch-Volume geteilt mit `cdb_risk` (`CDB_KILL_SWITCH_STATE_FILE`).
- **Kill-Cancel (#4185):** bei Kill active/unevaluable werden offene synthetische Orders
  deterministisch cancelled; neue Orders bleiben blockiert. Fehlgeschlagene Cancels
  bleiben als Restorders sichtbar (HOLD) — kein blindes `open_orders.clear()`.
  Fehlende autoritative Positions-Evidence → `RESIDUAL_POSITION_UNKNOWN` und Batch-HOLD
  (kein erfundenes Flat-Zero `NONE`/`0.0`).

## Kill: block vs cancel

| Duty | Mechanism |
|------|-----------|
| Block new orders | `process_order()` kill gate + kill-cancel HOLD readiness |
| Cancel open orders | `KillCancelSupervisor` + `KillCancelCoordinator` + `OpenOrderRegistry` |

Contract: [`docs/contracts/EXECUTION_KILL_CANCEL_CONTRACT_V1.md`](../../docs/contracts/EXECUTION_KILL_CANCEL_CONTRACT_V1.md)
Evidence: `docs/evidence/risk/4185_kill_cancel_open_orders.md`

Open-order truth: `services/execution/open_order_registry.py` (optional ledger
`CDB_OPEN_ORDER_LEDGER_PATH`). Resting mock drills: `CDB_MOCK_RESTING_ORDERS=true`.

Out of scope here: reduce-only unwind (#4184 / PR #4187, parked), stop-loss consumer (#4186),
automatic position close, productive MEXC cancel activation. LR remains **NO-GO**.

## Topics / Streams

- Input Topic: `orders`
- Output Topic: `order_results`
- Output Stream: `stream.fills` (`STREAM_ORDER_RESULTS`)
- Shutdown Stream: `stream.bot_shutdown`

## Runtime Surface

- Endpoint-Port: `8003` (`SERVICE_PORT`)
- HTTP: `/health`, `/status`, `/metrics` — `/health` and `/status` expose secret-safe
  kill-cancel readiness and residual open-order count (not LR-Go).

Start im BLUE-Stack:

```powershell
docker compose -f infrastructure/compose/compose.blue.yml up -d cdb_execution
```

## Key Config

- `MOCK_TRADING`, `DRY_RUN`, `MEXC_TESTNET`
- `MEXC_API_KEY` / `MEXC_API_SECRET` (Secrets)
- `STREAM_ORDER_RESULTS`, `STREAM_BOT_SHUTDOWN`
- `CDB_OPEN_ORDER_LEDGER_PATH`, `CDB_MOCK_RESTING_ORDERS`, `CDB_KILL_CANCEL_POLL_SECONDS`

## Canonical References

- `services/execution/service.py`
- `services/execution/kill_cancel.py`
- `services/execution/open_order_registry.py`
- `services/execution/config.py`
- `services/risk/README.md`
- `core/contracts/decision_contract_v1.py`
- `docs/contracts/EXECUTION_KILL_CANCEL_CONTRACT_V1.md`
