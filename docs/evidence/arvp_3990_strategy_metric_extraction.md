# ARVP #3990 Strategy Metric Extraction Evidence

**Date:** 2026-07-13  
**Issue:** [#4015](https://github.com/jannekbuengener/Claire_de_Binare/issues/4015)  
**Parent:** [#4013](https://github.com/jannekbuengener/Claire_de_Binare/issues/4013)  
**Blocks:** [#4016](https://github.com/jannekbuengener/Claire_de_Binare/issues/4016)  
**LR:** NO-GO  
**Evidence class:** `historical_cross_venue_research`  
**Outcome:** `READY_FOR_CANDIDATE_EVIDENCE`  
**ranking_ready:** `false` (unchanged)

---

## Brain Evidence

| Field | Value |
|-------|-------|
| brain_source | repo-only |
| brain_status | not-used |
| context_brain_attempted | true |
| context_brain_used | false |
| repo_fallback_reason | insufficient_evidence |
| records_found | none |

Repo crosscheck: live `queue_state.json`, `tools/arvp_vacation/strategy_metric_extraction.py`, `docs/contracts/arvp_strategy_metrics.v1.schema.json`, GitHub issues #4013/#4015/#4016.

---

## Canonical Selection

| Field | Value |
|-------|-------|
| Campaign ID | `arvp_binance_historical_3990_2bb32b68_20260712T111944Z` |
| Selector | `superseded_by_stress_v2_rerun != true` |
| Queue records | 324 |
| Canonical jobs | **318** |
| Superseded excluded | **6** |
| Scenario records emitted | **954** (318 × 3 scenarios) |

Original legacy stress FAIL jobs and stress-v2 replacements are never aggregated together.

---

## Deterministic Content Hash

| Field | Value |
|-------|-------|
| Algorithm | SHA-256 over canonical JSON (`core.replay.canonical_json`) |
| Input set | Sorted list of per-record hashable payloads (318 canonical jobs × 3 scenarios) |
| Excluded from hash | `source_artifact_sha256` only |
| Content hash | `ad3d4ccc449e81e4aa5ec81185d6b3229d12a9e05b2e4970dd352b7471e5b7ad` |

Re-run command (read-only):

```bash
python -m tools.arvp_vacation.strategy_metric_extraction \
  --queue-state artifacts/arvp_vacation/arvp_binance_historical_3990_2bb32b68_20260712T111944Z/queue_state.json \
  --hash-only
```

Second identical run reproduced the same hash on 2026-07-13.

---

## Contract and Mapping

- Output contract: [`docs/contracts/arvp_strategy_metrics.v1.schema.json`](../contracts/arvp_strategy_metrics.v1.schema.json)
- Input contract: [`docs/contracts/arvp_vacation_job_metrics.v1.schema.json`](../contracts/arvp_vacation_job_metrics.v1.schema.json)
- Availability matrix: [`docs/evidence/arvp_3990_metric_availability_matrix.md`](arvp_3990_metric_availability_matrix.md)
- Summary mapping fix: `tools/arvp_vacation/summary.py` reads nested `metrics.*` first, legacy aliases second
- Missing semantics: absent/null stays null; zero trades stay `0`; `rankable=false` when `closed_trades_total == 0`
- Slippage: `slippage_availability=not_available` (no invented per-trade slippage)
- Candles: deterministic fallback prefers `candles_live`, else `candles_total`; mismatch flagged in `data_quality_flags`

---

## PR #4019 Review Findings Resolved

| Finding | Resolution |
|---------|------------|
| schema-version-writer | Every record and bundle emit `schema_version=arvp_strategy_metrics.v1` |
| slippage-path | `slippage_availability=not_available`; no fabricated slippage metric |
| candle-count-path | `resolve_candles_total()` with live→total fallback and mismatch flag |

---

## Safety

- LR remains **NO-GO**
- `ranking_ready=false`
- Binance historical research only; not MEXC same-venue confirmation
- No replay reruns, no campaign artifact mutation, no promotion language

---

## Exit Gate for #4016

Child 2 delivers versioned normalized metrics and a stable campaign content hash.  
**Exit gate:** `READY_FOR_CANDIDATE_EVIDENCE`
