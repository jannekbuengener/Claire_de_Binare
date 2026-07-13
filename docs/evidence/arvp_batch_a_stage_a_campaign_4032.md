# ARVP Batch-A Stage-A Development Screening Campaign — Issue #4032

**Date:** 2026-07-13  
**Issue:** [#4032](https://github.com/jannekbuengener/Claire_de_Binare/issues/4032)  
**Control:** [#4029](https://github.com/jannekbuengener/Claire_de_Binare/issues/4029)  
**Source SHA:** `436209d8` (preflight/coordinator #4059) | Gate: `d0a4e72d` (#4058)  
**LR:** NO-GO | **`ranking_ready`:** `false`

---

## Campaign

| Field | Value |
|-------|-------|
| Campaign ID | `batch_a_stage_a_d0a4e72d_20260713` |
| Coordinator jobs | 390 |
| Scenario runs | 780 (`baseline` + `pessimistic_execution`) |
| Strategies | 10 Batch-A candidates |
| Development windows | 39 (locked #4030 selection) |
| Technical outcome | **390 PASS / 0 FAIL** |
| Wall clock | 2026-07-13T03:18:48Z → 03:38:01Z (~19 min) |
| Metrics content hash | `3ee5c429cc8d7df499e9870f1253f350f235ebe2a6974dbfcddbb1a7f8c60958` |

---

## Stage-A survivor verdict (`STAGE_A_SURVIVOR` tier)

| Status | Count |
|--------|------:|
| `STAGE_A_SURVIVOR` | **0** |
| `REJECTED` | 0 |
| `INSUFFICIENT_EVIDENCE` | **10** |

All ten candidates are **`INSUFFICIENT_EVIDENCE`** at the Stage-A gate tier. No candidate advances to Stage-B confirmation (#4033).

**Primary rankability blocker:** metric extraction flagged `candles_live_candles_total_mismatch` on 726/780 scenario records (warmup-trimmed `candles_live` ≠ window `candles_total` in dataset summary). Secondary: `zero_closed_trades_total` on 54 records.

This is a **screening outcome**, not a promotion or ranking-ready claim.

---

## Repro commands

```bash
# Preflight (after #4059 on main)
python -m tools.arvp_vacation.coordinator \
  --manifest artifacts/arvp_vacation/manifests/batch_a_stage_a_d0a4e72d.yaml \
  --preflight-only

# Campaign (resume-safe)
python -m tools.arvp_vacation.coordinator \
  --manifest artifacts/arvp_vacation/manifests/batch_a_stage_a_d0a4e72d.yaml \
  --run-until-complete --write-summary --resume

# Metric extraction
python -m tools.arvp_vacation.strategy_metric_extraction \
  --queue-state artifacts/arvp_vacation/batch_a_stage_a_d0a4e72d_20260713/queue_state.json \
  --output artifacts/evidence/batch_a_stage_a_d0a4e72d_20260713/arvp_strategy_metrics.v1.json

# Survivor scoring (all candidates)
python -c "
from pathlib import Path
import json
from core.replay.batch_a_strategy_registry import batch_a_strategy_ids
from tools.arvp_vacation.batch_a_stage_a_survivor_scorer import score_stage_a_candidates, result_to_dict
records = json.loads(Path('artifacts/evidence/batch_a_stage_a_d0a4e72d_20260713/arvp_strategy_metrics.v1.json').read_text())['records']
results = score_stage_a_candidates(records=records, candidate_ids=batch_a_strategy_ids())
print({cid: r.status for cid, r in sorted(results.items())})
"
```

---

## Artifacts (local, gitignored)

| Path | Purpose |
|------|---------|
| `artifacts/arvp_vacation/batch_a_stage_a_d0a4e72d_20260713/queue_state.json` | Campaign queue |
| `artifacts/arvp_vacation/batch_a_stage_a_d0a4e72d_20260713/vacation_summary.json` | Coordinator summary |
| `artifacts/evidence/batch_a_stage_a_d0a4e72d_20260713/arvp_strategy_metrics.v1.json` | Normalized metrics (780 records) |

Versioned summary: [`arvp_batch_a_stage_a_survivor_summary_4032.v1.json`](arvp_batch_a_stage_a_survivor_summary_4032.v1.json)

---

## Downstream routing

| Issue | Action |
|-------|--------|
| #4033 (WP4 Stage-B) | `NOT_APPLICABLE_NO_SURVIVORS` |
| #4034 (WP5 league) | Advisory only; no promotion path |
| #4032 | Close after this Evidence-PR merge |

---

## Boundaries

- Binance cross-venue development screening only
- Does not use `profitability_league_scorer.hard_gate_failures`
- No live capital, LR **NO-GO**
