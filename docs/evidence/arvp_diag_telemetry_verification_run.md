# ARVP Diagnostic Telemetry Verification — Execute (#3967)

Status Class: **RUNTIME_COMPLETE**
Issue: [#3967](https://github.com/jannekbuengener/Claire_de_Binare/issues/3967)
Preflight: [#3965](https://github.com/jannekbuengener/Claire_de_Binare/issues/3965) / PR [#3966](https://github.com/jannekbuengener/Claire_de_Binare/pull/3966)
Hypothesis: `HYP-ARVP-DIAG-TELEMETRY-01`
Live-Readiness: **NO-GO**
Echtgeld: **not authorized**

**Verdict:** `FAIL_FALSE_ZERO_EVENT_REPRODUCED` (Donchian lane)

---

## 1. RUNTIME-GO

Posted on #3967 @ `2026-07-10T11:30:00Z` (operator execute GO; refs #3965 phrase).

---

## 2. Campaign lanes

| Lane | campaign_id | strategy_id | bot_id | Window (UTC) |
|------|-------------|-------------|--------|--------------|
| PB1 | `arvp_diag_p15_pb1_20260710t1100z` | `primary_breakout_v1` | `np-pb1-diag-01` | `2026-07-10T11:30:00Z` → `2026-07-10T13:30:00Z` |
| Donchian | `arvp_diag_p15_donchian_20260710t1100z` | `donchian_breakout_v1` | `np-donchian-diag-01` | same |

Host env (verified in container): `CDB_CAMPAIGN_ID_PB1` / `CDB_CAMPAIGN_ID_DONCHIAN` from manifests.

---

## 3. Stack (PASS)

| Check | Result |
|-------|--------|
| `cdb_signal_pb1` :8015 | healthy — `CDB_CAMPAIGN_ID=arvp_diag_p15_pb1_20260710t1100z` |
| `cdb_signal_donchian` :8016 | healthy — `CDB_CAMPAIGN_ID=arvp_diag_p15_donchian_20260710t1100z` |
| Canonical `cdb_signal` | stopped during window |
| Safety flags | MOCK_TRADING / DRY_RUN / MEXC_TESTNET / USE_REAL_BALANCE=false |

---

## 4. Supervisor terminal (`2026-07-10T13:32:07Z`)

| Lane | Terminal state | Supervisor global | Supervisor lane | chain_detected |
|------|----------------|------------------:|----------------:|----------------|
| PB1 | `TIMEOUT_NO_CHAIN` | 0 | 0 | false |
| Donchian | `TIMEOUT_NO_CHAIN` | 0 | 0 | false |

Supervisor cycles: PB1 8+ (poll 900s); Donchian 8+.

Evidence logs:
- `artifacts/campaigns/arvp_diag_p15_pb1_20260710t1100z/`
- `artifacts/campaigns/arvp_diag_p15_donchian_20260710t1100z/`

---

## 5. Runtime activity (container logs)

| Lane | Signals emitted (log evidence) | correlation_ledger SIGNAL debug lines |
|------|----------------------------------|---------------------------------------|
| PB1 | **0** | none |
| Donchian | **10** unique `signal_id`s | 10 `📊 correlation_ledger SIGNAL` lines |

Donchian signal_ids (all pre-existed in ledger from `2026-02-15`):

`sig-c049d0be…`, `sig-bac30548…`, `sig-317aab23…`, `sig-3ab57a2d…`, `sig-8c21b3bd…`, `sig-fca18082…`, `sig-d52e2e5f…`, `sig-48bf8006…`, `sig-b8ed349a…`, `sig-da707ac2…`

---

## 6. Ledger readonly evidence

```sql
SELECT COUNT(*) FROM correlation_ledger WHERE created_at >= '2026-07-10T11:30:00Z';
-- → 0
```

All 10 Donchian runtime `signal_id`s already present in `correlation_ledger` (first_seen `2026-02-15`). New inserts use `ON CONFLICT (event_pk) DO NOTHING` → silent no-op; supervisor counts remain 0 despite emitted signals.

**`campaign_id_propagated_to_ledger`:** **not proven** — zero new ledger rows in campaign window; cannot inspect payload for diagnostic `campaign_id`.

---

## 7. lane_campaign_evidence / blocks_by_reason

| Field | PB1 | Donchian |
|-------|-----|----------|
| `lane_campaign_evidence` | null | null |
| `blocks_by_reason` | n/a | n/a |

Probe note: `aggregate_lane_campaign_evidence` failed on host path (`DB unreachable via psycopg2 … and docker exec` during supervisor cycles). No Risk decisions logged for diagnostic `bot_id`s (no ORDER/FILL).

---

## 8. Terminal Q&A

| Question | Answer |
|----------|--------|
| PB1 produced signals? | **No** (regime-gated idle) |
| Donchian produced signals? | **Yes** — 10 (container logs) |
| `lane_campaign_evidence` both lanes? | **No** — null |
| `campaign_id` in ledger payload? | **Unproven** — no new rows |
| Supervisor global + lane counts? | **Yes** — reported 0/0 (lane-scoped fields present) |
| `blocks_by_reason` if Risk blocks? | **N/A** — no Risk activity for diag bots |
| False zero-event? | **Yes (Donchian)** — signals emitted, supervisor/ledger count 0 |
| ORDER/FILL? | **No** for diagnostic lanes |
| LR unchanged NO-GO? | **Yes** |

---

## 9. Root cause (evidence-based)

**False zero-event on Donchian:** deterministic `signal_id` reuse collides with historical `correlation_ledger.event_pk` rows (`2026-02-15`). Inserts no-op; supervisor `events_since_campaign_start_*` stay 0 while `cdb_signal_donchian` logs show SIGNAL emissions.

**PB1:** true zero-signal window (no false-zero ambiguity).

**campaign_id / lane_campaign_evidence telemetry:** not end-to-end proven in this run due to absent campaign-window ledger inserts and probe aggregate failures.

---

## 10. Baseline restore

Post-terminal @ `2026-07-10T13:34:50Z`:

- `cdb_signal_pb1` / `cdb_signal_donchian` stopped
- `cdb_signal` restarted — `SIGNAL_STRATEGY_ID=primary_breakout_v1`, health :8005 ok

---

## 11. Boundaries

- LR **NO-GO** unchanged
- No Live/Echtgeld; no promotion claim
- No strategy/risk parameter changes during run

---

*Execute evidence recorded 2026-07-10. Terminal eval @ `2026-07-10T13:32:07Z`.*
