---
name: cdb-risk-governance
description: CDB risk-governance changes for the current Risk Service (`cdb_risk`). Use when Codex needs to implement or harden enforceable limits, kill-switches, drawdown or exposure caps, fail-closed gating, or human-approval semantics. Respect the current repo canon, the `Risk Service` naming, and the fact that Board stage does not clear live trading.
---

# Risk Governance

## Canon first
- Use the working repo and current `Risk Service` / `cdb_risk` terminology.
- Read `CURRENT_STATUS.md` for recent risk and runtime changes.
- Read `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` before making any claim about live readiness.
- Never interpret `trade-capable` as permission to resume or enable live trading.

## Trigger phrases
- risk limits, daily loss, drawdown
- kill switch, circuit breaker, stop trading
- exposure cap, position cap, leverage guard
- no-trade mode, human approval, fail-closed gate

## Non-negotiables
- Critical breaches must produce a machine-checkable stop state.
- Resume paths require explicit human approval where policy demands it.
- Add tests for breach and non-breach paths.
- If thresholds or policy intent are unclear, stop and surface the ambiguity instead of guessing.

## Deliverables
- guard logic and config changes
- tests for breach and non-breach scenarios
- concise evidence table mapping scenario to expected gate state
