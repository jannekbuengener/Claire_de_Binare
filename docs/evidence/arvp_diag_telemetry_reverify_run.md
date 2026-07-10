# ARVP Diagnostic Telemetry Re-Verify — Execute (#3977)

Status Class: **RUNTIME_COMPLETE**
Issue: [#3977](https://github.com/jannekbuengener/Claire_de_Binare/issues/3977)
Preflight: [#3973](https://github.com/jannekbuengener/Claire_de_Binare/issues/3973) / PR [#3974](https://github.com/jannekbuengener/Claire_de_Binare/pull/3974)
Regression fix: [#3970](https://github.com/jannekbuengener/Claire_de_Binare/issues/3970) / PR [#3971](https://github.com/jannekbuengener/Claire_de_Binare/pull/3971)
Prior failed execute: [#3967](https://github.com/jannekbuengener/Claire_de_Binare/issues/3967) (`FAIL_FALSE_ZERO_EVENT_REPRODUCED`)
Hypothesis: `HYP-ARVP-DIAG-TELEMETRY-REVERIFY-01`
Live-Readiness: **NO-GO**
Echtgeld: **not authorized**

**Verdict:** `PASS_TELEMETRY_REVERIFIED`

---

## 1. RUNTIME-GO

Operator execute prompt @ `2026-07-10T16:20:00Z` (plan_go, exact phrase match on #3973 template).
GitHub comment on #3977 documents GO + window.

---

## 2. Runtime window

| Field | Value |
|-------|-------|
| Planned start | `2026-07-10T16:20:00Z` |
| Planned timeout | `2026-07-10T18:20:00Z` |
| Baseline restore | `2026-07-10T16:41:22Z` |
| Observation note | Donchian terminal @ `16:22:33Z` (`CHAIN_FOUND`); PB1 true-zero through cycle 2 @ `16:38:10Z`; window truncated after primary re-verify proof (see §11) |

---

## 3. Source SHA proof (PASS)

Images rebuilt `--no-cache` before `up`. Container inspect:

| Container | `CDB_SOURCE_SHA` | `CDB_CAMPAIGN_ID` | `SIGNAL_BOT_ID` |
|-----------|------------------|-------------------|-----------------|
| `cdb_signal_pb1` | `251faf59d94f50bd77972c06b3a7cf23d6ecf401` | `arvp_diag_p0r_pb1_20260710t1600z` | `np-pb1-reverify-01` |
| `cdb_signal_donchian` | `251faf59d94f50bd77972c06b3a7cf23d6ecf401` | `arvp_diag_p0r_donchian_20260710t1600z` | `np-donchian-reverify-01` |

---

## 4. Stack / safety (PASS)

| Check | Result |
|-------|--------|
| Canonical `cdb_signal` | stopped during window; restored post-terminal |
| Parallel lanes | `cdb_signal_pb1` :8015, `cdb_signal_donchian` :8016 healthy during window |
| Safety | MOCK_TRADING / DRY_RUN / MEXC_TESTNET / USE_REAL_BALANCE=false (probe `safety: ok`) |

---

## 5. Supervisor terminal

| Lane | Terminal state | Global / lane counts | `chain_detected` | Terminal @ |
|------|----------------|---------------------:|-----------------:|------------|
| PB1 | `CAMPAIGN_RUNNING` (true zero) | 0 / 0 | false | cycle 2 @ `16:38:10Z` |
| Donchian | `CHAIN_FOUND` | 4 global / **2 lane** | true | cycle 1 @ `16:22:33Z` |

Evidence logs (local):
- `artifacts/campaigns/arvp_diag_p0r_pb1_20260710t1600z/evidence_log.jsonl`
- `artifacts/campaigns/arvp_diag_p0r_donchian_20260710t1600z/evidence_log.jsonl`

---

## 6. Signal activity vs #3967 regression

| Lane | Signals (logs/metrics) | Runtime `signal_id` style | Pre-run ledger collision? |
|------|------------------------|---------------------------|---------------------------|
| PB1 | 0 (`signals_generated_total=0`) | n/a | n/a |
| Donchian | 2 (`signals_generated_total=2`) | `sig-dc37aa77…`, `sig-6200af3a…` (runtime hex) | **0** rows before window |

**Contrast #3967:** Donchian had 10 signals but supervisor/ledger **0/0** (historical ID collision). This run: **2 signals → 2 lane ledger rows**, `false_zero_event_risk=false`.

---

## 7. Ledger readonly evidence

```sql
-- Donchian lane rows since window start
SELECT COUNT(*) FROM correlation_ledger
 WHERE created_at >= '2026-07-10T16:20:00Z'
   AND payload->>'bot_id' = 'np-donchian-reverify-01';
-- → 2

-- PB1 lane
SELECT COUNT(*) FROM correlation_ledger
 WHERE created_at >= '2026-07-10T16:20:00Z'
   AND payload->>'bot_id' = 'np-pb1-reverify-01';
-- → 0
```

**`campaign_id` propagation (Donchian):** `payload->>'campaign_id' = arvp_diag_p0r_donchian_20260710t1600z` on SIGNAL rows (top-level payload field). Supervisor `campaign_id_propagated_to_ledger=true`, `campaign_id_since_start=2`.

---

## 8. Ledger conflict evidence

| Service | `correlation_ledger_insert_conflicts_total` |
|---------|---------------------------------------------|
| `cdb_signal_pb1` (:8015) | 0 |
| `cdb_signal_donchian` (:8016) | 0 |

Supervisor `ledger_telemetry_risk.insert_conflicts_total=0`, `interpretation=no_false_zero_risk_detected`.

---

## 9. lane_campaign_evidence / blocks_by_reason

| Field | PB1 | Donchian |
|-------|-----|----------|
| `lane_campaign_evidence` | null (no lane activity) | present — `signals_emitted=2`, `blocks_by_reason={}` |
| `blocks_by_reason` | n/a | `{}` (no Risk blocks) |
| ORDER/FILL (diag bots) | none | none |

---

## 10. Terminal Q&A

| Question | Answer |
|----------|--------|
| Both containers prove expected `CDB_SOURCE_SHA`? | **Yes** |
| Donchian emitted signals? | **Yes** — 2 |
| Runtime-safe `signal_id`s (not historical)? | **Yes** |
| Ledger conflicts zero or reported? | **Zero**, metrics exposed |
| False 0/0 when signals emitted? | **No** — 2 signals / 2 lane ledger rows |
| `lane_campaign_evidence`? | **Donchian yes**; PB1 null (true idle) |
| `campaign_id` in ledger? | **Yes** (Donchian, top-level payload) |
| LR unchanged NO-GO? | **Yes** |

---

## 11. Baseline restore

Post-terminal @ `2026-07-10T16:41:22Z`:

- `cdb_signal_pb1` / `cdb_signal_donchian` stopped
- `cdb_signal` restarted — `SIGNAL_STRATEGY_ID=primary_breakout_v1`, health :8005 ok

---

## 12. Boundaries / limitations

- LR **NO-GO** unchanged; no Live/Echtgeld; no promotion claim
- **Window truncation:** Planned 2h timeout `18:20Z`; observation ended ~21 min after start once Donchian re-verify proof and PB1 idle consistency were established (supervisor PB1 stopped after cycle 2). Remaining idle polling would not change verdict.
- PB1 `lane_campaign_evidence` / `campaign_id` propagation unproven due to zero PB1 signals (expected regime idle, not false-zero)

---

*Execute evidence recorded 2026-07-10. Terminal eval @ `2026-07-10T16:41:22Z`.*
