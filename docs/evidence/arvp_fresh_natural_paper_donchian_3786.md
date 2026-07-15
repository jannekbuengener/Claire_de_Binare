# ARVP Fresh Natural-Paper Observation — Donchian (#3786)

Status Class: Scoped runtime evidence — **preflight abort; no observation window executed**
Issue: [#3786](https://github.com/jannekbuengener/Claire_de_Binare/issues/3786)
Hypothesis: `HYP-NP-DONCHIAN-01`
Parent: [#1900](https://github.com/jannekbuengener/Claire_de_Binare/issues/1900)
Tracker: [#3742](https://github.com/jannekbuengener/Claire_de_Binare/issues/3742)
Operator lineage: [#1784](https://github.com/jannekbuengener/Claire_de_Binare/issues/1784) (not authorization)
Live-Readiness: **NO-GO**
Echtgeld: **not authorized**

**Verdict enum:** `HOLD_RUNTIME_ABORT`

**No-run assertion (observation window):** No 8h bounded natural-paper observation was started. Stack was not reconfigured to `donchian_breakout_v1`. No campaign monitoring loop entered `running` state.

---

## 1. Brain Evidence Block

```text
brain_source: repo-only
brain_status: not-used
context_brain_attempted: true
context_brain_used: false
context_available: false
repo_fallback_used: true
repo_fallback_reason: insufficient_evidence
context_tool_status: available
context_trust_level: none
records_found: none

tools_or_queries:
  - cdb_context_briefing (task_id=cdb-briefing-3786-donchian-natural-paper)
  - bootloader: AGENTS.md, agents/AGENTS.md (full Read Order)
  - read: docs/evidence/arvp_fresh_paper_runtime_preflight_after_3742.md
  - read: docs/evidence/arvp_natural_paper_window_bank_readonly_feasibility_3742.md
  - read: docs/evidence/arvp_pack_a_wave1_shape_replay_3780.md
  - read: docs/runbooks/arvp_campaign_supervisor_manifest_state_machine.md
  - read: knowledge/operating_rules/runbook_papertrading.md
  - read: scripts/validate_paper_market_data_provenance.py
  - read: docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md
  - read: docs/runbooks/CONTROL_REGISTER.md
  - bash: git fetch/status/rev-parse/worktree; docker ps; docker inspect safety env
  - gh: issue view 3786/3742/1900/1784; issue comment RUNTIME-GO

records_or_results:
  - HEAD == origin/main == c16c4e398ce52051c115ba16f7bfcaf2afce5a80
  - #3786 OPEN; RUNTIME-GO comment posted before preflight
  - context briefing: operator_trust_level=LOW; no enrichment records
  - cdb_readonly SELECT: 34256 correlation_ledger rows (baseline unchanged)
  - kill_switch: inactive

repo_crosscheck:
  - knowledge/governance/SERVICE_CATALOG.md — donchian backtest runner: "keine Promotion, kein Runtime-Pfad"
  - services/signal/service.py — dedicated handler only for primary_breakout_v1
  - services/signal/README.md — "Default-Strategiepfad ist primary_breakout_v1"
  - docs/evidence/arvp_fresh_paper_runtime_preflight_after_3742.md §15 — Donchian adapters not yet implemented
  - docs/evidence/arvp_pack_a_breakout_baseline_spec_3748.md §18.2 — runtime adapter does not exist

impact_on_plan:
  - RUNTIME-GO honored for documentation and preflight only
  - Observation aborted before strategy reconfiguration (stop rule: strategy drift)
  - §5.2.4 remains NOT MET; no natural_paper_evidence claim

limitations:
  - No SurrealDB record evidence
  - No campaign-window provenance PASS (observation not started)
  - No guarded extraction / replay-vs-paper / regime_segments assessment (no chain possible without runtime path)
```

---

## 2. Bootloader / Read-Order Evidence

Executed per `agents/AGENTS.md` Read Order (governance, LR, CONTROL_REGISTER) plus issue-required docs.

Optional files not found in repo (reported, not guessed):

- `CDB.AGENT.LIST.json` — not present
- `CDB.AGENT.RULESET.md` — not present
- `CDB.VERFUEGBARE.SKILLS.md` — not present (canon: `docs/skills/CDB.VERFUEGBARE.SKILLS_LISTE_2026-06-30.md`)

---

## 3. Live-Lage

| Item | Value |
|------|-------|
| Branch | `runtime/3786-donchian-natural-paper` |
| Base SHA | `c16c4e398ce52051c115ba16f7bfcaf2afce5a80` |
| #3786 | OPEN |
| #3742 | OPEN (§5.2.4 tracker) |
| #1900 | OPEN |
| Docker BLUE+RED | Up ~2h; core trading path healthy |
| Current `cdb_signal` strategy | `primary_breakout_v1` / `momentum_builtin` |
| Kill-switch | `inactive` |

---

## 4. RUNTIME-GO-Nachweis

Human-GO phrase from chat matched issue template exactly.

GitHub evidence: [#3786 comment](https://github.com/jannekbuengener/Claire_de_Binare/issues/3786#issuecomment-4891970880) posted **before** preflight completion and **before** any stack reconfiguration.

---

## 5. Campaign-Manifest

Committed: `config/arvp/campaign_3786_donchian_np_01.yaml`

| Field | Value |
|-------|-------|
| campaign_id | `arvp_3786_natural_paper_donchian_20260706_1054` |
| hypothesis_id | `HYP-NP-DONCHIAN-01` |
| strategy_id | `donchian_breakout_v1` |
| symbol | `BTCUSDT` |
| max_duration_hours | `8.0` |
| evidence_class | `natural_paper_evidence` (claim deferred — observation not run) |
| campaign_status | `preflight_failed` |

Manifest scope check vs #3786: **PASS** (fields align). Start criteria **not met** due to preflight blocker.

---

## 6. Safety-Flag-Evidence

Verified on running stack (`cdb_execution` container Python config + `docker inspect`):

| Flag | Required | Observed |
|------|----------|----------|
| MOCK_TRADING | true | **true** |
| DRY_RUN | true | **true** (code default) |
| MEXC_TESTNET | true | **true** (code default) |
| USE_REAL_BALANCE | false | **false** (container env) |
| Kill-switch | inactive | **inactive** |

Safety flags would have been acceptable for observation **if** strategy path were implementable without drift.

---

## 7. Runtime-Verlauf

| Phase | State | Notes |
|-------|-------|-------|
| RUNTIME-GO documented | planned | GitHub comment |
| Manifest created | planned | repo-tracked YAML |
| Preflight strategy-path check | preflight_failed | Blocker found |
| Stack reconfiguration | **not executed** | Abort before drift |
| Monitoring loop | **not entered** | No `running` state |
| 8h window | **not started** | — |

---

## 8. Chain-/Timeout-/Abort-Befund

| Check | Result |
|-------|--------|
| Complete chain SIGNAL→DECISION→ORDER(paper_)→FILL | **N/A** — observation not started |
| Timeout (8h) | **N/A** |
| Abort trigger | **Preflight strategy-path missing** |
| Verdict | `HOLD_RUNTIME_ABORT` |

### Root cause (repo-backed)

1. `donchian_breakout_v1` exists as **offline** Pack-A backtest/replay (`services/validation/donchian_breakout_backtest_runner.py`, `core/replay/pack_a_breakout_common.py`).
2. `services/signal` implements a **dedicated runtime path only for** `primary_breakout_v1` (`services/signal/service.py`).
3. Setting `SIGNAL_STRATEGY_ID=donchian_breakout_v1` without new code would route through generic `momentum_builtin` threshold logic — **not** Donchian channel breakout per #3748 §7.2.
4. Stop rule #3786: *Strategie/Parameter weichen vom Manifest ab → abort*.

---

## 9. Provenance-Ergebnis

Campaign-window provenance: **not executed** (observation not started).

Baseline check on existing `logs/events/` (historical, not campaign-scoped): **FAIL** on legacy file `events_20260527.jsonl` (invalid JSON line) — documented as pre-existing data quality issue, not used as natural-paper evidence.

---

## 10. Extraction / Compare / regime_segments Assessment

| Step | Status |
|------|--------|
| Guarded window extraction | **skipped** — no new chain |
| Replay-vs-paper compare | **skipped** |
| regime_segments assessment | **skipped** |
| §5.2.4 | **NOT MET** (unchanged) |

Readonly baseline (`cdb_readonly`): 34,256 `correlation_ledger` rows; event mix unchanged from #3742 inventory (11 ORDER / 10 FILL total historical).

---

## 11. Geänderte Dateien

- `config/arvp/campaign_3786_donchian_np_01.yaml` (new)
- `artifacts/campaigns/arvp_3786_natural_paper_donchian_20260706_1054/evidence_log.jsonl` (new)
- `docs/evidence/arvp_fresh_natural_paper_donchian_3786.md` (this file)

---

## 12. Validation / Checks

| Check | Result |
|-------|--------|
| git fetch / status / rev-parse | PASS |
| RUNTIME-GO on #3786 before runtime | PASS |
| Manifest vs #3786 scope | PASS |
| Safety flags on live stack | PASS |
| Strategy-path vs manifest | **FAIL** → abort |
| cdb_readonly SELECT | PASS |
| Kill-switch | PASS (inactive) |
| 8h observation | **not run** |

---

## 13. Safety Boundaries

- LR **NO-GO** unchanged
- No Live-Go / no Echtgeld-Go
- No Product-Complete claim
- No `natural_paper_evidence` claim
- No PB1 / #3095 repeat
- No strategy parameter hack
- No replay/synthetic reclassification

---

## 14. Restunsicherheiten

1. Whether `donchian_breakout_v1` would produce a chain in current BTCUSDT conditions remains **untested** until a runtime signal adapter lands.
2. Even with a future chain, `regime_segments` still require guarded extraction + replay-vs-paper compare (#3742 tracker stays open).
3. Minimal runtime adapter scope (frozen #3748 parameters) is a **separate execute slice** — not silently folded into this observation issue.

---

*Evidence created 2026-07-06 for #3786. Preflight abort — honest negative delivery.*
