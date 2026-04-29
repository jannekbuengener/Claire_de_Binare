---
name: cdb-trading-core
description: 'Trading-system development for Claire de Binare in the current working repo. Use when Codex needs cross-cutting work over strategy logic, backtesting, market-data flow, Risk Service integration, shadow or paper evidence, or performance reporting. Respect the current canon: the working repo is authoritative, `trade-capable` does not imply LR-GO, and no action may place live orders or use live credentials.'
---

# Claire de Binare Trading

## Canon first
- Use the working repo as canon; do not use the retired external docs repo.
- Separate status classes:
  - `CURRENT_STATUS.md` for repo and engineering state
  - `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` for live-readiness verdict
  - `docs/runbooks/CONTROL_REGISTER.md` for Board stage
- Current reality: Board stage can be `trade-capable` while LR remains `NO-GO`.

## Scope
- strategy logic and evaluation
- market-data and decision-flow plumbing
- shadow or paper execution evidence
- performance reporting
- coordination across backtesting, exchange boundaries, and risk gates

## Routing rule
- If the task is mainly backtesting, prefer `cdb-backtest-engine`.
- If the task is mainly exchange-boundary work, prefer `cdb-exchange-adapters`.
- If the task is mainly gating or limits, prefer `risk-governance`.
- Use this skill when the request spans multiple of those areas.

## Working rules
- Evidence over assumptions. If a strategy, exchange, or runtime mode is unclear, derive it from the repo or ask.
- Prefer paper, replay, or shadow evidence.
- Do not introduce live-order behavior.
- Keep credentials in secret storage only and never print them.

## Safety
- No live orders.
- No live-credential changes.
- If the request implies enabling live trading, stop and point to `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` plus `knowledge/operating_rules/LIVE_TRADING_RUNBOOK.md` as procedure shape only.
