# CDB Profitability — First Evidence Packet #3032

**Date:** 2026-06-12
**Parent:** #3032
**Status:** Partial (replay blocked, dataset validated, pipeline demonstrated)

## Brain Evidence

| Field | Value |
|-------|-------|
| `brain_source` | `repo-only` |
| `brain_status` | `not-used` |
| `tools_or_queries` | `git fetch`, `git status`, `git switch`, `python -m services.validation.strategy_replay_runner --dry-run`, `python -m services.validation.strategy_replay_runner` (full), `python hashlib sha256`, `gh issue view/list` |
| `records_or_results` | Dry-run PASS (3496 candles loaded). Full replay FAIL (regime_id=null in dataset). SHA-256 verified match. |
| `repo_crosscheck` | `core/contracts/primary_breakout_v1_config.py`, `core/replay/historical_bridge.py`, `docs/contracts/profitability_*.v1.schema.json` |
| `impact_on_plan` | Evidence pipeline shape is proven end-to-end; blocked at backtest execution by regime_id gap |
| `limitations` | No SurrealDB/Context Brain used. No DB access. Replay requires regime assignment. |

## Scope and Non-goals

### In scope

- Produce first concrete evidence packet against a committed MEXC same-venue dataset.
- Validate dataset quality against the profitability dataset quality gate schema.
- Register primary_breakout_v1 as a profitability candidate with real repo-live config.
- Exercise the end-to-end evidence pipeline: dataset -> quality report -> candidate -> evidence packet.
- Document the regime_id gap honestly and create a narrow follow-up.

### Non-goals

- No runtime, no DB, no Docker, no Redis.
- No Live-Go, no Echtgeld-Go, no LR status change.
- No strategy code changes, no schema changes.
- No fabrication of backtest metrics.
- No automatic promotion.

## Input Dataset

| Property | Value |
|----------|-------|
| Dataset ID | `mexc_strict_window_3091_island_3` |
| Source | `file` (exported from `public.candles_1m` via `cdb_readonly`) |
| Symbol | BTCUSDT |
| Venue | MEXC |
| Venue match | `true` |
| Window | 2026-06-06T13:43:00Z – 2026-06-08T23:58:00Z (58.3h) |
| Candles | 3,496/3,496 (100%) |
| Gaps | 0 |
| Quality grade | `strict_campaign_grade` |
| SHA-256 | `d79a1c3c81191dcf4418ae0c2b2775a6f354ed0cc6801a6955904871c4077605` |
| Evidence class | `controlled_lab_evidence` |
| Ref issues | #3091, #3086, #3092, #3133, #3138 |

The dataset originates from the MEXC WebSocket persistent capture pipeline (`cdb_ws -> cdb_candles -> cdb_db_writer -> candles_1m`) and was exported as file-backed artifacts under `artifacts/candles/mexc_strict_window_3091/`.

## Candidate

| Property | Value |
|----------|-------|
| Candidate ID | `cand-primary-breakout-v1-btcusdt-mexc-3091` |
| Strategy family | `primary_breakout` |
| Symbol | BTCUSDT |
| Timeframe | 1m |
| Direction | `long_only` |
| Status | `SPECIFIED` |
| Allowed next gate | `BACKTESTED` (blocked by regime_id gap) |

Config parameters sourced from `core/contracts/primary_breakout_v1_config.py` (repo-live, canonical):
- `entry_lookback_minutes`: 240
- `exit_lookback_minutes`: 120
- `breakout_buffer`: 0.0005
- `min_minutes_between_entries`: 60
- `trade_side_mode`: `long_only`

## Replay Execution

### Dry-run

```
python -m services.validation.strategy_replay_runner \
  --dataset-source file \
  --input-candles artifacts/candles/mexc_strict_window_3091/candles.jsonl \
  --strategy-id primary_breakout_v1 \
  --symbol BTCUSDT \
  --adapter-id primary_breakout_runner_v1 \
  --dry-run

DRY-RUN: config valid, dataset loaded. source='file', candles_total=3496.
Exit code: 0
```

### Full run

```
python -m services.validation.strategy_replay_runner \
  --dataset-source file \
  --input-candles artifacts/candles/mexc_strict_window_3091/candles.jsonl \
  --strategy-id primary_breakout_v1 \
  --symbol BTCUSDT \
  --adapter-id primary_breakout_runner_v1

ERROR: failed to derive execution provenance id: missing required field: regime_id
Exit code: 1
```

**Root cause:** `core/replay/historical_bridge.py:204` requires `_required_int(row, "regime_id")` for every candle row. In this dataset, all 3,496 rows have `regime_id: null` because the regime service was not active during MEXC WebSocket capture. The `build_primary_breakout_historical_bridge` function rejects null regime values.

## Dataset Quality Report

Full report: `docs/evidence/profitability_dataset_quality_report_mexc_3091.json`

Verdict: **PASS**

All seven checks pass with clean results:
- Coverage: 3,496/3,496 (100%)
- Missing candles: 0
- Duplicates: 0
- Out-of-order: 0
- Timeframe consistency: strict 1m cadence
- Symbol/window metadata: consistent
- Fingerprint: SHA-256 verified

## Evidence Packet

Full packet: `docs/evidence/profitability_evidence_packet_primary_breakout_v1_mexc_3091.json`

Status: **Partial** — pipeline structure demonstrated, execution blocked.

Key findings:
- All financial metrics are zero (placeholders) because no backtest ran.
- Scenario results: dry-run PASS, full-run FAIL (regime_id).
- Recommendation: **PARK** until regime assignment is available.

## Economics / Ranking Readiness

| Dimension | Status |
|-----------|--------|
| Dataset quality gate | PASS |
| Candidate contract | SPECIFIED |
| Evidence packet | Partial (execution blocked) |
| Execution economics | Not applicable (no trades) |
| League table input | Not applicable (no comparable metrics) |

## Decision

This is the **first concrete evidence packet** for the CDB Profitability Engine. It proves that the end-to-end pipeline can be constructed:

```
MEXC dataset -> Dataset Quality Report -> Candidate Contract -> Evidence Packet
```

However, the critical **regime_id gap** blocks backtest execution. Without regime assignment, `primary_breakout_v1` cannot produce trade signals through the historical bridge, and no financial metrics can be computed.

**Verdict:** Pipeline shape is validated. Dataset is validated. Execution is blocked. No promotion is authorized.

## Limitations

1. `regime_id` is null for all 3,496 rows. This is a data-layer gap, not a code bug.
2. File-backed dataset provider successfully loads candles, but the historical bridge requires integer regime values.
3. No natural paper evidence chain exists for this window (no SIGNAL->DECISION->ORDER->FILL).
4. Evidence class remains `controlled_lab_evidence` — this is correct and intentional.
5. All financial metrics in the evidence packet are explicit placeholders (0.0), not claims.

## Follow-ups

| ID | Title | Priority |
|----|-------|----------|
| (to be created) | [PROFITABILITY][REPLAY] Enable regime-assigned file-backed replay for MEXC datasets | High |
| (to be created) | [PROFITABILITY][ECONOMICS] Compute execution economics from first successful backtest | Medium |
| (to be created) | [PROFITABILITY][RANKING] Populate Strategy League Table with first comparable candidate | Medium |

## Safety Boundaries

- LR remains NO-GO.
- Board `trade-capable` stage does not authorize live capital.
- No Live-Go, no Echtgeld-Go.
- No runtime, no DB, no Docker.
- No promotion to BACKTESTED, ARVP_VALIDATED, or any downstream gate.
- Dataset evidence class is `controlled_lab_evidence`, not `natural_paper_evidence`.
- All zero-value metrics are explicit placeholders; they are not profitability claims.

## Produced Artifacts

| File | Path | Type |
|------|------|------|
| Dataset Quality Report | `docs/evidence/profitability_dataset_quality_report_mexc_3091.json` | JSON (schema-validated) |
| Candidate Contract | `docs/evidence/profitability_candidate_primary_breakout_v1.json` | JSON (schema-validated) |
| Evidence Packet | `docs/evidence/profitability_evidence_packet_primary_breakout_v1_mexc_3091.json` | JSON (schema-validated) |
| Evidence Doc | `docs/evidence/profitability_first_evidence_packet_mexc_3091.md` | Markdown (this file) |

## Ref Issues

- #3032 — Parent: Profitability Engine
- #3091 — MEXC future capture (dataset source)
- #3086 — MEXC same-venue data acquisition
- #3034 — Candidate Contract and Evidence Packet v1 (schema source)
- #3035 — Dataset Quality Gate v1 (schema source)
