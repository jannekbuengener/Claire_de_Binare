# ARVP #3990 Candidate Evidence Package Assembly

**Date:** 2026-07-13  
**Issue:** [#4016](https://github.com/jannekbuengener/Claire_de_Binare/issues/4016)  
**Parent:** [#4013](https://github.com/jannekbuengener/Claire_de_Binare/issues/4013)  
**Blocks:** [#4017](https://github.com/jannekbuengener/Claire_de_Binare/issues/4017)  
**LR:** NO-GO  
**Evidence class:** `historical_cross_venue_research`  
**Outcome:** `READY_FOR_LEAGUE_TABLE`  
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

Repo crosscheck: `services/validation/arvp_candidate_evidence_assembler.py`, `tools/arvp_vacation/candidate_evidence_assembly.py`, live `queue_state.json`, GitHub issues #4013/#4016/#4017, PR #4021 merge.

---

## Packet Granularity

| Decision | Value |
|----------|-------|
| Granularity | **One PEP per candidate** (`strategy_id` + `parameter_fingerprint`) |
| Candidates (318-job campaign) | 3 (`donchian_breakout_v1`, `breakout_trend_filter_v1`, `primary_breakout_v1`) |
| Embedded slices | `arvp_evidence.economic_metric_summaries`, `scenario_sensitivity`, `split_stability`, `cost_evidence`, `stress_evidence` |
| `packet_id` contract | `pep-{strategy-slug}-binance-3990-{hash12}` from `candidate_id` + `source_content_hash` |
| Parameter fingerprint | `{strategy_id}:campaign_default_v1` (limitation: no parameter vector in upstream records) |

Development, validation, OOS, and stress remain separate via `purpose` + `window_class` slices. Scenarios `baseline`, `pessimistic_execution`, and `feed_gap` stay distinguishable.

---

## Source Coverage

| Field | Value |
|-------|-------|
| Campaign ID | `arvp_binance_historical_3990_2bb32b68_20260712T111944Z` |
| Source contract | `arvp_strategy_metrics.v1` |
| Source content hash | `ad3d4ccc449e81e4aa5ec81185d6b3229d12a9e05b2e4970dd352b7471e5b7ad` |
| Scenario records consumed | **954** (318 canonical jobs × 3 scenarios) |
| Superseded excluded | 6 |
| Source venue | Binance Spot BTCUSDT |

---

## Full-Campaign Assembly (read-only local validation)

| Candidate | evidence_packet_id | content_hash | rankability_status | baseline trade_count |
|-----------|-------------------|--------------|-------------------|----------------------|
| breakout_trend_filter_v1 | `pep-breakout-trend-filter-v1-binance-3990-ade758d43863` | `ad79a15ca78d50a5e8a6a1e801873d97828b49b27976eae87cf0b6acef2d9d93` | NOT_RANKABLE | 93968 |
| donchian_breakout_v1 | `pep-donchian-breakout-v1-binance-3990-74cfe5949a67` | `3c96422edef0ed0fbfb15211c47898dc1788cadcd6082cb1be261361ca0a303b` | NOT_RANKABLE | 118722 |
| primary_breakout_v1 | `pep-primary-breakout-v1-binance-3990-51895cd9c305` | `5800183fdc1f75a98885a08a8f050262d6f50b5672f277e2ca2d128f93d79298` | PARTIAL_EVIDENCE | 44 |

**Bundle hash (all candidates):** `4e7b4b88427d3fed84493721f97f82d0502c5a93ee96b81b8af8dab0671e26a4`

Identical re-run reproduced the same bundle hash on 2026-07-13.

CLI (read-only):

```bash
python -m tools.arvp_vacation.candidate_evidence_assembly \
  --queue-state artifacts/arvp_vacation/arvp_binance_historical_3990_2bb32b68_20260712T111944Z/queue_state.json

python -m tools.arvp_vacation.candidate_evidence_assembly \
  --queue-state artifacts/arvp_vacation/arvp_binance_historical_3990_2bb32b68_20260712T111944Z/queue_state.json \
  --hash-only
```

---

## Aggregation and Overlap Policy

- Quote PnL across overlapping month/quarter/year windows is **never summed** into total return.
- Month, quarter, and year aggregates are reported separately in `split_stability`.
- Overlap class treated as **descriptive non-i.i.d.** (`overlap_policy=descriptive_non_iid`).
- Missing metrics remain `null`; zero trades remain `0`.
- `fee_adjusted_max_drawdown_r` is never invented when absent.
- `slippage_availability=not_available`; slippage cost stays `0.0` with limitation.
- Regime fields remain window-level `regime_availability` context only.
- `paper_reference_status=not_run`, `same_venue_status=not_run`, `replay_vs_paper_status=not_run`.

---

## Contract Surface

- Assembler: `services/validation/arvp_candidate_evidence_assembler.py`
- CLI: `tools/arvp_vacation/candidate_evidence_assembly.py`
- PEP schema extensions (backward compatible): `docs/contracts/profitability_evidence_packet.v1.schema.json`
- Golden slice fixture: `tests/fixtures/arvp/candidate_evidence/slice_bundle_manifest.v1.json`

---

## Safety

- LR remains **NO-GO**
- `ranking_ready=false` on every packet
- Binance historical research only; not MEXC same-venue confirmation
- No promotion, paper-go, or live-go language authorized
- Exit gate for #4017: **READY_FOR_LEAGUE_TABLE**

---

## Validation

```bash
python -m pytest -q tests/unit/arvp/test_candidate_evidence_assembly.py
python -m pytest -q tests/unit/arvp/test_strategy_metric_extraction.py tests/unit/arvp/test_vacation_metric_availability_contract.py
python -m pytest -q tests/unit/validation/test_profitability_evidence_packet_assembler.py tests/unit/validation/test_profitability_league_scorer.py
ruff check services/validation/arvp_candidate_evidence_assembler.py tools/arvp_vacation/candidate_evidence_assembly.py tests/unit/arvp/test_candidate_evidence_assembly.py
python -m json.tool docs/contracts/profitability_evidence_packet.v1.schema.json
git diff --check
```

---

## Restunsicherheiten

- Full-campaign hashes depend on local campaign artifacts; CI validates via slice fixtures when artifacts are absent.
- Candidate-level `NOT_RANKABLE` for donchian/breakout_trend_filter reflects upstream per-window `rankable=false` flags (e.g. data-quality mismatch), not a new assembly override.
- League scoring semantics for cross-venue research packets are owned by #4017.
