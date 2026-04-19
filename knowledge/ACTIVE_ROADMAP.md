# ACTIVE_ROADMAP

Status: canonical local pointer page

## Purpose

This file is the short roadmap entrypoint used by agents and humans at session
start. It now resolves only to local working-repo sources.

## Canonical Locations (current)

- Working repo / engineering status: `CURRENT_STATUS.md`
- Operational live-readiness status: `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
- Control board status + workflow controls: `docs/runbooks/CONTROL_REGISTER.md`
- Strategy specification: `knowledge/contracts/PRIMARY_BREAKOUT_V1.md`
- Validation canon + deterministic runner: `knowledge/contracts/PRIMARY_BREAKOUT_V1_VALIDATION.md` / `services/validation/strategy_backtest_runner.py`
- Historical knowledge snapshot: `knowledge/CURRENT_STATUS.md` (context only)
- Canon and archive policy: `docs/meta/WORKING_REPO_CANON.md`

## Historical Milestone Plans (context only)

- `knowledge/roadmap/` — legacy M7/M8/M9 milestone plans from Dec 2025.
  These reflect planning assumptions (team size, security lead, external pentest)
  that no longer match the current solo-maintainer reality. Retained for
  historical context, not as operative guidance.

## Current Focus

- deterministic validation and backtesting for `primary_breakout_v1`
- shadow/mock-only operation with reproducible, repo-backed evidence
- data substance, run reproducibility, and evidence chain integrity

## Working Rule

Board stage `trade-capable` does not imply LR-Go. Live-readiness verdict remains
NO-GO. Real-capital operation requires explicit human gate and passing LR-SSOT
criteria. See `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`.

No default path in the roadmap should require an external docs repository. Use
the local archive snapshot only for historical lookup.
