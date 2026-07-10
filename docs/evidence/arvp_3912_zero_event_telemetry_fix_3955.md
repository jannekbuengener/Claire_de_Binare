# ARVP #3912 False Zero-Event Telemetry Fix (#3955)

Status Class: **ENGINEERING_FIX** — code/tests only; no runtime rerun  
Issue: [#3955](https://github.com/jannekbuengener/Claire_de_Binare/issues/3955)  
Parent observation: [#3912](https://github.com/jannekbuengener/Claire_de_Binare/issues/3912)  
Live-Readiness: **NO-GO**  
Echtgeld: **not authorized**

## Problem

Parallel natural-paper run #3912 reported `events_since_start=0` on both lanes at
terminal evaluation, although Donchian emitted **50** runtime signals.

Root causes:

1. **Runtime `signal_id` collision** — `generate_uuid_hex()` without an explicit
   `name` used a module-global deterministic counter that resets on container
   restart. Reused IDs hit `correlation_ledger` `ON CONFLICT DO NOTHING`, so no
   new rows appeared in the observation window.
2. **Supervisor global-only ledger count** — `probe_ledger` counted all ledger
   rows since `start_utc` without `bot_id` / `strategy_id` lane filters.

`TIMEOUT_NO_CHAIN` remains valid when no promotable SIGNAL→DECISION→ORDER→FILL
chain exists (e.g. 50× RC_001 under `HIGH_VOL_CHAOTIC`). Telemetry must still
surface lane activity separately from chain verdict.

## Fix (P0)

| Item | Change |
|------|--------|
| P0-1 | `format_runtime_signal_id()` / `generate_runtime_signal_id_hex()` (UUID4) for live runtime paths; deterministic IDs kept for stimulus/replay |
| P0-2 | `probe_ledger` exposes global + `bot_id` / `strategy_id` / `campaign_id` / `config_hash` scoped counts; supervisor cycle adds `event_count_since_start_lane` + `ledger_counts` |

## Non-goals

- No change to RC_001 / risk semantics
- No natural-paper promotion claim
- No runtime Docker execution in this slice
- LR **NO-GO** unchanged
