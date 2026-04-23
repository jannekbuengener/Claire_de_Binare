# ARVP — Accelerated Replay Validation Platform

**Status:** Governance anchor (core merged; operator front door + MUST layers implemented on the 1m replay canvas)
**Canonical term:** `ARVP` — Accelerated Replay Validation Platform
**Foundation PR:** `#1808` (merged 2026-04-20)
**Foundation issues:** `#1801`, `#1802`, `#1803`, `#1804`, `#1805`, `#1806`
**Productization epic:** `#1839`
**Repo snapshot date:** 2026-04-23

---

## 1. Why this document exists

The ARVP replay foundation landed in full via PR `#1808`, and the repo now
contains a merged, operator-facing ARVP entry point plus the core MUST layers
(historical dataset access, scheduler, run registry, scenario harness, scenario packs)
on the strict 1m replay canvas.

Historically, the product-level vocabulary was fragmented. This document
establishes the canonical name and module map and records the current merged
capabilities vs. explicit non-goals.

This document establishes the single canonical name and module map so that:
- all future issues, PRs, and docs can reference one unambiguous term
- foundation work and productization work are clearly separated
- scope boundaries between layers are explicit before code is written

**Rule:** Use `ARVP` as the umbrella term for the platform. Use
layer-specific module names (see §4) for narrower references.

---

## 2. Canonical product term

| Term | Meaning |
|---|---|
| **ARVP** | Accelerated Replay Validation Platform — the full productized capability |
| **ARVP foundation** | The deterministic replay core landed via PR `#1808` |
| **ARVP productization** | Ongoing layering beyond the merged core (see §4/§5); do not treat merged MUST layers as "not yet implemented" |

**Do not use** as primary names: "shadow replay", "offline replay",
"LR-021 replay", "deterministic replay platform". These terms may appear in
internal module docstrings for historical context, but they are **not**
the platform-level vocabulary.

---

## 3. Foundation: what is already built

All six foundation issues were closed and landed via PR `#1808` on 2026-04-20.

| Module | File | Issue | Role |
|---|---|---|---|
| Replay Clock Context | `core/replay/clock_context.py` | `#1801` | Deterministic event-time clock abstraction; no wall-clock calls |
| Replay Execution Wrapper | `core/replay/execution.py` | `#1802` | Converts replay signals to simulated FillEnvelopeV1 outputs |
| Deterministic Replay Event Loop | `core/replay/deterministic_loop.py` | `#1803` | Two-pass event loop with canonical signature comparison |
| Replay CLI Entrypoint | `services/validation/strategy_replay_runner.py` | `#1804` | Operator-facing CLI: load input → replay → write artifact bundle |
| Replay Reporter | `services/validation/replay_reporter.py` | `#1805` | Consumes ReplayReportInput, writes `report.json`/`manifest.json`/`audit.log` |
| Replay Contracts | `core/replay/replay_contracts.py` | `#1806` | Frozen dataclasses for all replay I/O surfaces |

Supporting utilities (present before PR `#1808`, part of the foundation layer):

| File | Role |
|---|---|
| `core/replay/canonical_json.py` | Sorted-key JSON serialization for deterministic hashing |
| `core/replay/envelopes.py` | Linked envelope chain: Decision → Order → Fill |
| `core/replay/historical_bridge.py` | File-backed historical input adapter for `primary_breakout_v1` |
| `core/replay/determinism.py` | Canonical hash helpers |
| `core/replay/emitter.py` | Replay event emission helpers |
| `core/replay/publisher.py` | Replay artifact publishing helpers |
| `core/replay/time.py` | Time utilities for replay domain |
| `core/replay/policy_snapshot.py` | Policy snapshot binding for replay runs |

**These foundation modules are complete.** Productization issues must not
re-implement or silently replace any of them.

### 3.1 Current merged operator-facing capability (repo-true)

The following capabilities are **implemented and merged** (as of 2026-04-23):

- Operator-facing ARVP replay entry point (`services/validation/strategy_replay_runner.py`)
- Explicit dataset source handling (`file` / `db`) via the canonical dataset layer
- Scenario-group workflow (multi-variant execution over one historical window)
- Thin reporting + scenario artifacts (bundle + scenario comparison summary)
- `delayed_execution` as explicit bar-level surface (no ms→bar shim)
- `feed_gap` as explicit bar-level replay data-gap surface
- Fail-closed data-integrity diagnostics surfaced via the report/metrics pipeline

---

## 4. Module boundaries

ARVP is organized into layers. Each layer has a defined scope and a clear
boundary with adjacent layers.

### 4.1 Foundation layer (DONE)

Deterministic core: clock, execution simulation, event loop, contracts,
reporter, CLI entrypoint. No I/O beyond file read/write. No network. No Redis.

### 4.2 Historical Data Access

**Scope:** Load reproducible historical market data for replay runs.
Supports file-backed and DB-backed providers under one canonical dataset spec.
Produces a deterministic dataset fingerprint.
**Not in scope:** Live/paper/Redis data. Synthetic generation.
**Issue:** `#1841`
**Status:** Implemented (merged; used by operator entry point)

### 4.3 Replay Scheduler

**Scope:** Event-time replay scheduling with explicit speed profiles
(1×, 2×, 5×, 10×, instant). Deterministic tick delivery to the replay loop.
**Not in scope:** Wall-clock scheduling of live services. Async frameworks.
**Issue:** `#1842`
**Status:** Implemented (merged; used by operator entry point)

### 4.4 Replay Run Orchestration / Run Registry

**Scope:** Run identity (`run_id`), run lifecycle, grouped artifact output,
concise operator summaries per run.
**Not in scope:** Scenario orchestration (that is §4.5). Parallel execution.
**Issue:** `#1843`
**Status:** Implemented (merged; used by operator entry point)

### 4.5 Scenario Harness

**Scope:** Multi-variant replay orchestration over the same historical window.
Scenario identity, parameter binding, grouped output per scenario set.
**Not in scope:** Scenario pack definitions (those are §4.6).
**Issue:** `#1844`
**Status:** Implemented (merged; used by operator entry point)

### 4.6 Scenario Packs

**Scope:** First canonical scenario library: `baseline`,
`pessimistic_execution`, `delayed_execution`, `low_liquidity`, `feed_gap`.
Each pack has a stable id, explicit parameters, documented perturbation intent,
and deterministic behavior.
**Not in scope:** Arbitrary user-defined DSLs. Counterfactual free-form perturbation.
**Issue:** `#1845`
**Status:** Implemented (merged; used by operator entry point)

### 4.7 Regime Analytics / Scorecards

**Scope:** Regime-segmented KPI analysis over replay and scenario outputs.
Regime scorecard per run/scenario.
**Not in scope:** Live regime classification (that belongs to `cdb_regime`).
**Issue:** `#1846`

### 4.8 Operator UX / Reporting

**Scope:** Operator-facing run index, management-grade replay summaries,
readable scenario comparison reports.
**Not in scope:** Heavy UI/dashboard. Grafana integration.
**Issue:** `#1847`

### 4.9 Replay-vs-Paper Comparison

**Scope:** Compare deterministic replay output against real paper trading
behavior for simulator calibration. Identify systematic execution divergence.
**Not in scope:** Replacing paper runs with replay. LR-upgrade decisions.
**Issue:** `#1848`

### 4.10 Gates / Evidence Integration

**Scope:** Feed ARVP outputs into validation evidence workflows and
go/no-go style gates. Machine-readable artifact contracts for downstream
gating.
**Not in scope:** LR phase decisions. Echtgeld authorization.
**Issue:** `#1849`

### 4.11 Robustness Layers (later / NICE)

Three optional layers for advanced stability analysis — intended only after
the MUST and SHOULD layers above are materially in place:

| Layer | Scope | Issue |
|---|---|---|
| Counterfactual Engine | Controlled historical perturbation variants | `#1850` |
| Walk-Forward Orchestration | Sliding replay validation windows | `#1851` |
| Bootstrap / Resampling | Deterministic metric stability analysis | `#1852` |

---

## 5. Productization sequence

```
MUST (minimum for a usable platform):
  #1840 → #1841 → #1842 → #1843 → #1844 → #1845

SHOULD (turn usable into decision-helpful):
  #1846 → #1847 → #1848 → #1849

NICE (robustness extensions, only after MUST+SHOULD):
  #1850 → #1851 → #1852
```

The correct cutoff when capacity is limited: finish MUST first, then SHOULD in order,
then NICE.

Repo note (2026-04-23): The MUST chain is present and exercised by the canonical
operator entry point. Remaining work is SHOULD/NICE layering, not "core missing."

---

## 6. Non-goals for the current ARVP phase

The following are explicitly out of scope for ARVP productization:

- Rebuilding or replacing the deterministic foundation already in `#1801–#1806`
- Refactoring live trading or paper trading runtime services
- ML-first strategy research
- Multi-strategy generalization beyond `primary_breakout_v1`
- Sub-minute replay canvas (the current canvas is strict 1m)
- Any hidden ms→bar / seconds→bars shims (bar-level surfaces must be explicit)
- Any implicit end-of-window auto-close semantics
- Replacing genuine paper runs with replay
- Building a heavyweight UI/dashboard before core productization slices exist
- LR phase decisions, Echtgeld authorization, or live-capital enablement
- Any bridge to the live trading path or production order routing

ARVP outputs are **validation evidence**. They are not LR Go/No-Go verdicts
and do not authorize live capital without an explicit human gate.

---

## 7. Naming rules for future issues, PRs, and docs

| Context | Required prefix / term |
|---|---|
| GitHub issues for ARVP work | `[ARVP][<LAYER>]` — e.g. `[ARVP][DATA]`, `[ARVP][SCHEDULER]` |
| PR titles | `feat(arvp):`, `fix(arvp):`, `docs(arvp):` |
| Module/file names | `core/replay/<module>.py` for core replay logic; `services/validation/<module>.py` for CLI/reporting surfaces |
| Governance docs | `docs/governance/arvp_*.md` |
| Layer references | Use the canonical layer name from §4 |

Do not open ARVP slices with generic prefixes like `[LR-021]`, `[REPLAY]`,
or `[VALIDATION]` unless the work is strictly within an already-anchored
LR or validation scope unrelated to the platform productization chain.

---

## 8. Guardrails

- `ARVP` stage status (in the Control Board `stage:strategy-validated`) is
  orthogonal to LR live-readiness (`NO-GO`).
- ARVP work does not change the live-readiness verdict.
- ARVP evidence can feed into LR tasks only through explicit, issue-anchored
  evidence commits — never implicitly.
- Foundation modules in `core/replay/` are stable. Do not modify them
  as a side-effect of productization slices.
