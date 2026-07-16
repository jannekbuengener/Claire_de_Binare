<!--
Canonical Skill Source: docs/skills/cdb-backtest-engine/SKILL.md
Surface: opencode
Sync Status: mirrored-from-canon
Last Verified: 2026-07-01
Drift Policy: Surface-Adapter duerfen nur mit dokumentierter Begruendung abweichen.
-->
---
name: cdb-backtest-engine
description: Deterministic CDB backtesting and strategy evaluation in the Claire de Binare repository. Use when Codex needs to run or update offline backtests, parameter sweeps, walk-forward tests, baseline comparisons, or PR-ready evidence packs. Treat the local Claire de Binare repository as canon, not the retired external docs repo; never infer live readiness from Board stage; no live keys, no live or testnet execution.
disable-model-invocation: true
---

# Backtest Engine

## Canon first
- Use local repository paths only.
- Read `CURRENT_STATUS.md` for repo and engineering context.
- Read `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` for Echtgeld guardrails and current `NO-GO`.
- Read `docs/runbooks/CONTROL_REGISTER.md` for Board stage, but never treat `trade-capable` as live authorization.

## Use this when you see
- backtest, walk-forward, parameter sweep
- baseline comparison or regression check
- equity curve, drawdown, Sharpe, profit factor
- evidence pack, report, or gate-supporting metrics

## Hard rules
- Evidence over assumptions: if the dataset, baseline, or configuration is ambiguous, stop and surface the missing artifact.
- Determinism required: freeze dataset window, seed, parameters, and code reference.
- Offline replay only. Do not call live or testnet endpoints.
- Always print output artifact paths in the final response.

## Default deliverables
1. `results.json` for raw run output when available
2. `metrics.json` for computed summary
3. `report.md` for human-readable evidence
4. `compare.md` only when a baseline is provided
