# ARVP Runtime signal_id Collision Regression Fix (#3970)

Status Class: **ENGINEERING_FIX** — code/tests only; no runtime rerun  
Issue: [#3970](https://github.com/jannekbuengener/Claire_de_Binare/issues/3970)  
Failed diagnostic: [#3967](https://github.com/jannekbuengener/Claire_de_Binare/issues/3967) / PR [#3968](https://github.com/jannekbuengener/Claire_de_Binare/pull/3968)  
Prior P0 fix: [#3955](https://github.com/jannekbuengener/Claire_de_Binare/issues/3955) / PR [#3956](https://github.com/jannekbuengener/Claire_de_Binare/pull/3956)  
Live-Readiness: **NO-GO**  
Echtgeld: **not authorized**

## Problem (#3967)

Donchian emitted **10** runtime signals (container logs) but supervisor/ledger reported **0/0**.
All 10 `signal_id` values already existed in `correlation_ledger` (first_seen `2026-02-15`).
`INSERT … ON CONFLICT (event_pk) DO NOTHING` suppressed rows silently; telemetry read as zero activity.

## Root cause (evidence-based)

| Factor | Finding |
|--------|---------|
| Code path on `main` post-#3956 | Donchian/PB1 use `format_runtime_signal_id()` (UUID4) |
| Pre-#3956 runtime path | `generate_uuid_hex(length=32)` without `name` → deterministic counter reuse after restart |
| #3967 timing | #3956 merged `2026-07-10T10:04:51Z`; execute window `11:30Z` — **likely stale signal containers** not rebuilt |
| Secondary gap | `_persist_correlation_event` treated `ON CONFLICT` as success (`return True`) |
| ID discard gap | Strategy adapter dropped pre-assigned `signal_id` from Donchian/PB1 before publish |

## Fix (P0 regression)

| ID | Change |
|----|--------|
| P0R-1 | Preserve `signal_id` on `StrategySignalCandidate`; `_signal_from_candidate` keeps strategy-assigned runtime IDs |
| P0R-2 | `CorrelationLedgerInsertResult`; conflict on `rowcount==0`; Prometheus `correlation_ledger_insert_conflicts_total`; supervisor `ledger_telemetry_risk` via `probe_signal_metrics` |
| P0R-3 | Preflight `runtime_freshness.expected_source_sha` + rebuild note (`CDB_SOURCE_SHA` marker env) |

## Validation (this slice)

- `pytest tests/unit/arvp/test_arvp_runtime_signal_id_collision_regression_3970.py`
- `pytest tests/unit/replay/test_correlation_ledger_insert.py`
- No runtime execution; no productive DB writes

## Non-goals

- Does not change #3967 verdict
- No strategy/risk semantics change
- No promotion claim
- LR **NO-GO** unchanged

## Remaining uncertainty

Runtime re-verification requires a future execute slice with **rebuilt signal images** matching post-#3970 `expected_source_sha`.
