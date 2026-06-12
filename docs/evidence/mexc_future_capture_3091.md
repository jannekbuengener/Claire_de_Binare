# MEXC Same-Venue File-Backed Dataset — #3091 Export-First Slice

**Date:** 2026-06-12
**Issue:** #3091
**Status:** File-backed dataset committed; no fresh runtime capture was required.

## Brain Evidence

| Field | Value |
|-------|-------|
| `brain_source` | `repo-only` |
| `brain_status` | `not-used` |
| `tools_or_queries` | `gh issue view`, `gh pr list`, `gh pr view`, `git fetch`, `git switch`, `git rebase`, `python psycopg2 readonly SELECT`, `python hashlib sha256` |
| `records_or_results` | 3496 rows exported; identity `cdb_readonly` confirmed; SELECT on candles_1m verified; 0 overlapping backfill rows; SHA-256 `d79a1c3c...` |
| `repo_crosscheck` | `artifacts/candles/mexc_strict_window_3091/`, `docs/evidence/mexc_same_venue_data_quality_policy_3091.md`, PR #3133, PR #3138 |
| `impact_on_plan` | Export-first path unblocked after #3138 grant apply; dataset now committed as file-backed artifact |
| `limitations` | No SurrealDB/Context Brain used. No continuity check against DB (requires writable connection). Window data validated via readonly SELECT identity/probe. |

## Scope and Non-goals

### In scope

- Export the already captured strict-qualified MEXC window (Island #3) from `public.candles_1m` via `cdb_readonly`.
- Produce file-backed `candles.jsonl` and update metadata/evidence artifacts.
- Demonstrate `venue=mexc`, `venue_match=true` via WS persistent capture provenance.
- Open PR with validation and wait for required checks.

### Non-goals

- No fresh runtime capture. No Docker compose actions.
- No DB schema changes, no DB writes.
- No strategy changes, no trading execution.
- No Live-Go / Echtgeld-Go.
- No synthetic/ersatz data.

## Relationship to #3133 and #3138

- **PR #3133** (`84f6b77f`): DB-backed strict-window qualification (data quality policy, Island #3 selected, 3496/3496, 0 gaps). Source was `db` at that point.
- **PR #3138** (`c69a9a4b`): Readonly grant contract — `candles_1m` added to `cdb_reader` SELECT list. Operator applied locally before export.
- **This slice**: Converts the DB-qualified window into a committed file-backed dataset (`candles.jsonl`), sets `source=file` in `dataset_spec.json`, and adds export provenance.

## Selected Strict Window

| Property | Value |
|----------|-------|
| Window ID | `mexc_strict_window_3091_island_3` |
| Symbol | BTCUSDT |
| Venue | MEXC (same-venue) |
| Start (UTC) | 2026-06-06T13:43:00Z |
| End (UTC) | 2026-06-08T23:58:00Z |
| Duration | 3,496 minutes (58.3h) |
| Candles | 3,496/3,496 (100%) |
| Gaps | 0 |
| Quality grade | `strict_campaign_grade` |
| Backfill overlap | 0 rows (pure WS capture) |

## Readonly DB Export

| Check | Result |
|-------|--------|
| Identity | `current_user=cdb_readonly`, `session_user=cdb_readonly` |
| `candles_1m` SELECT | true |
| `candles_1m` INSERT | false |
| `candles_1m` UPDATE | false |
| `candles_1m` DELETE | false |
| Window rows | 3496 |
| Window ts_ms range | 1780753380000 – 1780963080000 |
| Overlapping backfill rows | 0 |
| Export format | JSONL, one candle per line |
| Export path | `artifacts/candles/mexc_strict_window_3091/candles.jsonl` |
| Export principal | `cdb_readonly` via `POSTGRES_READONLY_PASSWORD_DSN` |

## Artifact Bundle

| File | Path | SHA-256 |
|------|------|---------|
| Candle dataset | `artifacts/candles/mexc_strict_window_3091/candles.jsonl` | `d79a1c3c81191dcf4418ae0c2b2775a6f354ed0cc6801a6955904871c4077605` |
| Dataset spec | `artifacts/candles/mexc_strict_window_3091/dataset_spec.json` | (committed) |
| Provenance manifest | `artifacts/candles/mexc_strict_window_3091/provenance_manifest.json` | (committed) |
| Gap report | `artifacts/candles/mexc_strict_window_3091/gap_report.json` | (from PR #3133) |
| Provenance (human) | `artifacts/candles/mexc_strict_window_3091/provenance.md` | (committed) |
| Evidence doc | `docs/evidence/mexc_future_capture_3091.md` | (this file) |

## Dataset Spec

Key fields in the updated `dataset_spec.json`:

| Field | Value |
|-------|-------|
| `source` | `file` |
| `file_path` | `artifacts/candles/mexc_strict_window_3091/candles.jsonl` |
| `venue` | `mexc` |
| `venue_match` | `true` |
| `candles_sha256` | `d79a1c3c81191dcf4418ae0c2b2775a6f354ed0cc6801a6955904871c4077605` |
| `provenance.no_runtime_capture_in_this_slice` | `true` |
| `provenance.export_principal` | `cdb_readonly` |
| `replay_compatibility.provider` | `FileBackedDatasetProvider` |

## Continuity / Gap Validation

The gap report from PR #3133 remains valid:
- 3,496/3,496 candles, 0 gaps, `strict_campaign_grade`.
- `candle_continuity check-window` was not re-run because it uses a writable DB connection path. The readonly DB probe confirmed identical row count (3496) and timestamp range (1780753380000–1780963080000). 0 overlapping backfill rows confirmed.

## File-backed Replay Load Validation

```bash
python -m services.validation.strategy_replay_runner \
  --dataset-source file \
  --input-candles artifacts/candles/mexc_strict_window_3091/candles.jsonl \
  --strategy-id primary_breakout_v1 \
  --symbol BTCUSDT \
  --adapter-id primary_breakout_runner_v1 \
  --dry-run
```

## No-Trading Safety Boundaries

| Boundary | Status |
|----------|--------|
| LR remains NO-GO | Confirmed |
| No Live-Go / Echtgeld-Go | Confirmed |
| No runtime capture | Confirmed (export-only from existing DB window) |
| No Docker compose actions | Confirmed |
| No DB writes | Confirmed (readonly SELECT only) |
| No synthetic/ersatz data | Confirmed |
| No strategy changes | Confirmed |
| Board `trade-capable` ≠ Live-Go | Confirmed |

## Decision for #3091

This slice completes the #3091 acceptance criteria insofar as:

1. A future comparison-grade window has been selected (Island #3, 58.3h, strict grade).
2. MEXC same-venue 1m candles have been exported and committed as a file-backed dataset.
3. `dataset_spec.json` shows `venue=mexc`, `venue_match=true`, `source=file`.
4. Provenance manifest is committed.
5. Evidence doc is committed.
6. No synthetic/ersatz data was used.

The remaining criterion "Pipeline validated: MEXC WS → candles → db_writer → candles_1m" is indirectly satisfied: the data in `candles_1m` was captured by this pipeline as documented in PR #3133. The export slice exercised the read path, not the write path — but the write path was already proven operational by the data's existence.

## Remaining Limitations

- No fresh cursor-based, gap-safe export tool exists. This is a one-window, one-time export.
- `candle_continuity check-window` was not re-run due to writable DB path requirements. Row count and timestamp range are confirmed via readonly DB probe instead.
- The DB-backed replay load parity check (same window, `--dataset-source db`) requires writable DB credentials; if available after operator setup, it can be run post-hoc.
- #3086 remains open pending broader same-venue acquisition objectives.
