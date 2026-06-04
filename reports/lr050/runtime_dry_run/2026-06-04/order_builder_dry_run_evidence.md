# Order Builder Dry-Run Evidence

## Scope decision

A full runtime order-builder drill was not executed in this session.

Reason:
- a realistic order-builder path would widen the surface into live `RiskManager` state, Redis streams, and additional runtime wiring
- that would exceed the smallest safe slice for `#2951`
- the prompt contract explicitly prefers a hard non-send proof before any broader execution-path command

## What was exercised instead

### Adjacent evidence that is repo-backed and executed

1. `tests/unit/risk/test_contract_enforcement.py`
   - validates decision-contract identity binding
   - validates hash provenance overwrite
   - validates risk-side kill-switch fail-closed behavior

2. `tests/unit/services/test_execution_shadow_gate.py`
   - validates downstream handling of order payloads at execution-service ingress
   - proves shadow and kill-switch reject behavior before executor use

### Repo-backed code reads

- [`services/risk/service.py`](../../../services/risk/service.py)
  - `_kill_switch_gate()`
  - `check_exposure_limit()`
  - allocation gating via `allocation_pct <= 0`
  - `emit_bot_shutdown()`
- [`docs/live-readiness/LR-050-RISK-LIMITS.md`](../../../docs/live-readiness/LR-050-RISK-LIMITS.md)
  - canary values remain `TBD_BLOCKER_BEFORE_LIVE`

## What remains unproven here

- full `process_signal()` runtime path with real market state inputs
- order publication to Redis under a controlled dry-run harness
- end-to-end evidence that a risk-approved order payload reaches execution while still remaining non-destructive

## Conservative verdict

`partial`

This file is intentionally conservative. It records that order-builder-adjacent contract and gate logic were exercised, but the full runtime order-builder path remains a separate live blocker or follow-up slice before any live-capital reconsideration.
