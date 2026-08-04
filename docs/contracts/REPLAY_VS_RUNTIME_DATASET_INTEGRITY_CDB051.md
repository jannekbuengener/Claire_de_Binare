# Replay vs Runtime Dataset Integrity Contract (CDB-051)

Status: Canonical for Correctness slice `#4336`  
Schema: `cdb.replay_vs_runtime_data_rules.v1`  
Code SSOT: [`core/replay/dataset_integrity_rules.py`](../../core/replay/dataset_integrity_rules.py)

## Purpose

Make Gap / Duplicate / Out-of-order / Cadence behavior explicit and
machine-testable. Document the intentional Replay vs Runtime asymmetry
without mutating the BLUE candle runtime stack.

## Replay (fail-closed)

| Fault | Behavior | Reason code |
| --- | --- | --- |
| Missing interval in requested window | Block load / mark not replay-ok | `GAP` |
| Identical duplicate timestamp | Block | `DUPLICATE_IDENTICAL` |
| Conflicting duplicate timestamp | Block | `DUPLICATE_CONFLICTING` |
| Non-increasing timestamps | Block | `OUT_OF_ORDER` |
| Non-60000 ms step | Block | `CADENCE_VIOLATION` |

Content-fingerprint normalization may sort by `ts_ms`, but only with
deterministic `normalization_evidence`. Sorting never hides an integrity
finding from DQ / rankability.

## Runtime candles (documented difference)

`services/candles` may still update the current window OHLC when a late tick
arrives. Missing minutes are not synthesized. This is **not** claimed as
replay parity and must not be silently reconciled in research provenance.

## Non-goals

- No DQ threshold tuning
- No Stage-A/B gate changes
- No runtime stack mutation in `#4336`
