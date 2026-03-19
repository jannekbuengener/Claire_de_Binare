# LR-041 Chaos Verdict - 2026-03-10T10:19:18.047291+00:00

- drill_id: `LR-041`
- runner_version: `1.0`
- overall: `PASS`
- injection_method: `docker_restart`

## Scenario Results

| Scenario | Status | Container Recovery | Service Recovery | Filled Delta |
| --- | --- | --- | --- | --- |
| redis_restart | PASS | 11.172s | 4.047s | 0.000 |
| postgres_restart | PASS | 11.156s | 4.016s | 0.000 |

## Hard Invariants

- shadow_runtime_preserved: `True`
- zero_execution_preserved: `True`

## Observations

- collateral_restarts: `{'redis_restart': {'cdb_risk': 2, 'cdb_db_writer': 1}, 'postgres_restart': {'cdb_risk': 2, 'cdb_db_writer': 1}}`

## Pass Criteria (Issue #787)

- Redis Recovery <30.0s: `True`
- Postgres Recovery <60.0s: `True`
