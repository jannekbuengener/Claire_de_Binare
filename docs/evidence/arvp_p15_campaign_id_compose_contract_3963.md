# ARVP P1.5 Campaign ID Runtime Compose Contract (#3963)

Status Class: **ENGINEERING_FIX** — manifest/compose contract + tests only; no runtime rerun  
Issue: [#3963](https://github.com/jannekbuengener/Claire_de_Binare/issues/3963)  
Prerequisite: [#3960](https://github.com/jannekbuengener/Claire_de_Binare/issues/3960) / PR [#3961](https://github.com/jannekbuengener/Claire_de_Binare/pull/3961)  
Root observation: [#3912](https://github.com/jannekbuengener/Claire_de_Binare/issues/3912) (`TIMEOUT_NO_CHAIN`)  
Live-Readiness: **NO-GO**  
Echtgeld: **not authorized**

## Problem

P1 (#3961) added `CDB_CAMPAIGN_ID` propagation into correlation_ledger payloads, but
parallel compose did not wire distinct campaign IDs into `cdb_signal_pb1` and
`cdb_signal_donchian` runtime environments.

## P1.5 Delivery

| Item | Change |
|------|--------|
| P1.5-1 | `tools/arvp_parallel_lane_compose_contract.py` maps campaign manifest `campaign_id` → host env → container `CDB_CAMPAIGN_ID` per lane |
| P1.5-2 | `manifests/runtime_np_parallel_signal_compose_override.yml` sets lane-specific substitution: `${CDB_CAMPAIGN_ID_PB1:-}` / `${CDB_CAMPAIGN_ID_DONCHIAN:-}` |
| P1.5-3 | Contract tests in `tests/unit/arvp/test_arvp_p15_campaign_id_compose_contract.py` |

## Execute contract (future parallel runs)

1. Rewrite both campaign manifests (`campaign_id`, `start_utc`, `timeout_utc`).
2. Export host env from manifests:
   - `CDB_CAMPAIGN_ID_PB1=<pb1 manifest campaign_id>`
   - `CDB_CAMPAIGN_ID_DONCHIAN=<donchian manifest campaign_id>`
3. `docker compose up` with parallel signal override — each lane receives distinct `CDB_CAMPAIGN_ID`.

`SIGNAL_BOT_ID` and `SIGNAL_STRATEGY_ID` behavior unchanged.

## Non-goals

- No runtime Docker execution in this slice
- No risk semantic changes
- No natural-paper promotion claim
- LR **NO-GO** unchanged
