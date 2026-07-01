# CDB No-Trade Taxonomy and Missed-Opportunity Boundaries

**Status:** Canonical (docs/spec)
**Mode:** Docs-only
**Issue Reference:** #3467
**Parent Canon:** [`CDB_PROFITABILITY_ENGINE_CANON.md`](CDB_PROFITABILITY_ENGINE_CANON.md)
**Live-Readiness:** NO-GO
**Runtime Impact:** none

## 1. Purpose

CDB needs a canonical vocabulary for **why no trade happened** and **how to
investigate inactivity offline** without turning inactivity into a live trading
pressure signal.

This document separates four reporting contexts:

1. Live/Paper no-trade explanations (deterministic, runtime-safe)
2. Offline/ARVP missed-opportunity analysis (research evidence only)
3. Control Room / profitability reporting (orientation, not authorization)
4. Future Strategy Gearbox / selector learning inputs (parked; see #205)

Core rule:

- **Live/Paper** may explain why no trade was emitted or executed.
- **Offline/ARVP** may later ask whether a historical window might have been a
  missed opportunity.
- **Runtime must not** label itself as having committed a "Bad No-Trade" as live
  fact.

## 2. Safety boundaries

This taxonomy is specification only. It does **not** authorize trading, runtime
changes, or promotion.

Explicit boundaries:

- No Live-Go. No Echtgeld-Go. LR remains NO-GO.
- No runtime, Risk, Execution, or Allocation code change.
- No DB migration. No MCP mutation.
- No automatic promotion. No dashboard or AI approval.
- ARVP is evidence, not authorization.
- Backtest and paper are not live proof.
- No-Trade analysis must not bypass Risk, KillSwitch, Execution Gate, or
  LR-SSOT.
- Board stage `trade-capable` is orthogonal; it does not imply live capital or
  strategy validation.

## 3. Canonical terms

### 3.1 Live/Paper No-Trade Reason

A **deterministic explanation** for why no trade was emitted or executed in the
current live/paper path.

Properties:

- Emitted at decision time from known gates, data, and candidate state.
- Suitable for audit logs, paper reports, and operator orientation.
- Does not claim counterfactual profit or label the decision "wrong."

Example reason families (non-exhaustive):

| Reason family | Typical source |
|---|---|
| `no_eligible_candidate` | Candidate lifecycle / registry |
| `risk_gate_blocked` | Risk service, exposure, kill-switch |
| `spread_too_high` | Execution economics threshold |
| `slippage_expectation_too_high` | Execution economics threshold |
| `data_quality_insufficient` | Dataset quality gate / stale feed |
| `regime_mismatch` | Regime / allocation context |
| `stale_signal` | Signal freshness contract |
| `incomplete_event_chain` | Envelope / decision chain gap |
| `execution_unsafe` | Execution gate / venue guard |
| `lr_live_boundary` | LR NO-GO / human gate blocks live action |

Live/Paper reasons are **facts about the decision path**, not performance
judgments.

### 3.2 Good No-Trade

A no-trade outcome that is **justified** by current evidence, risk posture, data
quality, execution economics, or candidate eligibility.

Usage rules:

- May appear cautiously in **offline or paper reporting** when the reason chain
  is documented.
- Must not imply live certainty beyond available evidence.
- Must not be used to pressure the runtime into trading.

Good No-Trade is a **classification helper for reviewers**, not a runtime KPI
that demands action.

### 3.3 Missed Opportunity

An **offline analytical finding** that a historical market window may have
contained a viable opportunity not captured by active candidates or current
parameters.

Properties:

- Belongs to ARVP, replay, shadow, and research analysis.
- Requires explicit evidence window, assumptions, and counterfactual method.
- Is **not** live runtime truth.
- Does not authorize trades, promotion, or capital allocation.

Missed Opportunity findings feed the Learning Loop only. They do not short-circuit
the Trading Loop.

### 3.4 Bad No-Trade (forbidden as live runtime state)

**Do not define or emit "Bad No-Trade" as a live or paper runtime state.**

If the term is used at all, it is only as an **informal offline research label**
after replay/evidence review—and even then with explicit counterfactual
assumptions and no authorization implication.

Runtime, risk, and execution services must **never** self-report
`bad_no_trade` as fact.

### 3.5 Idle Capital

**Idle capital** is capital not deployed by active candidates over a reporting
window.

Visibility:

- Allowed in paper, research, and Control Room orientation reports.
- Must **not** become a live pressure KPI or forced-trading incentive.

Idle capital may indicate:

- insufficient candidate coverage
- missing strategy family
- too narrow symbol universe
- overly restrictive parameters
- valid defensive posture (Good No-Trade dominance)

The taxonomy treats idle capital as a **diagnostic signal**, not a mandate to trade.

## 4. Context separation

```text
Live/Paper path          -> Live/Paper No-Trade Reason (deterministic)
Offline ARVP/Replay      -> Missed Opportunity (evidence, counterfactual)
Paper/Control reports    -> Good No-Trade / Idle Capital (orientation)
Runtime                  -> NEVER "Bad No-Trade" as fact
```

| Context | Allowed outputs | Forbidden outputs |
|---|---|---|
| Live/Paper runtime | No-Trade Reason codes | Bad No-Trade, Missed Opportunity as fact |
| ARVP / replay / research | Missed Opportunity (labeled, evidenced) | Live authorization, promotion |
| Control Room | Idle capital, reason aggregates, Good No-Trade (cautious) | Forced-trading KPI, Live-Go |
| Strategy Gearbox (#205, parked) | Future selector inputs (spec only) | Runtime activation without evidence |

## 5. Relationship to existing CDB surfaces

| Surface | Role in this taxonomy |
|---|---|
| [`CDB_PROFITABILITY_ENGINE_CANON.md`](CDB_PROFITABILITY_ENGINE_CANON.md) | Parent canon; Learning vs Trading Loop |
| [`CDB_PROFITABILITY_CANDIDATE_CONTRACT_V1.md`](CDB_PROFITABILITY_CANDIDATE_CONTRACT_V1.md) | Candidate lifecycle states inform eligibility reasons |
| Candidate Evidence Packet | Carries economics and quality context for offline review |
| [`CDB_PROFITABILITY_DATASET_QUALITY_GATE_V1.md`](CDB_PROFITABILITY_DATASET_QUALITY_GATE_V1.md) | `data_quality_insufficient` reason family |
| [`CDB_PROFITABILITY_EXECUTION_ECONOMICS_V1.md`](CDB_PROFITABILITY_EXECUTION_ECONOMICS_V1.md) | Spread/slippage/fee thresholds for no-trade economics |
| ARVP / Replay (`#1900`, harvester `#3345`) | Offline missed-opportunity evidence only |
| [`CDB_PROFITABILITY_LEAGUE_TABLE_V1.md`](CDB_PROFITABILITY_LEAGUE_TABLE_V1.md) | Ranking uses net evidence; does not force trades |
| [`CDB_PROFITABILITY_CAPITAL_SLEEVES_V1.md`](CDB_PROFITABILITY_CAPITAL_SLEEVES_V1.md) | Idle capital visibility; no live pressure |
| [`CDB_PROFITABILITY_CONTROL_ROOM_V1.md`](CDB_PROFITABILITY_CONTROL_ROOM_V1.md) | Aggregated reporting; orientation not authorization |

### Parked / separate issue anchors (reuse, do not duplicate)

| Issue | Rule |
|---|---|
| [#197](https://github.com/jannekbuengener/Claire_de_Binare/issues/197) | ML / intelligence umbrella — **parked**; reference only |
| [#205](https://github.com/jannekbuengener/Claire_de_Binare/issues/205) | Strategy Gearbox / selector — **parked** until evidence coverage exists |
| [#211](https://github.com/jannekbuengener/Claire_de_Binare/issues/211) | Multi-asset / portfolio — **downstream** of #205 |
| [#2985](https://github.com/jannekbuengener/Claire_de_Binare/issues/2985) | Live roadmap — **separate**; no Live-Go from this doc |

Do not create duplicate ML, Gearbox, portfolio, or live umbrella issues from this
slice.

## 6. Learning Loop vs Trading Loop (no-trade lens)

From the Profitability Engine canon:

**Learning Loop** may use Missed Opportunity and offline Good No-Trade review to
improve candidates, parameters, and coverage.

**Trading Loop** emits only Live/Paper No-Trade Reasons and respects Risk,
KillSwitch, Execution Gate, and LR/human gates.

No-Trade taxonomy must **never** convert a research finding into a runtime trade
command.

## 7. Non-goals

- No Strategy Selector or Gearbox implementation (#205 remains parked).
- No ML implementation (#197 remains parked).
- No Risk throttle or allocation runtime logic.
- No paper/live trading behavior change.
- No new required CI check or merge gate from this taxonomy.
- No status changes on #197, #205, #211, or #2985.

## 8. Suggested follow-ups (check anchors first; do not create here)

| Topic | Existing anchor | Possible future child-slice |
|---|---|---|
| Selector preconditions | #205 | Define selector preconditions before activation |
| Return target semantics | create only if no canon issue exists | Separate operator target vs research stage vs sleeve mandate |
| Risk decision taxonomy | create only if no risk-spec issue exists | Risk decision taxonomy before runtime throttle work |
| ML sidecar / lift | #197 | Child under #197 only |
| Portfolio / multi-asset | #211 | Downstream of gearbox evidence |
| Live / LR | #2985 | Separate live roadmap only |

## 9. Acceptance mapping (#3467)

- Canonical No-Trade taxonomy defined in docs/spec form — **this document**
- Live/Paper reasons separated from offline missed-opportunity analysis — **§3–4**
- "Bad No-Trade" forbidden as live runtime truth — **§3.4**
- Idle Capital as research/control signal, not forced-trading KPI — **§3.5**
- ARVP as offline evidence, not authorization — **§2, §3.3**
- Relationship to candidate lifecycle, evidence, economics, league table, #205 —
  **§5**
- Anchors #197, #205, #211, #2985 respected — **§5**
- Safety boundaries preserve LR NO-GO — **§2**
- No runtime/DB/risk/execution/allocation files changed — **docs-only slice**
