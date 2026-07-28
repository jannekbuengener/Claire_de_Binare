# Evidence: Fail-closed Risk/Safety Slice (#4152)

**Date:** 2026-07-28  
**Branch:** `fix/4152-risk-fail-closed-safety`  
**Base:** `origin/main@34c80a3c`  
**Scope:** S1 + S2 (+ small S3/S4 contract/docs)  
**LR:** NO-GO (unchanged)  
**Status claim:** `DONE_FIRST_SAFETY_SLICE` — **not** full #4152 closure

## Brain Evidence

```text
brain_source: repo-only
brain_status: not-used
context_brain_attempted: true
context_brain_used: false
context_available: false
records_found: 0
repo_fallback_used: true
repo_fallback_reason: insufficient_evidence
```

## Risk Safety Evidence Map (after slice)

| Domain | Before | After (this slice) |
|--------|--------|--------------------|
| Kill-switch missing/empty/corrupt/unknown | FAIL_OPEN on order path | FAIL_CLOSED via `get_kill_switch_details` / `get_state` / `is_active` |
| Risk bootstrap DB/unexpected error | FAIL_OPEN empty state | FAIL_CLOSED `RuntimeError` (no empty permissive continue) |
| Projected symbol position | UNDERCOUNTED | CORRECT (current + pending qty + order); unknown price / invalid qty block |
| Projected portfolio exposure | present but `>` only | CORRECT with `>=` boundary + helper |
| Stop-loss | ARTIFACT_ONLY | UNAVAILABLE contract; cannot claim protection PASS; no E2E consumer yet |
| Decision exposure/drawdown thresholds | CONFLICTING (50 pp hardcode vs 0.30 fraction) | Derived from RiskConfig via explicit `fraction * 100` → percentage points |

## Fail-open Before / Fail-closed After

| Case | Before | After | Block reason |
|------|--------|-------|--------------|
| Missing KS file (`create_if_missing=False`) | inactive | active | `system_error` / `State file missing` |
| Empty KS file | inactive | active | `system_error` / Empty state file |
| Corrupt / missing `state=` | `get_state` inactive | active | `system_error` |
| Unknown `state=` token | `is_active` false | active | `system_error` |
| Bootstrap DB error | continue empty | raise | `Risk bootstrap failed` |
| Bootstrap mismatch RuntimeError | swallowed by bare except | re-raised | `State mismatch` |
| Unknown price position check | pass | block | `POSITION_PRICE_UNKNOWN` |
| Projected symbol over cap | missing | block | `PROJECTED_POSITION_LIMIT` |
| Stop-loss protection claim | none / implied by metadata | raise | `STOP_LOSS_PROTECTION_UNAVAILABLE` |

## Units and ownership (S4)

| Limit | Canonical source | Unit | Consumer | Conversion |
|-------|------------------|------|----------|------------|
| Max position | `RiskConfig.max_position_pct` | decimal fraction of balance → USDT notional | `check_position_limit`, `check_projected_position_limit` | `notional = balance * fraction` |
| Max exposure | `RiskConfig.max_total_exposure_pct` | decimal fraction → USDT; decide_trade uses percentage points | Hard exposure gate; `decide_trade` RC_021 | `pp = fraction * 100` |
| Daily drawdown | `RiskConfig.max_daily_drawdown_pct` | decimal fraction → USDT; decide_trade percentage points | `check_drawdown_limit`; `decide_trade` RC_020 | `pp = fraction * 100` |
| Stop-loss | `RiskConfig.stop_loss_pct` | decimal fraction metadata only | Order artifact only | **no protection consumer** |

Dead/unused (not wired into order path): `services/risk/circuit_breakers.py`, `live_trading_gate.py` thresholds, metrics-only limits.

## Projection formulas

```text
projected_exposure_usdt =
  total_exposure + pending_exposure_usdt + (order_qty * price)

projected_symbol_qty =
  current_qty + pending_position_qty[symbol] + signed(order_qty)
projected_symbol_notional_usdt =
  abs(projected_symbol_qty) * price
```

Boundary: block when projected value `>=` configured USDT cap.

## Tests executed (this workspace)

```text
pytest -q \
  tests/unit/safety/test_kill_switch_fail_closed.py \
  tests/unit/safety/test_kill_switch.py \
  tests/unit/safety/test_stop_loss_protection.py \
  tests/unit/risk/test_kill_switch_endpoints.py \
  tests/unit/risk/test_bootstrap_fail_closed.py \
  tests/unit/risk/test_projected_position_exposure.py \
  tests/unit/risk/test_decision_threshold_units.py \
  tests/unit/risk/test_service.py \
  tests/unit/risk/test_contract_enforcement.py \
  tests/unit/runtime/test_health_metrics_contract.py \
  tests/integration/test_execution_pipeline.py
→ 94 passed
```

## What is NOT proven (closure blockers for #4152)

- Live Docker Kill-Switch / Unwind drill against running BLUE stack
- End-to-end stop-loss consumer + exit/unwind path
- Runtime restart drill proving unknown state cannot become allowed after process restart in production compose

Therefore: PR uses **Refs #4152**; issue stays **OPEN**; follow-up child for E2E SL monitor/drill.

## Safety boundaries

- No limit relaxation / cap increase
- No Live/Echtgeld/LR-GO
- No BLUE/RED runtime mutation
- No productive DB/MCP writes
- No secrets in evidence
