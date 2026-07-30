# Evidence: Kill-Cancel Open Orders (#4185)

**Getesteter Code-Commit:** 

**Run-ID:** 

**Verdict:** `HOLD`

**LR:** `NO-GO` (unverändert)

## Brain Evidence

```text
brain_source: repo-only
brain_status: not-used
context_tool_status: absent
context_trust_level: none
records_found: none
repo_fallback_used: true
repo_fallback_reason: unavailable
```

## Claim-Grenze

Mock-only Kill-Cancel fuer offene synthetische Orders. Kein produktiver Adapter,
kein automatisches Positions-Unwind, kein Stop-Loss-Consumer (#4186), kein
Reduce-only-Redesign (#4184 / PR #4187 geparkt). Board stage trade-capable ist
nicht Live-Go.

## G1/G2 Korrektur

**Before:** leeres `_known_residual_positions` wurde als `status=NONE`,
`quantity=0.0`, `RESIDUAL_POSITION_NONE` interpretiert → Batch-`PASS`.

**After:** fehlende autoritative Positions-Evidence → leere Resolver-Liste →
Coordinator normalisiert auf `UNKNOWN` / `RESIDUAL_POSITION_UNKNOWN` /
Batch-`HOLD`. Per-order Cancels bleiben `cancel_confirmed=true` /
`CANCEL_CONFIRMED` sichtbar. Batch-`KILL_CANCEL_PASS` ist mit
`RESIDUAL_POSITION_UNKNOWN` verboten.

Historische Evidence @ `59e31c60` (PASS + NONE/0.0) ist **superseded** und darf
nicht als aktueller Head-Beweis gelesen werden.

## Ergebnis

- Open-order truth: OpenOrderRegistry (+ optional JSON ledger)
- Cancel contract: CancelOrderRequest / CancelOrderResponse / readback
- Batch verdict **HOLD** bei bestätigtem Cancel ohne Positions-SSOT
- Unit/Contract: `tests/unit/execution/test_kill_cancel_open_orders.py` (27 PASS)
- Compose-E2E: siehe PR-Body (scenarios 1–12 am validierten Tip; Cleanup 0/0/0)

Maschinenlesbares Manifest: `4185_kill_cancel_open_orders.json` (Schema `cdb-kill-cancel-evidence/v1`).

## Safety

- Keine Secrets im Manifest
- Kein Merge / keine Issue-Schliessung in dieser Session
- LR bleibt NO-GO
- Keine autoritative Position-SSOT im #4185-Scope (Restunsicherheit)
