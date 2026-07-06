# ARVP Fresh Natural-Paper Observation — Donchian (#3792)

Status Class: Scoped runtime evidence — **observation RUNNING**
Issue: [#3792](https://github.com/jannekbuengener/Claire_de_Binare/issues/3792)
Hypothesis: `HYP-NP-DONCHIAN-02`
Parent: [#1900](https://github.com/jannekbuengener/Claire_de_Binare/issues/1900)
Tracker: [#3742](https://github.com/jannekbuengener/Claire_de_Binare/issues/3742)
Prior attempt: [#3786](https://github.com/jannekbuengener/Claire_de_Binare/issues/3786) (`HOLD_RUNTIME_ABORT` — no runtime path)
Runtime adapter: [#3790](https://github.com/jannekbuengener/Claire_de_Binare/pull/3790) @ `219ff460`
Live-Readiness: **NO-GO**
Echtgeld: **not authorized**

**Verdict enum:** *pending* (window ends `2026-07-06T19:36:12Z` unless early chain)

**No-evidence-yet assertion:** No `natural_paper_evidence` claim before campaign terminal verdict. Cycle 1 supervisor run showed `events_since_campaign_start=0` (historical ledger chains excluded by campaign-scoped guard).

---

## 1. RUNTIME-GO

GitHub: [#3792 comment](https://github.com/jannekbuengener/Claire_de_Binare/issues/3792#issuecomment-4892302200)

```text
RUNTIME-GO #3792 ARVP fresh natural-paper observation — hypothesis HYP-NP-DONCHIAN-02 — donchian_breakout_v1 runtime adapter delivered via #3790 — MOCK_TRADING=true DRY_RUN=true MEXC_TESTNET=true USE_REAL_BALANCE=false — no Product-Complete no Live-Go LR NO-GO unchanged
```

---

## 2. Campaign manifest

`manifests/campaign_3792_donchian_np_01.yaml`

| Field | Value |
|-------|-------|
| campaign_id | `arvp_3792_natural_paper_donchian_20260706_1136` |
| hypothesis_id | `HYP-NP-DONCHIAN-02` |
| strategy_id | `donchian_breakout_v1` |
| start_utc | `2026-07-06T11:36:12Z` |
| timeout_utc | `2026-07-06T19:36:12Z` |
| campaign_status | `running` |

Signal override: `manifests/runtime_3792_signal_compose_override.yml`

---

## 3. Preflight (PASS)

| Check | Result |
|-------|--------|
| Safety flags (`cdb_execution`) | PASS |
| `cdb_signal` strategy | `donchian_breakout_v1` (logs: Entry/Exit Channel Bars 20/10) |
| Runtime path vs manifest | PASS (#3790 adapter) |
| Kill-switch | inactive (prior session check) |
| Supervisor cycle 1 | `CAMPAIGN_RUNNING`, `events_since_campaign_start=0` |

---

## 4. Runtime reconfiguration

- `cdb_signal` image rebuilt from `main` @ `7181f9d4`
- Recreated with compose override (`SIGNAL_STRATEGY_ID=donchian_breakout_v1`, frozen channel bars 20/10, cooldown 30m)

---

## 5. Monitoring

Supervisor loop: `python -m tools.arvp_campaign_supervisor` (poll 900s)  
Evidence log: `artifacts/campaigns/arvp_3792_natural_paper_donchian_20260706_1136/evidence_log.jsonl`  
Status: `artifacts/campaigns/arvp_3792_natural_paper_donchian_20260706_1136/campaign_status.md`

---

## 6. Boundaries

- LR **NO-GO** unchanged
- No Product-Complete / §5.2.4 claim until post-compare evidence
- No `natural_paper_evidence` claim until terminal verdict with chain

---

*Evidence file opened 2026-07-06 — update on campaign terminal state.*
