# Replay vs Runtime Dataset Integrity Contract (CDB-051)

Status: Canonical for Correctness slice `#4336`  
Schema: `cdb.replay_vs_runtime_data_rules.v1`  
Code SSOT: [`core/replay/dataset_integrity_rules.py`](../../core/replay/dataset_integrity_rules.py)

## Purpose

Make Gap / Duplicate / Out-of-order / Cadence behavior explicit and
machine-testable. Document the intentional Replay vs Runtime asymmetry
without mutating the BLUE candle runtime stack.

## Parity claim

`parity_claim = asymmetric` — Replay fail-closed; Runtime may update OHLC on
late ticks. This is **not** replay parity.

## Replay (fail-closed)

| Fault | Behavior | Reason code |
| --- | --- | --- |
| Empty series | Block | `EMPTY_SERIES` |
| Non-increasing timestamps | Block | `OUT_OF_ORDER` |
| Identical duplicate timestamp | Block | `DUPLICATE_IDENTICAL` |
| Conflicting duplicate timestamp | Block | `DUPLICATE_CONFLICTING` |
| Candle(s) outside / short of bound window | Block | `INCOMPLETE_WINDOW` |
| Missing interval in requested window | Block | `GAP` |
| Non-60000 ms step | Block | `CADENCE_VIOLATION` |

Root-cause priority (stable): `EMPTY_SERIES` > `OUT_OF_ORDER` >
`DUPLICATE_CONFLICTING` > `DUPLICATE_IDENTICAL` > `INCOMPLETE_WINDOW` >
`GAP` > `CADENCE_VIOLATION`.

Window binding uses the **final** `DatasetSpec` warmup→end range
(`warmup_start_ms(spec)` … `end_ts_ms`). CDB-049 exact-window remains the
edge-equality contract; CDB-051 owns gap/dup/ooo/cadence codes.

Consumers (`DatasetLoadError`, `ReplayRunnerError`,
`BinanceWindowBankAdapterError`) must preserve `.code`.

Content-fingerprint normalization may sort by `ts_ms`, but only with
deterministic `normalization_evidence`. Sorting never hides an integrity
finding from DQ / rankability.

## Runtime candles (documented difference)

`services/candles` may still update the current window OHLC when a late tick
arrives. Missing minutes are not synthesized. This is **not** claimed as
replay parity and must not be silently reconciled in research provenance.

Executable asymmetry is covered by
`tests/unit/replay/test_dataset_integrity_rules_cdb051.py::test_cdb051_executable_runtime_asymmetry_ooo`.

## Non-goals

- No DQ threshold tuning
- No Stage-A/B gate changes
- No runtime stack mutation in `#4336`
- No CDB-052 rankability / stale-manifest work
