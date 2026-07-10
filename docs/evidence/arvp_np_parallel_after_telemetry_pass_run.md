# ARVP Parallel Natural-Paper After Telemetry PASS — Execute (#3982)

Status Class: **RUNTIME_COMPLETE**
Issue: [#3982](https://github.com/jannekbuengener/Claire_de_Binare/issues/3982)
Preflight: [#3980](https://github.com/jannekbuengener/Claire_de_Binare/issues/3980) / PR [#3981](https://github.com/jannekbuengener/Claire_de_Binare/pull/3981) @ `c4ba7428`
Telemetry chain: [#3977](https://github.com/jannekbuengener/Claire_de_Binare/issues/3977) `PASS_TELEMETRY_REVERIFIED`
Hypothesis: `HYP-NP-PARALLEL-2S-01`
Live-Readiness: **NO-GO**
Echtgeld: **not authorized**

**Verdict (combined):** `PASS_TELEMETRY_CLEAN_MIXED_STRATEGY`

| Lane | Verdict |
|------|---------|
| Donchian | `PASS_CHAIN_OBSERVED` |
| PB1 | `TIMEOUT_NO_CHAIN` (true zero / regime idle) |

---

## 1. RUNTIME-GO

Operator phrase matched @ `2026-07-10T17:19:45Z` on #3982.

---

## 2. Runtime window

| Field | Value |
|-------|-------|
| Start | `2026-07-10T17:20:00Z` |
| Timeout | `2026-07-10T21:20:00Z` |
| PB1 supervisor terminal | cycle 17 @ `2026-07-10T21:34:24Z` (`TIMEOUT_NO_CHAIN`, exit `20`) |
| Donchian supervisor terminal | cycle 1 @ `2026-07-10T17:23:07Z` (`CHAIN_FOUND`, exit `10`) |
| Baseline restore | `2026-07-10T21:34:48Z` |

---

## 3. Source SHA proof (PASS)

Images rebuilt `--no-cache` before `up`.

| Container | `CDB_SOURCE_SHA` | `CDB_CAMPAIGN_ID` | `SIGNAL_BOT_ID` |
|-----------|------------------|-------------------|-----------------|
| `cdb_signal_pb1` | `c4ba7428e605cca09b1d3e2c9469a431ac475554` | `arvp_np_pb1_after_telemetry_pass_20260710t1700z` | `np-pb1-telemetry-pass-01` |
| `cdb_signal_donchian` | `c4ba7428e605cca09b1d3e2c9469a431ac475554` | `arvp_np_donchian_after_telemetry_pass_20260710t1700z` | `np-donchian-telemetry-pass-01` |

---

## 4. Stack / safety (PASS)

| Check | Result |
|-------|--------|
| Canonical `cdb_signal` | stopped during window; restored `primary_breakout_v1` @ `:8005` healthy |
| Parallel lanes | `cdb_signal_pb1` :8015, `cdb_signal_donchian` :8016 healthy during window |
| Safety | MOCK_TRADING / DRY_RUN / MEXC_TESTNET / USE_REAL_BALANCE=false |

---

## 5. Supervisor terminal

| Lane | Terminal state | Global / lane counts | `chain_detected` | Terminal @ |
|------|----------------|---------------------:|-----------------:|------------|
| PB1 | `TIMEOUT_NO_CHAIN` | 36 global / **0 lane** | false | cycle 17 @ `21:34:24Z` |
| Donchian | `CHAIN_FOUND` | 4 global / **2 lane** | true | cycle 1 @ `17:23:07Z` |

Evidence logs:
- `artifacts/campaigns/arvp_np_pb1_after_telemetry_pass_20260710t1700z/evidence_log.jsonl`
- `artifacts/campaigns/arvp_np_donchian_after_telemetry_pass_20260710t1700z/evidence_log.jsonl`

---

## 6. Signal activity

| Lane | `signals_generated_total` | Lane ledger rows | False-zero risk |
|------|--------------------------:|-----------------:|-----------------|
| PB1 | 0 | 0/0 | **none** (true zero) |
| Donchian | 2 | 2/2 | **none** |

Contrast #3967: Donchian had 10 signals but supervisor 0/0 (historical ID collision). This run: **2 signals → 2 lane rows**.

---

## 7. Insert conflict evidence (PASS)

| Service | `correlation_ledger_insert_conflicts_total` |
|---------|---------------------------------------------|
| `cdb_signal_pb1` (:8015) | 0 |
| `cdb_signal_donchian` (:8016) | 0 |

Supervisor `ledger_telemetry_risk.insert_conflicts_total=0` both lanes; `interpretation=no_false_zero_risk_detected`.

---

## 8. lane_campaign_evidence / campaign_id

| Field | PB1 | Donchian |
|-------|-----|----------|
| `lane_campaign_evidence` | null (no lane activity) | present — `signals_emitted=2`, `blocks_by_reason={}` |
| `campaign_id` in ledger | n/a (0 signals) | **propagated** (`campaign_id_propagated_to_ledger=true`, 2 rows) |
| Risk blocks | n/a | 0 |
| Orders/Fills (lane bots) | none | none |

---

## 9. Terminal Q&A

| Question | Answer |
|----------|--------|
| PB1 emitted signals? | **No** — regime idle (true zero) |
| Donchian emitted signals? | **Yes** — 2 |
| Lane-ledger rows per lane? | PB1: 0; Donchian: 2 |
| `campaign_id` present per lane? | Donchian yes; PB1 n/a (no signals) |
| `insert_conflicts_total` zero? | **Yes** both lanes |
| Risk approved/blocked? | Donchian: no blocks; PB1: n/a |
| ORDER/FILL rows for lane bots? | **None** |
| False-zero telemetry reappear? | **No** |
| LR unchanged NO-GO? | **Yes** |
| Evidence type? | **Both** — telemetry clean; strategy partial (Donchian chain, PB1 idle) |

---

## 10. Baseline restore

Post-terminal @ `2026-07-10T21:34:48Z`:

- `cdb_signal_pb1` / `cdb_signal_donchian` stopped
- `cdb_signal` restarted — `SIGNAL_STRATEGY_ID=primary_breakout_v1`, health :8005 ok

---

## 11. Boundaries / limitations

- LR **NO-GO** unchanged; no Live/Echtgeld; no promotion claim
- PB1 `lane_campaign_evidence` / `campaign_id` propagation unproven due to zero signals (expected regime idle, not false-zero)
- Donchian ORDER/FILL chain for lane bots not observed (signals only; shared risk pool may block downstream)
- #3742 stays OPEN
