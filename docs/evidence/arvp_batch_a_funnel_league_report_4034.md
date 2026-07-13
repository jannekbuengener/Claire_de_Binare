# ARVP Batch-A Funnel League Closeout — Issue #4034

**Date:** 2026-07-13  
**Issue:** [#4034](https://github.com/jannekbuengener/Claire_de_Binare/issues/4034)  
**Control:** [#4029](https://github.com/jannekbuengener/Claire_de_Binare/issues/4029)  
**Epic:** [#1900](https://github.com/jannekbuengener/Claire_de_Binare/issues/1900)  
**Plan:** `arvp-funnel-v1.1-2026-07-13` (Dual-GO, NO_SURVIVORS path)  
**Evidence class:** `historical_cross_venue_research`  
**Funnel verdict:** `HISTORICAL_FUNNEL_NO_SURVIVORS`  
**LR:** NO-GO · **promotion_status:** NOT_AUTHORIZED

---

## Source lineage

| WP | Issue | Status | Evidence |
|----|-------|--------|----------|
| WP1 | #4030 | CLOSED | Development window lock (39) |
| WP2 | #4031 | CLOSED | 10 runners executable |
| WP3 | #4032 | CLOSED | Stage-A campaign + survivor scoring |
| WP4 | #4033 | N/A | `NOT_APPLICABLE_NO_SURVIVORS` |
| WP5 | #4034 | this closeout | League reconcile (advisory) |

| Field | Value |
|-------|-------|
| Campaign ID | `batch_a_stage_a_d0a4e72d_20260713` |
| Source SHA (closeout) | `044ad3c4` |
| Metrics content hash | `3ee5c429cc8d7df499e9870f1253f350f235ebe2a6974dbfcddbb1a7f8c60958` |
| Closeout report hash | `7402da3c1b3345b40aeab2c5e9b786dfc66136eb9281fb52f269eff6c61be867` |
| Scenario records | 780 (390 jobs × 2 scenarios) |
| Technical jobs | 390/390 PASS |

Upstream evidence: [`arvp_batch_a_stage_a_campaign_4032.md`](arvp_batch_a_stage_a_campaign_4032.md), [`arvp_batch_a_stage_a_survivor_summary_4032.v1.json`](arvp_batch_a_stage_a_survivor_summary_4032.v1.json)

---

## League / funnel result (deterministic closeout)

| Field | Value |
|-------|-------|
| `funnel_verdict` | **`HISTORICAL_FUNNEL_NO_SURVIVORS`** |
| `table_status` | `PARTIAL` |
| `ranking_ready` | `false` |
| `official_ranking` | `[]` |
| `winner` | `null` |
| `officially_ranked_count` | `0` |
| `stage_a_survivor_count` | `0` |
| `stage_a_insufficient_count` | `10` |

All ten Batch-A candidates remain **`INSUFFICIENT_EVIDENCE`** at the Stage-A survivor tier (A1 gate). No candidate is eligible for Stage-B confirmation or official league ranking.

Machine-readable ledger: [`arvp_batch_a_funnel_league_report_4034.v1.json`](arvp_batch_a_funnel_league_report_4034.v1.json)

---

## League CLI applicability

`python -m tools.arvp_vacation.league_table_report --assemble-from-queue-state …` **was not used** for the final closeout hash on `main` @ `044ad3c4`:

- Metrics bundle schema drift (`regime_stats` field from #4056 not yet in `arvp_strategy_metrics.v1.schema.json`) blocks PEP assembly.
- This does **not** change the funnel verdict: zero survivors ⇒ empty official ranking regardless.

The closeout ledger above is the authoritative WP5 artifact for the NO_SURVIVORS path.

---

## Rankability / screening limitations

| Blocker | Count (of 780 records) |
|---------|----------------------:|
| `candles_live_candles_total_mismatch` | 726 |
| `zero_closed_trades_total` | 54 |

Warmup-trimmed replay `candles_live` differs from window-bank `candles_total` in dataset summaries. Metric extraction flags this as non-rankable; Stage-A paired economics gates therefore see zero rankable windows for all candidates.

This is documented as a **measurement/rankability policy gap**, not evidence of strategy promotion.

---

## Why no official winner

1. Zero `STAGE_A_SURVIVOR` after A1 paired pessimistic gate scoring.
2. Zero candidates with rankable baseline/pessimistic pairs for economics gates.
3. Stage-B (#4033) not applicable.
4. Paper reference and MEXC same-venue confirmation remain `not_run`.
5. `promotion_status=NOT_AUTHORIZED`; LR remains **NO-GO**.

---

## Repro (closeout regeneration)

```bash
# Survivor summary already versioned; regenerate closeout JSON:
python - <<'PY'
import json
from pathlib import Path
from core.replay.batch_a_strategy_registry import batch_a_strategy_ids
from core.replay.canonical_json import canonical_hash

survivor = json.loads(
    Path("docs/evidence/arvp_batch_a_stage_a_survivor_summary_4032.v1.json").read_text()
)
# See docs/evidence/arvp_batch_a_funnel_league_report_4034.v1.json for full payload
PY
```

Full campaign repro: see [`arvp_batch_a_stage_a_campaign_4032.md`](arvp_batch_a_stage_a_campaign_4032.md).

---

## Safety boundaries

- Binance historical research ≠ MEXC production confirmation
- No strategy promotion, paper-go, live-go, or capital authorization
- Descriptive `candidate_rows` must not be read as an official ranking
- Does not invoke `profitability_league_scorer.hard_gate_failures` for survivor tier

---

## Validation

```text
pytest -q tests/unit/arvp/test_batch_a_stage_a_survivor_scorer.py
pytest -q tests/unit/arvp/test_batch_a_stage_a_manifest.py
# Campaign evidence: 390/390 PASS queue_state (local artifacts)
```
