# Shadow + Soak Evidence Run Index

This is the operator entrypoint for the existing shadow/evidence path.
It does not introduce a new runtime surface.

## Purpose

- Run `.github/workflows/shadow-soak-evidence.yml` reproducibly.
- Keep the existing LR-030/LR-031 shadow evidence chain intact.
- Pin the signal path to `primary_breakout_v1` while execution remains zero-execution/fail-closed.

## Canonical entrypoint

- Workflow: `.github/workflows/shadow-soak-evidence.yml`
- Trigger: `workflow_dispatch` or `schedule`

### CLI trigger

```bash
gh workflow run shadow-soak-evidence.yml -f mode=lean
```

## Strategy wiring for this workflow

- `SIGNAL_STRATEGY_ID=primary_breakout_v1`
- `SIGNAL_ADAPTER_ID=momentum_builtin`
- `SIGNAL_TRADE_SIDE_MODE=long_only`
- plus canonical v1 parameter env values from the workflow override

## Evidence artifacts to check

Within a successful run package, the machine-readable chain is:

1. `evidence/shadow_block_probe.json`
2. `evidence/endpoints/execution_metrics.txt`
3. `evidence/endpoints/risk_metrics.txt`
4. `evidence/evidence_index.json`
5. `evidence/soak_gate_eval.json`
6. `evidence/shadow_metrics_comparison.json`
7. `evidence/shadow_metrics_comparison.md`
8. `evidence/package_manifest.json`
9. `evidence/packages/<package_id>/manifest.json`

Hard invariants stay fail-closed:

- `execution_shadow_blocked_total >= 1`
- `execution_orders_filled_total == 0`
- probe order result remains `REJECTED`

## Boundary

- This is shadow-prereq evidence only.
- LR verdict remains `NO-GO`.
