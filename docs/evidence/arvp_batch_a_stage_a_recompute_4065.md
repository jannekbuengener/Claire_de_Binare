# Batch-A Stage-A Recompute (#4065 P3)

**Issue:** [#4065](https://github.com/jannekbuengener/Claire_de_Binare/issues/4065)  
**Campaign:** `batch_a_stage_a_d0a4e72d_20260713`  
**LR:** NO-GO · **ranking_ready:** false

---

## Source invariants (unchanged)

| Invariant | Value |
|---|---|
| queue_state SHA256 (before/after) | `4fc9dd45389de8d6ca5eec6ea3b2e97ea990c0c6a75dca5841eb53481a064842` |
| Jobs | 390 |
| Scenario records | 780 |
| Gate contract SHA256 | `714b183b8219eb07050d99dab1caaa65797142d2671c1128f2036ac7213bdefc` |
| Replay rerun | **NOT AUTHORIZED** |

---

## Deterministic re-extraction (A3)

Two independent runs from unmodified `queue_state.json`:

| Run | Output path | content_hash |
|---|---|---|
| 1 | `artifacts/.../arvp_strategy_metrics.v1.recompute_run1.json` | `ecddd1420e03a0dd06ae99087e19a4c0ec20afe09470cb001e5e664909b1d328` |
| 2 | `artifacts/.../arvp_strategy_metrics.v1.recompute_run2.json` | `ecddd1420e03a0dd06ae99087e19a4c0ec20afe09470cb001e5e664909b1d328` |

Record-by-record comparison: **identical** (same content_hash).

---

## Before / After verdict

| Metric | Before fix | After fix |
|---|---|---|
| metrics content_hash | `3ee5c429cc8d7df499e9870f1253f350f235ebe2a6974dbfcddbb1a7f8c60958` | `ecddd1420e03a0dd06ae99087e19a4c0ec20afe09470cb001e5e664909b1d328` |
| rankable records | 0 / 780 | 726 / 780 |
| warmup_trim_applied | 0 | 780 |
| zero-trade unrankable | 54 | 54 |
| STAGE_A_SURVIVOR | **0** | **0** |
| INSUFFICIENT_EVIDENCE | 10 | 1 (`range_mean_reversion_v1`) |
| REJECTED | 0 | 9 |

**Verdict sensitivity:** #4065 fix changes rankability and gate economics path (technical → economic/sample_size failures) but **does not produce survivors**.

---

## Repro

```bash
python -m tools.arvp_vacation.strategy_metric_extraction \
  --queue-state artifacts/arvp_vacation/batch_a_stage_a_d0a4e72d_20260713/queue_state.json \
  --output artifacts/evidence/batch_a_stage_a_d0a4e72d_20260713/arvp_strategy_metrics.v1.recompute_run1.json

python -m tools.arvp_vacation.strategy_metric_extraction \
  --queue-state artifacts/arvp_vacation/batch_a_stage_a_d0a4e72d_20260713/queue_state.json \
  --output artifacts/evidence/batch_a_stage_a_d0a4e72d_20260713/arvp_strategy_metrics.v1.recompute_run2.json
```

Exit gate: `STAGE_A_VERDICT_RECOMPUTED`
