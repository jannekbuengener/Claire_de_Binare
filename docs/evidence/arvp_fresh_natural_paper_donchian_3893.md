# ARVP 24h Natural-Paper Observation — Donchian (#3893)

Status Class: Scoped runtime evidence — **observation RUNNING**
Issue: [#3893](https://github.com/jannekbuengener/Claire_de_Binare/issues/3893)
Hypothesis: `HYP-NP-DONCHIAN-03`
Parent: [#1900](https://github.com/jannekbuengener/Claire_de_Binare/issues/1900)
Prior: [#3792](https://github.com/jannekbuengener/Claire_de_Binare/issues/3792) (`TIMEOUT_NO_CHAIN`, 8h)
Tracker: [#3742](https://github.com/jannekbuengener/Claire_de_Binare/issues/3742)
Feasibility (parallel, design-only): [#3894](https://github.com/jannekbuengener/Claire_de_Binare/issues/3894)
Live-Readiness: **NO-GO**
Echtgeld: **not authorized**

**Verdict enum:** *pending* (window ends `2026-07-07T20:32:00Z` unless early chain)

**No-evidence-yet assertion:** No `natural_paper_evidence` claim before campaign terminal verdict.

---

## 1. RUNTIME-GO

Posted on #3893 before observation start.

---

## 2. Campaign manifest

`manifests/campaign_3893_donchian_np_24h_01.yaml`

| Field | Value |
|-------|-------|
| campaign_id | `arvp_3893_natural_paper_donchian_24h_20260706_2032` |
| hypothesis_id | `HYP-NP-DONCHIAN-03` |
| strategy_id | `donchian_breakout_v1` |
| start_utc | `2026-07-06T20:32:00Z` |
| timeout_utc | `2026-07-07T20:32:00Z` (Berlin end ~ `2026-07-07T22:32:00 CEST`) |
| max_duration_hours | `24.0` |

Signal override: `manifests/runtime_3893_signal_compose_override.yml`

---

## 3. Preflight (PASS)

| Check | Result |
|-------|--------|
| Safety flags (`cdb_execution`) | PASS — MOCK_TRADING=true, USE_REAL_BALANCE=false |
| `cdb_signal` strategy | `donchian_breakout_v1` (channel bars 20/10, cooldown 30m) |
| Risk-gate bypass | **not applied** |
| Parameter tuning | **none** (only window 8h→24h) |

---

## 4. Monitoring

Supervisor: `scripts/arvp_campaign_background_runner.ps1 -Start` (poll 900s)  
Evidence log: `artifacts/campaigns/arvp_3893_natural_paper_donchian_24h_20260706_2032/evidence_log.jsonl`

---

## 5. Boundaries

- LR **NO-GO** unchanged
- No multi-strategy parallel runtime in this slice
- No Live-Go / Echtgeld-Go

---

*Evidence file opened 2026-07-06 — update on campaign terminal state.*
