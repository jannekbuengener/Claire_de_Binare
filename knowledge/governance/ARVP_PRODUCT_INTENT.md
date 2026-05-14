---
relations:
  role: doc
  domain: governance
  upstream:
    - knowledge/governance/CDB_GOVERNANCE.md
  downstream:
    - docs/governance/arvp_platform.md
    - https://github.com/jannekbuengener/Claire_de_Binare/issues/1900
---

# ARVP Product Intent — North-Star Anchor

**Purpose:** This document records the product-level intent behind ARVP and guardrails against drift into locally clever but strategically irrelevant side paths.

**This is not a feature roadmap or technical specification.** For architecture, layers, and module boundaries, see `docs/governance/arvp_platform.md`.

**Last updated:** 2026-04-24

---

## Why This Document Exists

The ARVP replay foundation was correctly built. But without an explicit product-intent anchor, the platform risks drifting into:

- More governance theater than actual leverage
- More reporting/dashboards than decision insight
- More locally clever architecture than product value
- More "cool layers" than actual paper-phase acceleration

This document is the guardrail against that drift.

---

## The Core Product Intent

**ARVP is not:**
- A fancy backtest UI
- A generic research sandbox without operational target
- A dashboard-first analytics product
- A replacement for short, real paper validation
- A container for every technically possible robustness idea
- An engine for converting replay evidence into live/capital approval

**ARVP is:**
- An **accelerated replay paper-mode** — a paper-phase multiplier
- A realistic replay surface combining:
  - Historical market data replayed through the real strategy/execution path in accelerated event-time
  - Realistic execution stress (slippage, partial fills, rejects, liquidity degradation, jitter, feed gaps)
  - Calibration against real paper behavior to identify simulator drift
  - Regime-aware interpretation without pretending to predict regime shifts live

---

## Product-Level Success Criteria

Future ARVP work is on-track only if it moves at least one of these forward:

### A. Accelerated Replay Paper-Mode Usefulness
Can we replay historical market behavior through the real strategy/execution path in a way that is operationally useful, reproducible, and faster than waiting in wall-clock paper time?

### B. Execution Realism
Can we model enough adverse execution behavior that the replay result stops being cosmetically optimistic?

### C. Replay-vs-Paper Calibration
Can we identify where the simulator is too optimistic, too pessimistic, or simply wrong by comparing replay outputs to real paper behavior?

### D. Regime Understanding
Can we explain in which market regimes the strategy behaves well, degrades, or breaks—without inferring regime shifts from replay data?

### E. Robustness Honesty
Can we test controlled perturbations without pretending they are proof of live readiness?

---

## Explicit Anti-Drift Rules

When evaluating future ARVP work, ask these first:

1. Does this make ARVP more useful as an accelerated replay paper-mode?
2. Does this improve realism of execution or market stress?
3. Does this improve replay-vs-paper calibration?
4. Does this improve regime-level interpretability (without over-inferring)?
5. Does this improve robustness evidence without faking certainty?

**If the answer to all five is "no" or "not really", the slice is probably drift.**

Examples of likely drift unless strongly justified:
- Heavy UI/dashboard work before calibration value exists
- More governance/docs work that does not unlock actual replay usefulness
- Generic analytics expansion without strategy/paper calibration value
- Scenario proliferation without clearer decision value
- Architecture polishing that does not shorten or improve evidence generation
- Stress-layer expansion without calibration-driven prioritization

---

## Current State (2026-04-24)

### Child Slices and Status

| Slice | Issue | Status | Evidence |
|-------|-------|--------|----------|
| Paper-Reference Contract | #1901 | ✓ DONE | `docs/governance/arvp_paper_reference_contract.md` |
| Replay-vs-Paper Comparison | #1902 (PR #1914) | ✓ DONE | `core/replay/replay_vs_paper_compare.py` |
| Simulator Calibration Report | #1903 (PR #1916) | ✓ DONE | `core/replay/simulator_calibration_report.py` |
| Regime Scorecards | #1904 (PR #1918) | ✓ DONE | `core/replay/arvp_regime_scorecards.py` |
| **Execution-Realism Gaps** | **#1905** | **⏸ PARKED** | **Evidence-blocked; narrow pilot exists, but no comparison-grade calibration set yet** |

### What's Landed

✓ Infrastructure to compare replay vs. real paper behavior
✓ Infrastructure to classify simulator drift (optimistic/pessimistic/ambiguous)
✓ Infrastructure to analyze regime-specific outcomes
✓ Unit tests for all layers
✓ Operator-facing CLI for paper reference export and comparison

### What's Missing

✗ Comparison-grade calibration evidence remains missing (only a narrow pilot exists; no 1h/2h/4h window, no committed JSON artifacts)
✗ Execution-realism gap prioritization (candidate categories, no data-driven ranking)
✗ Execution-realism improvements tied to calibration findings (deferred pending evidence)

### Critical: #1905 Status

**#1905 is parked, not delivered.**

#1905 was designed as a downstream consumer of calibration findings. A narrow pilot evidence anchor now exists via `docs/evidence/arvp_calibration_pilot_1932_2026-04-26.md`, but it is not comparison-grade evidence. Without broader replay↔paper delta measurements, there are still no material-ranked "highest-value execution-realism gaps"—only a narrow pessimistic missed-order / missed-fill case.

**#1905 cannot proceed responsibly until:**
1. Broader comparison-grade calibration evidence produces reproducible gap measurements
2. Gaps are ranked by operationally material impact
3. A narrow, testable improvement is scoped (not a generic "add all realism features" bucket)

Narrow pilot scope so far:
- BTCUSDT / `primary_breakout_v1`
- 2026-04-24T00:42:00Z to 2026-04-24T00:43:00Z
- Paper: 1 ORDER / 1 FILL
- Replay: 0 ORDER / 0 FILL
- Classification: pessimistic missed-order / missed-fill narrow case
- No LR-/Live-/Echtgeld implication

This is not a failure. This is a prerequisite clarification.

---

## Guardrails: What ARVP Is Not

- **Not a live-readiness gate.** ARVP outputs are validation evidence. They do not authorize live capital without an explicit separate human gate.
- **Not a paper success proof.** Replay acceleration does not replace genuine paper validation; it compresses evidence generation while staying honest about what replay cannot prove.
- **Not a strategy validator.** ARVP surfaces execution and market stress. It does not claim to validate strategy correctness or live profitability.
- **Not a Echtgeld enabler.** No ARVP work changes the live-readiness verdict. The LR NO-GO remains independent.
- **Not a governance substitute.** ARVP feeds into validation evidence workflows. It does not replace control-board decisions or human gates.

---

## Relationship to Governance Structures

| Structure | Relationship to ARVP |
|-----------|---------------------|
| **LR (Live-Readiness) Phases** | ARVP evidence can feed LR-030 / LR-031 only through explicit, issue-anchored evidence commits—never implicitly. |
| **Board Stage System** | `stage:strategy-validated` (ARVP north-star anchor) is orthogonal to LR Go/No-Go. Stage status ≠ LR verdict. |
| **Risk Service / Kill-Switch** | ARVP does not change risk governance. Risk Service remains independent. |
| **Control Register (#1445)** | ARVP status mirrors to #1445 only as optional context (e.g., "latest replay smoke PASS"). Never as a decision gate. |

---

## Use of This Document

**For future ARVP slices:**
- Link to this document when the product-intent alignment matters
- Challenge slices that are technically elegant but do not move the north star
- Prefer slices that increase replay realism, calibration quality, or regime-level decision value

**For governance reconciliation:**
- If an ARVP proposal seems to drift, reference this document
- Use the [Anti-Drift Rules](#anti-drift-rules) as a checklist
- Keep the focus on the [Product-Level Success Criteria](#product-level-success-criteria)

---

## Open Questions Intentionally Not Answered Here

This document is deliberately narrow. It does not prescribe:

- Exact execution-realism gap prioritization (defer to calibration evidence)
- Specific regime thresholds or classification rules (defer to domain data)
- Implementation details or timelines for any slice (defer to owner + team)
- Full feature roadmap (that belongs in GitHub issues and PRs)

---

## Explicit Non-Goals

The following are out of scope for ARVP productization:

- Rebuilding or replacing the deterministic foundation (already solid in #1801–#1806)
- Refactoring live trading or paper trading runtime services
- ML-first strategy research
- Multi-strategy generalization beyond `primary_breakout_v1`
- Sub-minute replay canvas (current strict 1m canvas is intentional)
- Any hidden ms→bar or seconds→bars shims (bar-level surfaces must be explicit)
- Any implicit end-of-window auto-close semantics
- Replacing genuine paper runs with replay
- LR phase decisions, Echtgeld authorization, or live-capital enablement

---

## Done Condition

This north-star anchor should remain open and active as long as:
- ARVP is actively being developed
- Future ARVP slices need alignment guidance

The intent will be sufficiently embodied in the product once the repo has:
- A clearly usable ARVP path for accelerated replay through the real strategy/execution path
- Realistic execution stress
- Replay-vs-paper comparison with evidence-driven gap identification
- Regime-aware interpretation without over-inferring

At that point, the north-star anchor may become reference-only (not decision-level).

---

## References

**GitHub Anchors:**
- **North-Star Issue:** [#1900](https://github.com/jannekbuengener/Claire_de_Binare/issues/1900) — living product-intent record
- **Child Slices:** #1901–#1905
- **Infrastructure Merge:** PRs #1914, #1916, #1918, #1920
- **Operational Cockpit:** [#1445](https://github.com/jannekbuengener/Claire_de_Binare/issues/1445)

**Technical References:**
- `docs/governance/arvp_platform.md` — layers, module boundaries, productization sequence
- `core/replay/` — deterministic replay core
- `services/validation/` — operator-facing CLI runners

---

## Revision History

| Date | Change | Owner |
|------|--------|-------|
| 2026-04-24 | Initial anchor; product intent + anti-drift rules recorded | Codex |
