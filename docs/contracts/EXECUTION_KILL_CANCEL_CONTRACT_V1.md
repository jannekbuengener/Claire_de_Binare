# Execution Kill-Cancel Contract v1

**Issue:** #4185
**Schema:** `cdb-kill-cancel-evidence/v1`
**Status:** Mock/dry-run proven surface — **not** live/echtgeld clearance
**LR:** remains **NO-GO**

## Purpose

Distinguish two kill-switch duties:

1. **Block new orders** — fail-closed gate in `process_order()` (#4152 / #4182).
2. **Cancel open orders** — deterministic reconciliation of already-open synthetic
   orders when kill becomes active or unevaluable (#4185).

A failed cancel is not success. An unknown status is not success. Clearing an
in-memory set is not proof that a venue/adapter order was cancelled.

## Open-order truth source

Canonical process truth: `services/execution/open_order_registry.OpenOrderRegistry`

- Registers orders **before** adapter submission (race-safe).
- Tracks internal vs venue order IDs separately.
- Open: `PENDING`, `SUBMITTED`, `PARTIALLY_FILLED`.
- Removes only after **confirmed** terminal status (`FILLED`, `CANCELLED`, `REJECTED`).
- Cancel errors / unknown status keep the residual open.
- Optional JSON ledger via `CDB_OPEN_ORDER_LEDGER_PATH` for restart reconstruction.
- Does **not** use or duplicate the reduce-only ledger from #4184 / PR #4187.

## Cancel adapter contract

Normalized types in `core/contracts/external_adapter_contracts.py`:

- `CancelOrderRequest`
- `CancelOrderResponse` (`accepted` ≠ `confirmed_cancelled`)
- `OpenOrderSnapshot`

Mock adapter (`mock_builtin`) implements cancel + readback.
MEXC builtin marks `supports_cancel=False` in this slice → HOLD
`CANCEL_ADAPTER_UNSUPPORTED` (no productive activation).

## State machine

Per order: `DISCOVERED_OPEN` → `CANCEL_REQUESTED` →
`CANCEL_CONFIRMED` | `ALREADY_TERMINAL` | `CANCEL_REJECTED` |
`CANCEL_ERROR` | `STATUS_UNKNOWN` | `FILL_AFTER_KILL_VIOLATION`

Batch verdicts:

| Verdict | Meaning |
|---------|---------|
| PASS | Every discovered cancelable order confirmed cancelled or already terminal; no fill after kill |
| HOLD | Any reject/error/unknown/residual/source gap/unknown position |
| FAIL | Fill observed after confirmed kill activation |

## Kill trigger

- File kill-switch active **or** unevaluable → HALT for cancel purposes.
- Supervisor watches transitions (not only bot-shutdown events).
- Startup runs reconciliation **before** accepting orders when kill is active/unevaluable.
- Existing new-order kill gate remains fail-closed.

## Idempotency / restart

- Same `kill_event_id` does not re-cancel already confirmed orders.
- Ledger reload reconstructs residuals after process restart.
- No automatic kill deactivation. No silent residual removal.

## Residual orders and positions

- Residuals remain visible in evidence and `/status`.
- Positions are reported only; **no automatic unwind** (see #4184 for reduce-only contract; parked).
- Unknown positions → HOLD. Missing evidence must not invent flat zero.
- Absence of an authoritative position snapshot (empty resolver result, missing
  resolver, or resolver error) normalizes to `status=UNKNOWN`,
  `quantity=null`, `RESIDUAL_POSITION_UNKNOWN` — **never** `NONE`/`0.0`.
- Batch `KILL_CANCEL_PASS` is forbidden while `RESIDUAL_POSITION_UNKNOWN` is set.
  Confirmed per-order cancels remain visible via `cancel_confirmed` /
  `CANCEL_CONFIRMED` even when the batch stays HOLD for unknown positions.

## Fill after kill

Reason code `FILL_AFTER_KILL_ACTIVATION` → batch **FAIL**. No self-heal, no
automatic counter-order in this scope.

## Reason codes

Stable codes include: `KILL_CANCEL_PASS`, `KILL_CANCEL_HOLD`,
`KILL_STATE_UNEVALUABLE`, `OPEN_ORDER_SOURCE_UNAVAILABLE`,
`OPEN_ORDER_STATUS_UNKNOWN`, `CANCEL_ADAPTER_UNSUPPORTED`,
`CANCEL_REQUEST_REJECTED`, `CANCEL_EXECUTION_ERROR`,
`CANCEL_CONFIRMATION_MISSING`, `CANCEL_ALREADY_CONFIRMED`,
`FILL_AFTER_KILL_ACTIVATION`, `RESIDUAL_OPEN_ORDERS`,
`RESIDUAL_POSITION_UNKNOWN`.

## Compose drill evidence statuses (`cdb-kill-cancel-compose-evidence/v1`)

The isolated Compose drill (`infrastructure/scripts/run_kill_cancel_drill.sh`)
writes a per-run manifest via `tools/ci/kill_cancel_compose_evidence.py`.

| Status | Meaning |
|--------|---------|
| `PASS` | Matched JUnit testcase with no failure/error/skipped |
| `FAIL` | Matched JUnit testcase with `<failure>` or `<error>` (product fail) |
| `HOLD` | Matched JUnit testcase was skipped |
| `NOT_RUN` | Expected JUnit file missing for this run |
| `MISSING_MAPPING` | JUnit file present but expected testcase name not found |
| `PARSE_ERROR` | JUnit XML unreadable or malformed |
| `INCOMPLETE` | Stale JUnit (mtime before `.run_marker`) or overall evidence gap |

Rules:

- Scenario `FAIL` is **only** for a real matched testcase failure/error.
- Missing/unmapped/unreadable JUnit must **not** be reported as product `FAIL`.
- `overall_verdict=PASS` requires pytest exits `0`, cleanup pass, and every
  required scenario `PASS`.
- Pytest exit `0` plus scenario evidence gaps → `overall_verdict=INCOMPLETE`
  (honest hold), never a PASS+FAIL contradiction (#4222).

Troubleshooting (Pytest PASS vs scenario-map FAIL):

1. Open `manifest.json` → check `pytest_result`, `scenarios`, `junit_summary`,
   `scenario_evidence_reason`.
2. If scenarios are `NOT_RUN`/`MISSING_MAPPING`/`PARSE_ERROR`, treat as evidence
   pipeline gap — not a kill-cancel product reopen.
3. Confirm `phase1.xml`/`phase2.xml` exist under the run's evidence dir and
   names match `SCENARIO_TEST_MAP` in `tools/ci/kill_cancel_compose_evidence.py`.

## Boundaries

- Mock / dry-run only (`MOCK_TRADING`, `DRY_RUN`).
- No productive MEXC activation, no live credentials, no LR uplift.
- Out of scope: #4186 stop-loss consumer; #4184 reduce-only redesign.
- Board stage `trade-capable` ≠ live go.
