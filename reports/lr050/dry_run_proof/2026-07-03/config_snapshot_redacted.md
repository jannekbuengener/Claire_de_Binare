# LR-050 Runtime Dry-Run — Config Snapshot (Redacted)

**Captured:** 2026-07-03T19:47:47Z UTC  
**Issue:** #2978  
**LR verdict:** NO-GO (unchanged)

## Operator safety attestation

| Flag / boundary | Value | Source |
|-----------------|-------|--------|
| `DRY_RUN` | `true` (effective) | `cdb_execution` startup log: `DRY_RUN=True` |
| `MOCK_TRADING` | `true` (explicit) | Compose env + startup log: `MOCK_TRADING=True` |
| `TRADING_MODE` | `(unset)` | Startup log — not authoritative for execution path |
| `CONFIRM_LIVE_TRADING` | `(unset)` | Not set in container env |
| Execution adapter | `mock_builtin` | Startup log: Paper Trading Mode |
| `MEXC_TESTNET` | default `true` if unset | Per `services/execution/config.py` — **not** cited as non-send proof |
| Real exchange order path | **inactive** | Mock adapter + dry-run branch |
| Secret values read by agent | **none** | Names/presence only |

## Compose reference (repo SSOT)

From `infrastructure/compose/compose.blue.yml` for `cdb_execution`:

- `MOCK_TRADING: "true"` (explicit)
- `DRY_RUN` not overridden → defaults to `true` per `services/execution/config.py`

## Container env (names only, values redacted where sensitive)

### `cdb_execution`

| Variable | Observed |
|----------|----------|
| `MOCK_TRADING` | `true` |
| `DRY_RUN` | *(unset in compose → default true)* |
| `MEXC_TESTNET` | *(unset in compose → default true)* |
| `CONFIRM_LIVE_TRADING` | *(unset)* |
| `TRADING_MODE` | *(unset)* |

### `cdb_risk`

| Variable | Observed |
|----------|----------|
| `CDB_KILL_SWITCH_STATE_FILE` | `/app/kill_switch/.cdb_kill_switch.state` |

## Effective trading config (runtime log excerpt)

```text
Mode: MOCK
Trading config: TRADING_MODE=(unset) DRY_RUN=True MOCK_TRADING=True
Using execution adapter: mock_builtin (Paper Trading Mode)
```

## Secret presence (no values)

| Secret mount name | Referenced by service | Value in evidence |
|-------------------|----------------------|-------------------|
| `mexc_api_key` | execution config | **not read** |
| `mexc_api_secret` | execution config | **not read** |
| `postgres_password` | execution/risk config | **not read** |
| `redis_password` | redis clients | **not read** (used only inside container for read-only probe) |

## Stack services (health at capture)

| Service | Health |
|---------|--------|
| `cdb_execution` | ok |
| `cdb_risk` | ok |
| `cdb_allocation` | ok |
| `cdb_candles` | ok |
| `cdb_regime` | ok (1 consumer error noted) |
| `cdb_market` | healthy |
| `cdb_ws` | healthy |
| `cdb_signal` | healthy |
| `cdb_paper_runner` | healthy |

## Non-goals

- No kill-switch activation (#2984 remains open)
- No canary parameters (#2976 remains open)
- No LR-Go / Live-Go / Echtgeld-Go
