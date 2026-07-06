# ARVP Fresh-Paper Runtime Preflight — After #3742 Readonly Inventory

Status Class: Decision preflight — docs/evidence only; **no runtime executed**
Issue: [#3742](https://github.com/jannekbuengener/Claire_de_Binare/issues/3742) (readonly inventory complete; data-negative)
Operator thread: [#1784](https://github.com/jannekbuengener/Claire_de_Binare/issues/1784)
Parent: [#1900](https://github.com/jannekbuengener/Claire_de_Binare/issues/1900)
Related: [#3095](https://github.com/jannekbuengener/Claire_de_Binare/issues/3095) (CLOSED), [#3087](https://github.com/jannekbuengener/Claire_de_Binare/issues/3087) (CLOSED), [#3748](https://github.com/jannekbuengener/Claire_de_Binare/issues/3748) (CLOSED), PR [#3769](https://github.com/jannekbuengener/Claire_de_Binare/pull/3769) @ `0e614b2`
Live-Readiness: **NO-GO**
Echtgeld: **not authorized**
Board stage: `trade-capable` (orthogonal to LR; **not** Live-Go)

**Recommended verdict:** `PACK_A_EXECUTE_NEXT_NON_NATURAL_PAPER` (Option C primary; Option B conditional with new hypothesis)

**No-run assertion:** This slice did **not** start Docker, paper runner, replay, ARVP batch, or any live capital path.

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
  - cdb_context_briefing (task_id=cdb-briefing-3742-fresh-paper-preflight)
  - bootloader: AGENTS.md, agents/AGENTS.md (full Read Order)
  - read: docs/evidence/arvp_natural_paper_window_bank_readonly_feasibility_3742.md
  - read: docs/evidence/arvp_option_e_waiver_split_decision_3087_3095.md
  - read: docs/evidence/arvp_pack_a_breakout_baseline_spec_3748.md
  - read: docs/evidence/arvp_p0_strategy_data_regime_economics_map_3747.md
  - read: docs/evidence/arvp_volatility_window_campaign_3095_3.md
  - read: docs/runbooks/arvp_campaign_supervisor_manifest_state_machine.md
  - read: docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md
  - read: docs/runbooks/CONTROL_REGISTER.md
  - read: knowledge/operating_rules/runbook_papertrading.md (checkpoint time-integrity)
  - bash: git fetch/status/rev-parse; git switch docs/3742-1784-fresh-paper-preflight
  - gh: pr view 3769; issue view 3742/1784/1900/3095/3087/3748/2985

records_or_results:
  - HEAD == origin/main base == 0e614b2ece88532b4461129f96c178c5e11f9e8a
  - PR #3769 MERGED @ 0e614b2 (readonly inventory evidence landed)
  - #3742 OPEN; #1900 OPEN; #1784 OPEN; #3095/#3087/#3748 CLOSED
  - #3742 post-repair: 34256 correlation_ledger rows; 12 clusters; 0 new >=2h comparable windows
  - regime_segments: unavailable on all classified candidates
  - #3095: 3/3 gated no-chain campaign slots consumed (PB1 volatility windows)
  - context briefing: no enrichment records; operator_trust_level insufficient for brain claims

repo_crosscheck:
  - docs/evidence/arvp_natural_paper_window_bank_readonly_feasibility_3742.md §13.5–13.7
  - docs/evidence/arvp_option_e_waiver_split_decision_3087_3095.md (Split C; waiver not recommended)
  - docs/evidence/arvp_pack_a_breakout_baseline_spec_3748.md §3, §15–16
  - docs/evidence/arvp_2961_paper_window_runtime_preflight_2026-06-04.md (Runtime-GO checklist pattern)

impact_on_plan:
  - Readonly data path complete → no further #3742 repair slice
  - Blind PB1 campaign repeat (#3095 pattern) is governance-forbidden
  - Pack-A replay/shape is safest non-duplicating next lever
  - Fresh-paper runtime requires new scoped issue + explicit Human-GO (not #1784 alone)

limitations:
  - No SurrealDB record evidence; no live runtime observation in this slice
  - Whether fresh-paper would yield populated regime_segments remains unproven
  - Donchian / breakout_trend_filter adapters not yet implemented (#3748 §16)
```

---

## 2. Bootloader / Read-Order Evidence

Canonical read-order executed per `agents/AGENTS.md`:

1. `knowledge/governance/CDB_CONSTITUTION.md`
2. `knowledge/governance/CDB_GOVERNANCE.md`
3. `knowledge/governance/CDB_AGENT_POLICY.md`
4. `knowledge/governance/SYSTEM_INVARIANTS.md`
5. `knowledge/CDB_KNOWLEDGE_HUB.md`
6. `docs/meta/WORKING_REPO_CANON.md`
7. `CURRENT_STATUS.md`
8. `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
9. `docs/runbooks/CONTROL_REGISTER.md`
10. `agents/OPEN_CODE_AGENTS.md`

Verified boundaries:

- LR SSOT: **NO-GO** (`docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`)
- Board stage `trade-capable` is **not** Live-Go (`docs/runbooks/CONTROL_REGISTER.md`)
- `CURRENT_STATUS.md` is ledger, not live GitHub truth
- No credential values printed, committed, or inspected

---

## 3. Live-Lage (Git / GitHub)

| Item | Status |
|------|--------|
| Branch | `docs/3742-1784-fresh-paper-preflight` |
| Base / HEAD | `0e614b2` == `origin/main` at slice start |
| PR #3769 | **MERGED** @ `0e614b2` |
| #3742 | **OPEN** — readonly inventory complete; data-negative |
| #1900 | **OPEN** — ARVP north-star; §5.2.4 NOT MET |
| #1784 | **OPEN** — 14-day paper operational thread (historical) |
| #3095 | **CLOSED** — 3/3 campaign slots exhausted |
| #3087 | **CLOSED** — Option-E Split (C) recorded |
| #3748 | **CLOSED** — Pack-A spec only; no execution |
| #2985 | **OPEN** — meta navigation |
| LR verdict | **NO-GO** |
| Board stage | `trade-capable` (not Live-Go) |

---

## 4. Management Summary

After #3742 repaired readonly access and completed a live `correlation_ledger` inventory, the honest data verdict is **`HOLD_NO_VALID_WINDOWS_READONLY`**: no new comparison-grade natural-paper window exists in the database, and `regime_segments` remain unavailable on all candidates. ARVP §5.2.4 stays **NOT MET**.

**Recommended route:** Execute **Pack-A wave-1 shape/replay** first (`PACK_A_EXECUTE_NEXT_NON_NATURAL_PAPER`) — deterministic, non-duplicating, explicitly **without** natural-paper or Product-Complete claims. Prepare **fresh natural-paper runtime** only as a **conditional** parallel track (`READY_FOR_FRESH_PAPER_GO`) under a **new narrow execute issue** with a **documented new hypothesis** — not a blind repeat of the exhausted #3095 PB1 volatility campaigns. **#1784** remains useful as operator lineage reference but does **not** authorize runtime by itself.

Do **not** re-open governance Split/Waiver (Option D) unless a formal Roadmap-Amendment vote is sought; Split (C) was already decided in #3087.

---

## 5. What #3742 Changed

| Phase | Verdict | Meaning |
|-------|---------|---------|
| 2026-07-05 (prior) | `HOLD_READONLY_ACCESS_UNAVAILABLE` | DSN present but `cdb_readonly` auth failed — access hold, not data verdict |
| 2026-07-06 (post-repair, PR #3769) | `HOLD_NO_VALID_WINDOWS_READONLY` | Readonly path operational; live SELECT inventory executed |

Post-repair inventory highlights (from `arvp_natural_paper_window_bank_readonly_feasibility_3742.md` §13):

- **34,256** `correlation_ledger` rows inspected
- **12** clusters scanned across `primary_breakout_v1`, `paper`, and `paper_`-qualified chains
- **6** trade-dense clusters; **0** with span >= 2h meeting comparability contract
- **0** new comparable candidates outside the existing 3-window bank
- **`regime_segments`:** unavailable / not_assessable on all candidates
- Longest trade-dense PB1 cluster: **1.81h** (below 2h target)
- Largest `strategy_id=paper` cluster: **23.4h** span but **inadmissible** (no paper_-qualified ORDER+FILL chain)

Follow-up gate named in #3742 evidence: `REQUIRES_RUNTIME_GO_FOR_FRESH_PAPER` — out of #3742 write scope; addressed here.

---

## 6. Why #3095 Must Not Be Blindly Repeated

#3095 executed three **gated no-chain** volatility-window campaigns for `primary_breakout_v1` (0.5% breakout, 15m lookback) under HIGH_VOL_CHAOTIC / mixed conditions:

| Campaign | Result | Slot |
|----------|--------|------|
| #1R | HOLD_NO_CHAIN | Slot 1 consumed |
| #2R | HOLD_NO_CHAIN | Slot 2 consumed |
| #3 | TIMEOUT_NO_CHAIN | Slot 3 consumed |
| #1, #2 | Infrastructure interruptions | **Not** slot consumptions |

**Effective: 3 of max 3 slots consumed.** Zero SIGNAL→DECISION→ORDER(paper_)→FILL chains across all observed windows.

Per #3094 design and `arvp_option_e_waiver_split_decision_3087_3095.md`:

- Escalation to Option-E Split was **mandatory** and **completed** (Decision C)
- Further campaigns **without new hypothesis / new design** are **explicitly forbidden**
- The blocker is **market-conditional** (insufficient breakout trigger), not a technical defect
- Threshold-lowering (e.g. breakout < 0.5%) counts as parameter-hack gate-cheat

Repeating the same PB1 campaign pattern would be **duplicative**, **governance-noncompliant**, and **unlikely** to satisfy §5.2.4 without a materially different hypothesis (strategy, start criteria, or evidence class).

---

## 7. Role of #1784 — Can and Cannot Authorize

### What #1784 is

- Open **operational control thread** for the historical 14-day paper phase (April–May 2026)
- Contains operator checkpoints, market-data provenance hygiene, health evidence
- Useful **lineage reference** for paper-runtime conventions (MOCK_TRADING, provenance validator)

### What #1784 is not

- **Not** an automatic Runtime-GO for ARVP fresh-paper observation
- **Not** a scoped execute issue with campaign manifest, hypothesis ID, or stop rules
- **Not** a substitute for #3742 / #1900 §5.2.4 tracking

### Preflight answer

**#1784 alone is insufficient.** Fresh-paper runtime requires:

1. A **new narrow execute issue** (e.g. `[ARVP][WINDOW][EXECUTE] Fresh natural-paper observation — hypothesis <ID>`)
2. Cross-refs: `Refs #1784`, `Refs #3742`, `Refs #1900`
3. Campaign manifest per `docs/runbooks/arvp_campaign_supervisor_manifest_state_machine.md`
4. Explicit **RUNTIME-GO** phrase from Jannek (see §11)

Comment on #1784 is recommended **only** as lineage pointer when the B-track is prepared — not as authorization.

---

## 8. Pack-A vs Fresh-Paper Tradeoff

| Dimension | Pack-A (Option C) | Fresh-Paper (Option B) |
|-----------|-------------------|------------------------|
| Evidence class | `controlled_lab_evidence` / replay shape | `natural_paper_evidence` (if chain produced) |
| §5.2.4 claim | **No** — offline regime with limitation banner | **Possible** only if window + replay/compare populates `regime_segments` |
| Duplication risk | **Low** — new Donchian/Bo+Trend vs PB1-PARK compare | **High** if repeating #3095 PB1 pattern |
| Prerequisites | #3748 spec; #3035 dataset re-pin; adapter scope for new candidates (#3748 §16) | Runtime-GO; safety flags; campaign manifest; new hypothesis |
| Economics | `ranking_ready=false` (#3747 B1 friction gap) | Same — no honest net economics without B1 |
| LR impact | **None** | **None** |

**Pack-A delivers the next real lever** without pretending §5.2.4 is satisfied. Fresh-paper remains **unproven** for `regime_segments` until Runtime-GO + observation + replay/compare runs.

---

## 9. Runtime-GO Checklist (Fresh-Paper — Not Executed Here)

All items must be **verified and documented** before any Runtime-GO slice starts:

| # | Check | Required value / state |
|---|-------|------------------------|
| 1 | `MOCK_TRADING` | `true` |
| 2 | `DRY_RUN` | `true` |
| 3 | `MEXC_TESTNET` | `true` |
| 4 | `USE_REAL_BALANCE` | `false` |
| 5 | Kill-switch | **inactive** |
| 6 | `ALLOW_EVIDENCE_DEBT` | **not** enabled (`!= "1"`) |
| 7 | `TRACE_CONTRACT_V1_ENABLED` | per compose default (`1`) |
| 8 | LR verdict | **NO-GO** (unchanged) |
| 9 | Board stage | `trade-capable` — **not** interpreted as Live-Go |
| 10 | Market-data provenance | `validate_paper_market_data_provenance.py --strict --allow-source mexc` PASS on active run logs |
| 11 | Readonly DSN | operational post-#3742 (`cdb_readonly` + `POSTGRES_READONLY_PASSWORD_DSN`) |
| 12 | Campaign manifest | Pre-documented per supervisor contract (hypothesis, criteria, timeout, evidence paths) |
| 13 | Hypothesis | **New** — not #3095 PB1 slot-4 repeat |
| 14 | Issue scope | Dedicated execute issue — not #1784 prose alone |
| 15 | Human-GO | Explicit RUNTIME-GO phrase recorded on issue (§11) |

---

## 10. Decision Matrix A / B / C / D

| ID | Option | Verdict enum | Assessment |
|----|--------|--------------|------------|
| **A** | No runtime; finalize #3742 as data-negative | `HOLD_NO_VALID_WINDOWS_READONLY_FINAL` | Readonly inventory **complete**; data slice may be final-commented on #3742. **§5.2.4 remains open** → keep #3742 **OPEN** as regime_segments tracker; do not silently close |
| **B** | Fresh-paper Runtime-GO under #1784 lineage | `READY_FOR_FRESH_PAPER_GO` | Legitimate **only** with new hypothesis + new execute issue + RUNTIME-GO. **Not** a blind #3095 repeat. **Conditional** — prepare, do not execute in this slice |
| **C** | Pack-A shape/replay first | `PACK_A_EXECUTE_NEXT_NON_NATURAL_PAPER` | **Recommended primary** — non-duplicating, deterministic, `ranking_ready=false`, no natural-paper claim |
| **D** | Governance split / waiver review | `REQUIRES_GOVERNANCE_DECISION` | **Not primary** — Split (C) already decided (#3087); waiver not recommended; revisit only via Roadmap-Amendment vote |

### Recommended combination

**C now** + **B prepared in parallel** (not executed) via dedicated follow-up issues.

---

## 11. Exact Human-GO Phrases

### Pack-A replay (offline — no Docker paper)

```text
GO #<execute-issue> Pack-A wave-1 shape/replay execute — offline replay only, ranking_ready=false, no natural_paper_evidence claim, LR NO-GO unchanged
```

### Fresh natural-paper runtime (after new execute issue)

```text
RUNTIME-GO #<execute-issue> ARVP fresh natural-paper observation — hypothesis <ID> — MOCK_TRADING=true DRY_RUN=true MEXC_TESTNET=true USE_REAL_BALANCE=false — no Product-Complete no Live-Go LR NO-GO unchanged
```

Replace `<execute-issue>` with the dedicated issue number and `<ID>` with the documented hypothesis identifier in the campaign manifest.

---

## 12. Stop Rules

| Rule | Rationale |
|------|-----------|
| No Product-Complete claim | §5.2.4 NOT MET |
| No LR status change | LR SSOT unchanged; this preflight does not amend LR |
| No Live-Go / Echtgeld-Go language | LR NO-GO; board stage ≠ live authorization |
| No `MOCK_TRADING=false` | Would cross live-capital boundary |
| No parameter hacks (e.g. lower breakout threshold) | Gate-cheat per #3087 decision |
| No synthetic → natural reclassification | Evidence-class violation (#3094) |
| No #3095 slot-4 under old design | 3/3 slots exhausted; new design required |
| No checkpoint time simulation | Paper-capture uses real market time (`runbook_papertrading.md`) |
| No PB1 promotion / rescue | PB1 remains PARKED (#3183) |
| No controlled-lab evidence as §5.2.4 substitute | Per Split (C) contract |
| Stop on kill-switch activation | Emergency stop per `EMERGENCY_STOP_SOP.md` |
| Stop on provenance FAIL | Paper evidence invalid without MEXC strict provenance |

---

## 13. Recommended Next Issue / Thread

### Primary (create if no duplicate)

**Title:** `[ARVP][PACK-A][EXECUTE] Wave-1 shape/replay run per #3748 spec`

**Scope:**

- Offline replay only for Top-3: `primary_breakout_v1` (PARK reference), `donchian_breakout_v1`, `breakout_trend_filter_v1`
- Same pinned dataset; #3035 quality gate; `ranking_ready=false`
- Adapter implementation scope for Donchian/Bo+Trend if not yet in repo
- Evidence doc under `docs/evidence/`; **no** natural_paper_evidence claim

**Refs:** #3748, #3747, #3742, #1900

Dedupe scan at slice time: **no open Pack-A execute issue found**.

### Conditional (later, separate)

**Title:** `[ARVP][WINDOW][EXECUTE] Fresh natural-paper observation — non-PB1 hypothesis <ID>`

**Refs:** #1784 (lineage), #3742, #1900, #3087

Requires RUNTIME-GO phrase (§11) and campaign manifest. **Not** started by this preflight.

### #3742 disposition

- **Keep OPEN** — §5.2.4 / `regime_segments` tracker
- Comment: readonly inventory slice **final negative**; fresh-paper route decided in this doc

---

## 14. No-Run Assertion and LR Boundary

This preflight slice:

- Did **not** start Docker or any compose stack
- Did **not** start `cdb_paper_runner` or paper trading
- Did **not** execute replay or ARVP batch
- Did **not** mutate strategy parameters or promote PB1
- Did **not** write to productive DB or MCP mutation surfaces
- Did **not** change LR status

**LR remains NO-GO.** Board stage `trade-capable` does not authorize live capital, Grafana live-trading gates, or strategy validation for echtgeld.

---

## 15. Restunsicherheiten

1. Whether any fresh-paper hypothesis (non-PB1) would produce ORDER/FILL chains in current BTCUSDT conditions is **unproven**.
2. Even with a fresh paper chain, `regime_segments` require replay/compare pipeline work — not solved by runtime observation alone (#3742 §14).
3. Donchian / `breakout_trend_filter_v1` adapters may need implementation scope before Pack-A execute (#3748 §16).
4. Example dataset under `artifacts/backtests/primary_breakout_v1/` may not be MEXC same-venue — execute slice must re-pin per #3035 + same-venue policy.
5. B1 same-venue friction series gap (#3747) blocks honest net economics for **all** paths until closed.

---

## 16. Status

**Preflight verdict:** `PACK_A_EXECUTE_NEXT_NON_NATURAL_PAPER`

**#3742 data slice:** `HOLD_NO_VALID_WINDOWS_READONLY` (final for readonly inventory)

**§5.2.4:** NOT MET

**LR:** NO-GO | **Live-Go:** not authorized | **Echtgeld:** not authorized

**Runtime executed in this slice:** **No**
