# Evidence: Kill-Cancel Open Orders (#4185)

**Getesteter Code-Commit:** `59e31c606e9819f3efa5fc69e28d599190617759`

**Run-ID:** `4185_59e31c60_unit`

**Verdict:** `PASS`

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

## Ergebnis

- Open-order truth: OpenOrderRegistry (+ optional JSON ledger)
- Cancel contract: CancelOrderRequest / CancelOrderResponse / readback
- Batch verdict PASS fuer bestaetigbare Cancels; HOLD bei Restorders; FAIL bei Fill-after-Kill
- Unit/Contract: tests/unit/execution/test_kill_cancel_open_orders.py
- Compose-E2E: nicht ausgefuehrt (Restunsicherheit; Mock-Integration belegt)

Maschinenlesbares Manifest: `4185_kill_cancel_open_orders.json` (Schema `cdb-kill-cancel-evidence/v1`).

## Safety

- Keine Secrets im Manifest
- Kein Merge / keine Issue-Schliessung in dieser Session
- LR bleibt NO-GO
