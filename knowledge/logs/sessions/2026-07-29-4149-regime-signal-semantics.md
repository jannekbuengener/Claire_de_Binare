# Session 2026-07-29 — #4149 Regime/Signal Semantics

## Status
DONE_DRAFT_PR_PARTIAL_VALIDATION (39-window evidence partial)

## Delivered
- Draft PR #4189 @ `bf20e626` on `fix/4149-regime-signal-semantics`
- atr/close High-Vol semantics; event-time `pct_change_15m`; replay NULL regime
- Follow-up #4188 for offline TREND assign paths

## Validation
- 107 unit tests in regime/signal scopes passed locally
- ruff clean on touched paths; signal.schema.json valid JSON

## Boundaries
- LR NO-GO; no runtime/Docker/DB/MCP; no merge; issue left OPEN
- Ledger files (CURRENT_STATUS/CONTROL_REGISTER) untouched (parallel-wave lock)
