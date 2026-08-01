# Safety Stop-Loss Consumer Contract v1

**Issue:** #4186 (Refs #4152, #4182)
**Schemas:** `cdb-stop-loss-trigger/v1`, `cdb-stop-loss-exit-intent/v1`,
`cdb-stop-loss-dedup-state/v1`, `cdb-stop-loss-shadow-report/v1`
**Status:** Mock/shadow proven surface — **not** a protection PASS, **not** live clearance
**Protection status:** `UNAVAILABLE` (see § Protection status gate)
**LR:** remains **NO-GO**

## Purpose

Turn stop-loss from order metadata into a deterministic, restart-safe protection
path: one price trigger, one protection event, one reduce-only exit intent.

Until #4186, `STOP_LOSS_PCT` travelled on the order artifact with no consumer and
no exit path (`ARTIFACT_ONLY` / `UNAVAILABLE`, #4152). This contract adds the
missing pieces but does **not** activate a productive exit adapter or queue.

## Components

| Component | Module | Role |
|---|---|---|
| Trigger contract | `core/safety/stop_loss/contracts.py` | Versioned, fail-closed price trigger; deterministic protection event |
| Exit intent | `core/safety/stop_loss/exit_intent.py` | Reduce-only `ExitIntentV1`, sinks, disabled productive adapter |
| Dedup state | `core/safety/stop_loss/dedup_state.py` | Persistence abstraction + atomic JSON file store |
| Consumer | `core/safety/stop_loss/consumer.py` | Orchestrates trigger → dedup → single exit intent |
| Shadow harness | `core/safety/stop_loss/shadow.py` | Container-free candle replay with restart simulation |
| Protection status gate | `core/safety/stop_loss_protection.py` | Evidence ledger → status |

## Trigger semantics

Input is an authoritative `PositionSnapshot` plus one `PriceObservation`.

- LONG: `stop_price = entry * (1 - stop_loss_pct)`, triggers at `price <= stop_price`.
- SHORT: `stop_price = entry * (1 + stop_loss_pct)`, triggers at `price >= stop_price`.
- Quantization uses **protective rounding**: LONG stops round up, SHORT stops
  round down, so rounding can only make protection fire earlier.
- Money/ratio/quantity inputs are `Decimal`/`int`/`str`; `float` and `bool` are
  rejected on the protection path (no-float rule).

Three outcome classes, never conflated:

| Decision | Meaning |
|---|---|
| `TRIGGERED` | Stop breached; carries the protection event |
| `NO_TRIGGER` | Position is flat, or price has not breached the stop |
| `BLOCKED` | Input is unknown, invalid, or stale — protection cannot be decided |

Fail-closed blocks: `STOP_LOSS_SYMBOL_MISMATCH`,
`STOP_LOSS_POSITION_STATE_UNKNOWN`, `STOP_LOSS_POSITION_QUANTITY_UNKNOWN`,
`STOP_LOSS_POSITION_IDENTITY_UNKNOWN`, `STOP_LOSS_ENTRY_PRICE_UNKNOWN`,
`STOP_LOSS_PRICE_INVALID`, `STOP_LOSS_PRICE_STALE`, `STOP_LOSS_CONFIG_INVALID`.

## Protection event identity

The event id is a pure function of the **protection situation**:

```text
identity = {contract_version, symbol, position_id, position_side,
            position_quantity, entry_price, stop_price, stop_loss_pct,
            position_opened_at_ms}
fingerprint = sha256(canonical_json(identity))
event_id    = "slp-" + fingerprint[:32]
```

Consequences:

- Observing tick data (`observed_price`, `observed_at_ms`, `price_source`) is
  **not** part of the identity → every tick below the same armed stop maps to one
  protection event.
- A new position, a reused `position_id` with a new epoch, a changed quantity, or
  a re-armed stop yields a **different** event → a newer protection event can
  never be swallowed by an older dedup entry.

## Exit intent

`ExitIntentV1` is reduce-only by construction:

- `side` is the reducing side (`LONG → SELL`, `SHORT → BUY`); `FLAT`/`UNKNOWN`
  have no reducing side and raise.
- `quantity > 0` and `quantity <= position_quantity` → no position increase, no
  side flip. Partial exits are allowed.
- `reduce_only=True`, `intent_kind=PROTECTIVE_EXIT`.
- `dispatch_state=NOT_DISPATCHED`, `productive_adapter_enabled=False`.
- `intent_id = "slx-" + sha256(canonical_json({schema, event_id, symbol, side, quantity}))[:32]`
  — deterministic, independent of wall-clock time.

An exit intent is **not** an order. Order-side reduce-only enforcement is owned
by #4184 / PR #4187 (parked) and is not touched here.

## Dedup state and restart safety

Two-phase ledger per protection event:

```text
prepare (PREPARED) → sink.accept(intent) → finalize (FINALIZED)
```

| Stored state | Consumer behaviour |
|---|---|
| absent | Emit one intent (prepare → accept → finalize) |
| `FINALIZED`, fingerprint matches | `DUPLICATE_SUPPRESSED` |
| `PREPARED` | **BLOCK** `STOP_LOSS_PREPARE_INCOMPLETE` — delivery unproven, never emit a second intent |
| fingerprint mismatch | **BLOCK** `STOP_LOSS_DEDUP_STATE_CONTRADICTORY` |
| state file missing | **BLOCK** `STOP_LOSS_DEDUP_STATE_MISSING` — an absent state is not an empty state |
| state file corrupt | **BLOCK** `STOP_LOSS_DEDUP_STATE_CORRUPT` |

Rules:

- The store must be explicitly initialized once (`initialize()`), which writes a
  valid empty ledger. `initialize()` never overwrites existing or corrupt state.
- `FileStopLossDedupStore` writes atomically (temp file + `Path.replace`), the
  same pattern as `core/safety/kill_switch.py`.
- Persistence is an abstraction (`StopLossDedupStore` protocol). The file store
  is the local, non-productive implementation. **No** productive DB migration or
  mutation is part of this slice.

## Partial-success handling

No failure is silently absorbed:

| Failure | Outcome | Emitted intents |
|---|---|---|
| prepare write fails | BLOCK `STOP_LOSS_DEDUP_PREPARE_FAILED` | 0 |
| sink rejects intent | BLOCK `STOP_LOSS_EXIT_INTENT_SINK_FAILED`, record stays `PREPARED` | 0 |
| finalize fails after acceptance | BLOCK `STOP_LOSS_DEDUP_FINALIZE_FAILED`, outcome carries the intent | 1, reported |

A crash after `prepare` can only **lose** an intent, never duplicate one. Losing
protection is visible as a persistent `PREPARE_INCOMPLETE` block that requires
operator resolution.

## Protection status gate

`core/safety/stop_loss_protection.py` derives the status from an explicit
evidence ledger. `END_TO_END_PROVEN` requires **all** proofs:

| Proof | State after #4186 |
|---|---|
| `trigger_contract_proven` | ✅ unit/contract tests |
| `consumer_proven` | ✅ unit tests + shadow run |
| `persistent_dedup_proven` | ✅ file-store tests |
| `restart_replay_proven` | ✅ restart/replay tests |
| `real_stack_persistence_proven` | ❌ open (no Docker/Redis/Postgres drill) |
| `productive_exit_path_proven` | ❌ open (adapter intentionally disabled) |

Two proofs are missing, so `STOP_LOSS_PROTECTION_STATUS` stays `UNAVAILABLE` and
the risk gate (`services/risk/service.py`) keeps blocking any signal that
declares `requires_stop_loss_protection`. Code presence is never protection
evidence.

## Price sources

The trigger consumes a `PriceObservation`. Available runtime sources today:
`market_state:{symbol}` (`close_now`) and the `stream.candles_1m` `close` field.
Both are converted to `Decimal` via decimal strings; observations older than
`max_price_age_ms` (default 120 000 ms, matching the market-state TTL) or dated
in the future block as `STOP_LOSS_PRICE_STALE`.

## Evidence

- Manifest: `docs/evidence/risk/4186_stop_loss_consumer_dedup.json`
  (generator: `python -m tools.safety.stop_loss_consumer_evidence`)
- Report: `docs/evidence/risk/4186_stop_loss_consumer_dedup.md`
- Fixture: `tests/fixtures/stop_loss_shadow_candles.json`

## Boundaries

- Mock/shadow only; no productive queue, adapter, or exchange call.
- No risk, exposure, drawdown, or position cap was changed.
- No productive DB write, no MCP mutation, no BLUE/RED runtime change.
- Kill-switch and unwind scope (#4185, #4184) untouched.
- Board stage `trade-capable` ≠ live go. LR remains **NO-GO**.
