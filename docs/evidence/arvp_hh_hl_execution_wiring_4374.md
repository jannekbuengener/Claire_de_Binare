# hh_hl #4374 — Production Execution Wiring Evidence

Status: WIRING SLICE COMPLETE — production path wired, **0 campaign runs**.
Scope: Issue #4374 execute-wiring only. No Owner-GO post/edit. LR = **NO-GO**.

## Root cause addressed

1. `resolve_campaign_executor(hh_hl_continuation_replay_v1)` previously returned
   `HhHlSingleRunReplayProvider` with `single_run_callable=None` →
   `HOLD_EXECUTION_SINGLE_RUN_CALLABLE_UNSET`.
2. No AuthorizationContext-bound entry-point propagated to
   `services.validation.strategy_replay_runner` single-run.

## Production path (WIRED_AND_REACHABLE)

```
Owner Execution-GO (live verify)
  → AuthorizationContext
  → hh_hl_campaign_execute (preflight|execute|status)
  → hh_hl_campaign_lifecycle (bindings/startable/resume)
  → HhHlSingleRunReplayProvider (+ AuthorizationContext)
  → build_production_single_run_callable
  → ARVPReplayConfig (binance_window / hh_hl / batch_b)
  → run_arvp_replay_detailed / run_arvp_replay
  → Batch-B dispatch → run_hh_hl_continuation_backtest
  → bound run artifacts + state markers
```

## Delivered files

- `tools/arvp_vacation/hh_hl_single_run_callable.py` — production callable
- `tools/arvp_vacation/hh_hl_campaign_execute.py` — preflight/execute/status
- `tools/arvp_vacation/campaign_executor_providers.py` — production wiring
- `services/validation/strategy_replay_runner.py` — hh_hl binance_window allowlist +
  `ArvpReplayOutcome` / `run_arvp_replay_detailed`
- `tests/unit/arvp/test_hh_hl_campaign_execute_wiring.py`

## Explicit non-goals (this slice)

- No campaign execute against live GO `#5213976751` (invalid fence; inert)
- No Owner-GO post/edit
- No analyzer / reproduction / Stage-B / paper / live / promotion

## Auth / runtime-gate hardening (PR #4380 follow-up)

Status: `DONE_PR_4380_AUTH_RUNTIME_GATES_HARDENED` candidate evidence.

### Removed public test surfaces

- Removed `--fixture-json` and `--design-go-fixture-json` from
  `hh_hl_campaign_execute` argparse.
- Production `_owner_go_fetcher` always resolves to
  `default_gh_comment_fetcher` unless a private `_test_set_owner_go_fetcher`
  injection is active (unit tests only).
- Design-GO receipt resolution uses reference receipt only (no CLI fixture).
- No env-var / hidden CLI offline bypass.

### Runtime surface gate

- Removed tautological
  `payload.surface_capability_fingerprint == ctx.surface_capability_fingerprint`
  self-check (never claimed as current-surface proof).
- `surface_capability_fingerprint` retained as Owner-authorized historical
  post-merge surface-receipt binding on `AuthorizationContext`.
- Fresh free-disk threshold gate:
  `current free_disk_bytes >= resource_budget.minimum_free_disk_bytes`
  via `measure_free_disk_bytes` / injectable `_test_set_free_disk_bytes`
  → `HOLD_EXECUTION_FREE_DISK_BELOW_MINIMUM` before any callable.
- Live gates remain: execution_sha checkout, provider callable, strategy/
  adapter via plan rebuild, FINAL run-plan exact, 39 unique keys, dataset
  aggregate bindings, max_parallelism/in_flight/attempts/max_run_count ==
  authorized caps.

### Authorization bypass audit verdict

`NO_PRODUCTION_TEST_BYPASS`

## Next gate (post-merge, separate session)

1. Rebuild FINAL plan + surface receipt on new main SHA
2. Post **new** Owner Execution-GO with correct triple-backtick fence
3. Supervised `hh_hl_campaign_execute execute` for exact 39 baseline runs
