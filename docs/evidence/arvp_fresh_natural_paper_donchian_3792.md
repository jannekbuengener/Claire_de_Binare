# ARVP Fresh Natural-Paper Observation — Donchian (#3792)

Status Class: Scoped runtime evidence — **observation COMPLETE**
Issue: [#3792](https://github.com/jannekbuengener/Claire_de_Binare/issues/3792)
Hypothesis: `HYP-NP-DONCHIAN-02`
Parent: [#1900](https://github.com/jannekbuengener/Claire_de_Binare/issues/1900)
Tracker: [#3742](https://github.com/jannekbuengener/Claire_de_Binare/issues/3742)
Prior attempt: [#3786](https://github.com/jannekbuengener/Claire_de_Binare/issues/3786) (`HOLD_RUNTIME_ABORT` — no runtime path)
Runtime adapter: [#3790](https://github.com/jannekbuengener/Claire_de_Binare/pull/3790) @ `219ff460`
Live-Readiness: **NO-GO**
Echtgeld: **not authorized**

**Verdict enum:** `TIMEOUT_NO_CHAIN`

**No-evidence-yet assertion:** No `natural_paper_evidence` claim. Campaign completed full 8h window with healthy stack and donchian runtime path verified, but **zero campaign-scoped** SIGNAL→DECISION→ORDER(paper_)→FILL chains.

---

## 1. RUNTIME-GO

GitHub: [#3792 comment](https://github.com/jannekbuengener/Claire_de_Binare/issues/3792#issuecomment-4892302200)

```text
RUNTIME-GO #3792 ARVP fresh natural-paper observation — hypothesis HYP-NP-DONCHIAN-02 — donchian_breakout_v1 runtime adapter delivered via #3790 — MOCK_TRADING=true DRY_RUN=true MEXC_TESTNET=true USE_REAL_BALANCE=false — no Product-Complete no Live-Go LR NO-GO unchanged
```

---

## 2. Campaign manifest

`config/arvp/campaign_3792_donchian_np_01.yaml`

| Field | Value |
|-------|-------|
| campaign_id | `arvp_3792_natural_paper_donchian_20260706_1136` |
| hypothesis_id | `HYP-NP-DONCHIAN-02` |
| strategy_id | `donchian_breakout_v1` |
| start_utc | `2026-07-06T11:36:12Z` |
| timeout_utc | `2026-07-06T19:36:12Z` |
| campaign_status | `timeout_no_chain` |
| verdict_enum | `TIMEOUT_NO_CHAIN` |

Signal override: `config/arvp/runtime_3792_signal_compose_override.yml`

---

## 3. Preflight (PASS)

| Check | Result |
|-------|--------|
| Safety flags (`cdb_execution`) | PASS — MOCK_TRADING=true, USE_REAL_BALANCE=false |
| `cdb_signal` strategy | `donchian_breakout_v1` (Entry/Exit Channel Bars 20/10) |
| Runtime path vs manifest | PASS (#3790 adapter) |
| Kill-switch | inactive at start |
| Container restarts | 0 (`cdb_signal` RestartCount=0) |

---

## 4. Runtime reconfiguration

- `cdb_signal` container started `2026-07-06T11:36:45Z`
- Compose override: `SIGNAL_STRATEGY_ID=donchian_breakout_v1`, channel bars 20/10, cooldown 30m, `long_only`

---

## 5. Monitoring

Supervisor loop: `python -m tools.arvp_campaign_supervisor` (poll 900s)  
Evidence log: `artifacts/campaigns/arvp_3792_natural_paper_donchian_20260706_1136/evidence_log.jsonl`  
Terminal status: `artifacts/campaigns/arvp_3792_natural_paper_donchian_20260706_1136/campaign_status.md` (Cycle 32 @ `2026-07-06T19:41:11Z`)

**Supervisor note:** Cycle 1 briefly reported `CHAIN_FOUND` with historical ledger events (34256); campaign-scoped guard corrected to `events_since_campaign_start=0` from cycle 1 onward.

---

## 6. Run metrics (campaign window)

| Metric | Count | Source |
|--------|------:|--------|
| Signals generated | 34 (17 BUY + 17 SELL) | `cdb_signal` logs |
| Signals persisted | 34 (DB IDs 222244–222277) | `cdb_db_writer` logs |
| Risk approvals | 0 | `cdb_risk` logs |
| Risk blocks (RC_001) | 34 | `cdb_risk` logs |
| Orders | 0 | `cdb_execution` logs |
| Fills | 0 | `cdb_execution` logs |
| Campaign-scoped chain events | 0 | Supervisor + campaign_status |
| Regime during window | `HIGH_VOL_CHAOTIC` (risk_off=True) | `cdb_risk` logs |
| PnL / regime_segments | not belegbar | no chain / no window extraction |

**Primary block reason:** `RC_001` — unfavorable regime (`regime_id` 2/3 per `services/risk/reason_codes.py`).

---

## 7. Verdict and §5.2.4 assessment

| Outcome | Value |
|---------|-------|
| Verdict enum | **`TIMEOUT_NO_CHAIN`** |
| Infrastructure | PASS — full 8h, healthy stack, strategy path correct |
| ARVP chain hypothesis | **Falsified** for 8h window under observed regime |
| `natural_paper_evidence` | **Not claimed** |
| §5.2.4 / `regime_segments` | **Not satisfied** — no extractable chain window |
| Follow-up | New execute issue required for 24h observation (`HYP-NP-DONCHIAN-03`); not a silent retry |

---

## 8. Boundaries

- LR **NO-GO** unchanged
- No Product-Complete claim
- No Live-Go / Echtgeld-Go
- No risk-gate bypass or parameter tuning applied

---

*Evidence finalized 2026-07-06 — terminal state TIMEOUT_NO_CHAIN.*
