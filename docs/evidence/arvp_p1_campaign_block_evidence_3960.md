# ARVP P1 Campaign Attribution + Block-Reason Evidence (#3960)

Status Class: **ENGINEERING_FIX** — code/tests only; no runtime rerun  
Issue: [#3960](https://github.com/jannekbuengener/Claire_de_Binare/issues/3960)  
Root observation: [#3912](https://github.com/jannekbuengener/Claire_de_Binare/issues/3912) (`TIMEOUT_NO_CHAIN`)  
P0 prerequisite: [#3955](https://github.com/jannekbuengener/Claire_de_Binare/issues/3955) / PR [#3956](https://github.com/jannekbuengener/Claire_de_Binare/pull/3956)  
Live-Readiness: **NO-GO**  
Echtgeld: **not authorized**

## Problem

P0 fixed false global zero-event telemetry (#3955) but parallel runs still could not
attribute ledger rows to a campaign or explain lane-level `TIMEOUT_NO_CHAIN` with
risk block codes (e.g. Donchian 50× `RC_001` under `HIGH_VOL_CHAOTIC`).

## P1 Delivery

| Item | Change |
|------|--------|
| P1-1 | `CDB_CAMPAIGN_ID` propagated into `correlation_ledger` SIGNAL/DECISION payloads via `core/replay/correlation_ledger_attribution.py` |
| P1-2 | `aggregate_lane_campaign_evidence()` reports per-lane `signals_emitted`, `decisions_total`, `approvals`, `blocks_total`, `blocks_by_reason`, `orders`, `fills`, `no_chain_reason` |
| P1-3 | `probe_ledger` + supervisor cycle JSONL expose `lane_campaign_evidence` and `no_chain_reason` (P0 `ledger_counts` preserved) |

## Evidence shape (lane)

```json
{
  "campaign_id": "arvp_3912_np_parallel_donchian_20260709_1327",
  "bot_id": "np-donchian-parallel-01",
  "strategy_id": "donchian_breakout_v1",
  "signals_emitted": 50,
  "decisions_total": 50,
  "approvals": 0,
  "blocks_total": 50,
  "blocks_by_reason": {"RC_001": 50},
  "orders": 0,
  "fills": 0,
  "no_chain_reason": "RISK_BLOCKED_NO_PROMOTABLE_CHAIN"
}
```

Idle lane example (`primary_breakout_v1`): `signals_emitted=0`, `no_chain_reason=NO_SIGNALS_OR_GATE_IDLE`.

## Non-goals

- No change to RC_001 / risk semantics
- No natural-paper promotion claim
- No runtime Docker execution in this slice
- LR **NO-GO** unchanged
