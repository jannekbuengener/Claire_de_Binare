# ARVP Pack-A Wave-1 Shape/Replay Evidence (#3780)

Status Class: offline shape/replay execute (no promotion, no paper claim)
Issue: #3780
Parent: #1900
Spec: #3748
Live-Readiness: **NO-GO**
Echtgeld: **not authorized**
ranking_ready: **false**
natural_paper_evidence: **false**

## Brain Evidence

```text
brain_source: repo-only
brain_status: not-used
tools_or_queries:
  - git fetch/status/rev-parse; gh issue view 3780,3748,3747,3742,1900
  - MCP cdb_context_briefing attempted — unknown_tool on context_briefing alias
  - run_pack_a_wave1_shape_replay_3780.py offline replay execution
records_or_results:
  - context_brain_attempted=true; context_brain_used=false; context_available=false
  - repo_fallback_reason=tool_blocked; records_found=none
  - HEAD=7939465ba608e26805aaf479e69aaf87c42c2194
  - dataset_sha256=3be2430b5e30845b1db8d3330fc5e6b5d2b322dabf834db4bc2efaad379b30a7
repo_crosscheck:
  - docs/evidence/arvp_pack_a_breakout_baseline_spec_3748.md
  - services/validation/strategy_replay_runner.py
  - core/replay/scenario_packs.py
impact_on_plan:
  - Implemented minimal Donchian + Breakout+Trend adapters; executed Top-3 offline.
limitations:
  - No SurrealDB records; B1 friction gap unchanged; #3035 formal report not re-emitted.
  - deterministic_replay_ok two-pass only for primary_breakout_v1.
context_brain_attempted: true
context_brain_used: false
context_available: false
repo_fallback_used: true
repo_fallback_reason: tool_blocked
context_tool_status: partial
context_trust_level: none
records_found: none
```

## Scope and Human-GO boundary

- Offline replay only; no Docker paper runtime; no fresh-paper observation.
- ranking_ready=false; no natural_paper_evidence; LR NO-GO unchanged.
- PB1 PARKED reference only — no rescue/promotion.

## Dataset and quality gate

| Field | Value |
|-------|-------|
| path | `artifacts/backtests/primary_breakout_v1/20260418-212643/dataset.candles.json` |
| sha256 | `3be2430b5e30845b1db8d3330fc5e6b5d2b322dabf834db4bc2efaad379b30a7` |
| symbol | BTCUSDT |
| timeframe | 1m |
| #3035 report | not re-emitted — technical replay validity only (WARNING banner) |

## Execution matrix

| strategy_id | role | scenarios | exit | verdict | sub_status |
|-------------|------|-----------|------|---------|------------|
| `primary_breakout_v1` | PARKED reference anchor | baseline,pessimistic_execution,feed_gap | 0 | **PASS** | NOT_RANKING_READY |
| `donchian_breakout_v1` | external breakout benchmark | baseline,pessimistic_execution,feed_gap | 0 | **PASS** | NOT_RANKING_READY |
| `breakout_trend_filter_v1` | breakout + trend gate comparison | baseline,pessimistic_execution,feed_gap | 0 | **PASS** | NOT_RANKING_READY |

## Scenario results (summary)

### `primary_breakout_v1`

- artifact_root: `D:\Dev\Workspaces\Repos\Claire_de_Binare\artifacts\replay_reports\pack_a_wave1_3780\primary_breakout_v1`
- manifest: `D:\Dev\Workspaces\Repos\Claire_de_Binare\artifacts\replay_reports\pack_a_wave1_3780\primary_breakout_v1\pack_a_wave1_primary_breakout_v1\scenario_group_manifest.json`
- dataset_fingerprint: `619bee3a98e144327e0fe6a0c3ad871bd90e528bae56a9330229310bd37f8bf1`

```json
{
  "failed_count": 0,
  "group_fingerprint": "619bee3a98e144327e0fe6a0c3ad871bd90e528bae56a9330229310bd37f8bf1",
  "group_id": "pack_a_wave1_primary_breakout_v1",
  "scenarios": {
    "baseline": {
      "closed_trades_total": 22,
      "fee_adjusted_return_r": null,
      "max_drawdown_r": 0.022599448094972167,
      "ranking_ready": false,
      "run_id": "bt-b70fe2a4d0ffa5d5",
      "signals_total": 44
    },
    "feed_gap": {
      "closed_trades_total": 22,
      "fee_adjusted_return_r": null,
      "max_drawdown_r": 0.022599448094972167,
      "ranking_ready": false,
      "run_id": "bt-b3eaf255c7b8847b",
      "signals_total": 44
    },
    "pessimistic_execution": {
      "closed_trades_total": 22,
      "fee_adjusted_return_r": null,
      "max_drawdown_r": 0.09599382134120939,
      "ranking_ready": false,
      "run_id": "bt-d8a225e60396f6f0",
      "signals_total": 44
    }
  },
  "succeeded_count": 3
}
```

### `donchian_breakout_v1`

- artifact_root: `D:\Dev\Workspaces\Repos\Claire_de_Binare\artifacts\replay_reports\pack_a_wave1_3780\donchian_breakout_v1`
- manifest: `D:\Dev\Workspaces\Repos\Claire_de_Binare\artifacts\replay_reports\pack_a_wave1_3780\donchian_breakout_v1\pack_a_wave1_donchian_breakout_v1\scenario_group_manifest.json`
- dataset_fingerprint: `5f4bcf8d9de0a7ad89b4f2db2a81d8925c008126ee3cfc50aa7953e96ab965cd`

```json
{
  "failed_count": 0,
  "group_fingerprint": "5f4bcf8d9de0a7ad89b4f2db2a81d8925c008126ee3cfc50aa7953e96ab965cd",
  "group_id": "pack_a_wave1_donchian_breakout_v1",
  "scenarios": {
    "baseline": {
      "closed_trades_total": 257,
      "fee_adjusted_return_r": -0.5343919736115524,
      "max_drawdown_r": 0.2518220297440353,
      "ranking_ready": false,
      "run_id": "c6c9f0ee-d45e-51ee-bf80-c8b5244ba12c",
      "signals_total": 257
    },
    "feed_gap": {
      "closed_trades_total": 257,
      "fee_adjusted_return_r": -0.5343919736115524,
      "max_drawdown_r": 0.2518220297440353,
      "ranking_ready": false,
      "run_id": "1cfebf0e-40dc-5740-92ea-1ca42be52d65",
      "signals_total": 257
    },
    "pessimistic_execution": {
      "closed_trades_total": 257,
      "fee_adjusted_return_r": -1.814294411804425,
      "max_drawdown_r": 1.506798159070276,
      "ranking_ready": false,
      "run_id": "c049d0be-05d0-58f1-8321-da9ba06644ab",
      "signals_total": 257
    }
  },
  "succeeded_count": 3
}
```

### `breakout_trend_filter_v1`

- artifact_root: `D:\Dev\Workspaces\Repos\Claire_de_Binare\artifacts\replay_reports\pack_a_wave1_3780\breakout_trend_filter_v1`
- manifest: `D:\Dev\Workspaces\Repos\Claire_de_Binare\artifacts\replay_reports\pack_a_wave1_3780\breakout_trend_filter_v1\pack_a_wave1_breakout_trend_filter_v1\scenario_group_manifest.json`
- dataset_fingerprint: `102b75b96c87912412da8a1d0a96239f0ad48f624cc6a1617f2f9bb8988e3d1a`

```json
{
  "failed_count": 0,
  "group_fingerprint": "102b75b96c87912412da8a1d0a96239f0ad48f624cc6a1617f2f9bb8988e3d1a",
  "group_id": "pack_a_wave1_breakout_trend_filter_v1",
  "scenarios": {
    "baseline": {
      "closed_trades_total": 196,
      "fee_adjusted_return_r": -0.3848198624310175,
      "max_drawdown_r": 0.18497702709796682,
      "ranking_ready": false,
      "run_id": "bac30548-485b-5dc8-8410-38a1abb233ef",
      "signals_total": 196
    },
    "feed_gap": {
      "closed_trades_total": 196,
      "fee_adjusted_return_r": -0.3848198624310175,
      "max_drawdown_r": 0.18497702709796682,
      "ranking_ready": false,
      "run_id": "317aab23-b7e6-52ab-82bf-fec15d024ee1",
      "signals_total": 196
    },
    "pessimistic_execution": {
      "closed_trades_total": 196,
      "fee_adjusted_return_r": -1.3610456916799083,
      "max_drawdown_r": 1.1277676132807168,
      "ranking_ready": false,
      "run_id": "254beabf-5394-5f33-952d-633c95339d86",
      "signals_total": 196
    }
  },
  "succeeded_count": 3
}
```

## Deterministic rerun parity

- Scenario group manifests with `failed_count=0` treated as deterministic rerun OK for this slice.
- Pack-A Donchian/Bo+Trend runners use single-pass reports (`deterministic_replay_ok=false` by design).
- PB1 retains native two-pass determinism check when run standalone.

## Limitations

- B1 same-venue friction evidence missing (#3747) — economics advisory only.
- ranking_ready=false for all candidates.
- No §5.2.4 / Product-Complete / natural_paper_evidence claim.
- LR remains NO-GO.

Generated: 2026-07-06T10:08:45.263541+00:00
