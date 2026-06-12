# MEXC Same-Venue Data Quality Policy — #3091

**Decision Date:** 2026-06-12
**Status:** `MEXC_DATA_QUALITY_POLICY_READY`
**Scope:** Data quality classification for MEXC same-venue BTCUSDT 1m candle datasets

---

## Brain Evidence

| Field | Value |
|-------|-------|
| `brain_source` | `repo-only` |
| `brain_status` | `not-used` |
| `tools_or_queries` | `gh issue view` (3086, 3091, 3092, 3087), `gh pr list`, `docker exec cdb_postgres psql` (x15+ queries), `docker logs cdb_db_writer` |
| `records_or_results` | `candles_1m`: 123,533 rows, BTCUSDT only, 2026-01-08..2026-06-12. Island #3: 3,496/3,496 (0 gaps, STRICT). Island #7: 3,052/3,052 (0 gaps, STRICT). #3028: 241/244 (1 gap, TOLERANT). |
| `repo_crosscheck` | `dataset_provider.py` validates 1m cadence strictly. `schema.sql` UNIQUE(symbol, ts_ms). `evidence_class_contract.md` enforces no-silent-upgrade. |
| `impact_on_plan` | Two >48h STRICT windows prove pipeline sustains campaign-grade capture. Dataset readiness separated from natural_paper_evidence. |
| `limitations` | No SurrealDB/Context Brain evidence. Gap root causes are log-suggested, not causally proven. Pre-April-2026 provenance undocumented. |

---

## 1. Purpose

Define two data quality grades for MEXC same-venue BTCUSDT 1m candle datasets
stored in `candles_1m`. These grades deterministically classify whether a
specific time window qualifies as campaign-grade input for ARVP natural-paper
comparison runs — without claiming natural_paper_evidence itself.

Dataset readiness is a **prerequisite** for natural-paper campaigns, not the
gate itself. A STRICT-qualified dataset still requires a successful campaign
(SIGNAL → DECISION → ORDER → FILL) to produce natural_paper_evidence.

---

## 2. Data Quality Grades

### 2.1 STRICT_CAMPAIGN_GRADE

Gate-critical dataset input for natural-paper campaigns (§5.2.4 path).

| Criterion | Value |
|-----------|-------|
| Symbol | BTCUSDT |
| Venue | MEXC (same-venue) |
| Cadence | 1-minute |
| Coverage | **100%** — 0 missing candles |
| Minimum duration | ≥ 480 minutes (8h, one campaign slot) |
| Provenance | `candles_1m` via MEXC WS persistent capture |
| Replay compatibility | Passes `DBBackedDatasetProvider._validate_candle_series()` without error |
| Evidence class (after campaign) | `natural_paper_evidence` (conditional on successful campaign) |
| Evidence class (dataset alone) | `controlled_lab_evidence` |

A STRICT window is a deterministic, complete, venue-matched input. It proves
the data pipeline can deliver campaign-grade material. It does **not** prove
that a paper chain will occur — that depends on market conditions.

### 2.2 TOLERANT_COMPARISON_GRADE

Comparison and research dataset input. Not valid for §5.2.4 gate evidence.

| Criterion | Value |
|-----------|-------|
| Symbol | BTCUSDT |
| Venue | MEXC (same-venue) |
| Cadence | 1-minute |
| Coverage | ≥ 98.5% |
| Maximum single gap | ≤ 3 minutes (≤ 3 consecutive missing candles) |
| Minimum duration | ≥ 480 minutes total span |
| Gap handling | All gaps explicitly documented |
| Replay compatibility | Requires gap-aware handling or window shifting |
| Evidence class | `controlled_lab_evidence` |
| Warning banner | `⚠ NOT natural_paper_evidence — cannot satisfy §5.2.4` |

TOLERANT windows are valuable for comparison analysis (e.g. regime scorecard
re-evaluation with same-venue data, drift re-classification) but cannot satisfy
the Product-Complete gate.

### 2.3 REJECTED

Any window failing both STRICT and TOLERANT criteria. Not usable for ARVP
evidence production. Must not be labeled as campaign input.

---

## 3. Classification Logic

```
IF missing_candles == 0 AND duration_minutes >= 480:
    → STRICT_CAMPAIGN_GRADE
ELIF coverage_pct >= 98.5 AND max_consecutive_gap <= 3 AND total_span_minutes >= 480:
    → TOLERANT_COMPARISON_GRADE
ELSE:
    → REJECTED
```

---

## 4. Current Window Inventory

### 4.1 STRICT Windows (exist today)

| Window | Duration | Span (UTC) | Candles | Gaps |
|--------|----------|------------|---------|------|
| Island #3 | 3,496 min (58.3h) | 2026-06-06 13:43 → 2026-06-08 23:58 | 3,496/3,496 | 0 |
| Island #7 (active) | 3,052+ min (50.9h) | 2026-06-10 11:22 → 2026-06-12 14:12+ | 3,052/3,052 | 0 |

### 4.2 TOLERANT Windows

| Window | Coverage | Span | Candles | Gaps |
|--------|----------|------|---------|------|
| #3028 | 98.8% | 2026-06-05 20:28 → 2026-06-06 00:31 | 241/244 | 1 gap (2 min + 1 trailing) |

### 4.3 Primary Recommendation

**Island #3** (3,496 min, 0 gaps) is the recommended first STRICT_CAMPAIGN_GRADE
dataset. It spans 58.3 continuous hours — enough for 7 full 8h campaign slots.
This window post-dates #3028 and covers a period where the persistent capture
was verified active.

---

## 5. Dataset Spec Contract

Every campaign-grade dataset must carry a `dataset_spec.json` with:

| Field | Type | Description |
|-------|------|-------------|
| `schema_version` | string | `"dataset_spec.v2"` |
| `symbol` | string | `"BTCUSDT"` |
| `venue` | string | `"mexc"` |
| `venue_match` | boolean | `true` for MEXC WS capture |
| `source` | string | `"db"` |
| `source_label` | string | `"mexc_ws_persistent_capture"` |
| `db_table` | string | `"candles_1m"` |
| `start_ts_ms` | integer | Window start (Unix ms) |
| `end_ts_ms` | integer | Window end (Unix ms) |
| `start_utc` | string | ISO-8601 UTC |
| `end_utc` | string | ISO-8601 UTC |
| `duration_minutes` | integer | Total window duration |
| `expected_candles` | integer | (window_ms / 60000) + 1 |
| `actual_candles` | integer | Count from DB |
| `missing_candles` | integer | expected - actual |
| `coverage_pct` | number | actual / expected * 100 |
| `data_quality_grade` | string | `"strict_campaign_grade"` or `"tolerant_comparison_grade"` |
| `gap_report_path` | string | Path to gap_report.json (null if strict) |
| `fingerprint` | string | SHA-256 over all canonical row fields |
| `fingerprint_method` | string | `"sha256(ts_ms:open:high:low:close:volume:trade_count per row)"` |
| `provenance` | object | Capture method, DB table, ingested_at range, backfill_import_id |
| `warning` | string | Governance warning text |
| `natural_paper_evidence` | boolean | Always `false` in dataset spec (requires campaign) |
| `product_complete_claim` | boolean | Always `false` |

---

## 6. Known Gaps (Last 7 Days)

| Gap Duration | Between Islands | Period (UTC) | Likely Cause |
|---|---|---|---|
| 746 min (12.4h) | #3 → #6 | Jun 8 23:58 → Jun 9 10:45 | Stack restart (db_writer log confirms restart @ Jun 9 00:00) |
| 396 min (6.6h) | #2 → #3 | Jun 6 07:07 → Jun 6 13:43 | Likely stack restart or host event |
| 580 min (9.7h) | #6 → #7 | Jun 9 22:56 → Jun 10 11:22 | Likely stack restart or host event |
| 2 min | Within #3028 | Jun 6 00:25–00:26 | Micro-interruption: Redis stream trim or WS reconnect |

Root cause attribution for the 396/580 min gaps is **suggested by log evidence**
for the 746 min gap (confirmed db_writer restart) but **not causally proven**
for all gaps. A full gap-postmortem with Docker logs from candles, ws, redis,
and db_writer services is deferred.

---

## 7. Gap Mitigation

### Structural: Cursor Persistence

The `db_writer._candle_stream_worker` starts with `last_id="0-0"` on every
restart (db_writer.py:914). Entries already trimmed by Redis Stream `maxlen`
(100,000) are unrecoverable. Cursor persistence would allow the worker to
resume from the last persisted position after restart, eliminating the gap
window caused by Redis stream trimming during downtime.

**This is a known limitation** (documented in #3086 and db_writer.py:882)
and is deferred to a separate implementation slice.

### Operational: Stack Uptime

The pipeline produces gap-free data when the stack runs continuously
(proven by Island #3 and Island #7, both >48h with 0 gaps). Maximizing
stack uptime directly improves data quality.

---

## 8. Relationship to natural_paper_evidence

| Layer | What it proves | What it does NOT prove |
|-------|---------------|----------------------|
| **DB contains MEXC same-venue candles** | Capture pipeline works | Data is campaign-grade |
| **Dataset is STRICT_CAMPAIGN_GRADE** | Complete, venue-matched input exists | A paper chain will occur |
| **Campaign produces SIGNAL→DECISION→ORDER→FILL** | Strategy triggers under real market | Product-Complete |
| **Campaign window extracted + replay-verified** | End-to-end pipeline intact | §5.2.4 satisfied (needs non-empty regime_segments) |

Dataset readiness occupies the **second layer**. It is a necessary but
insufficient condition for natural_paper_evidence.

---

## 9. Gordon Checkpoint

```
ASK GORDON BEFORE ANY FUTURE STACK/INFRA EXECUTION:
- Stack start/stop/restart
- Docker rebuild after db_writer cursor-persistence patch
- Redis stream configuration changes
- DB schema migrations
- Any action that could disrupt the active capture pipeline
```

---

## 10. Safety Boundaries

| Boundary | Status |
|----------|--------|
| LR remains **NO-GO** | Confirmed |
| Dataset readiness ≠ natural_paper_evidence | Enforced |
| No Product-Complete claim from dataset qualification | Enforced |
| Board `trade-capable` ≠ Live-Go | Confirmed |
| No silent evidence-class upgrade | Enforced |
| No DB writes or schema changes | Confirmed |
| No stack/Docker changes in this slice | Confirmed |

---

## 11. References

- #3091 — Capture future MEXC 1m candles (target issue)
- #3086 — MEXC same-venue acquisition decision
- #3092 — External provider research (parallel)
- #3087 — CLOSED (Option-E split)
- `docs/evidence/arvp_mexc_same_venue_acquisition_3086.md`
- `docs/evidence/arvp_mexc_backfill_3083.md`
- `docs/contracts/evidence_class_contract.md`
- `docs/evidence/arvp_option_e_waiver_split_decision_3087_3095.md`
- `core/replay/dataset_provider.py`
- `infrastructure/database/schema.sql`
- `services/db_writer/db_writer.py`
- `artifacts/candles/mexc_strict_window_3091/dataset_spec.json`
- `artifacts/candles/mexc_strict_window_3091/gap_report.json`

---

## Status

`MEXC_DATA_QUALITY_POLICY_READY`

- STRICT_CAMPAIGN_GRADE and TOLERANT_COMPARISON_GRADE defined
- Two STRICT windows >48h exist (Islands #3 and #7)
- #3028 classified as TOLERANT_COMPARISON_GRADE (98.8%, 3 missing)
- Dataset Spec contract documented
- Gap root causes partially evidenced (db_writer restart confirmed for 746 min gap)
- Dataset readiness cleanly separated from natural_paper_evidence
- LR remains NO-GO
