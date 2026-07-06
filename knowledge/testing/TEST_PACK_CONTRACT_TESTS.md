# Test Pack Contract Tests

Status: active (Issue #3872 child slices — P0 + P1)
Scope: Test Pack manifest, operator drill evidence, kill-switch simulation,
MockExchange boundary, chaos assertions, metrics smoke — test-only

## Purpose

Contract tests distinguish **frozen Test Pack artifacts** from live runtime proof.
They guard manifest/catalog integrity, operator evidence pack shape,
kill-switch drill simulation semantics, MockExchange adapter boundaries,
deterministic chaos assertion evaluation, and metrics-smoke PASS/WARN/FAIL
semantics without Docker, alerts, live exchange, or real monitoring instances.
LR remains NO-GO; simulation and drill evidence are not Live-Go.

| Issue | Test module | Rule protected |
|---|---|---|
| #3873 | `tests/unit/test_pack/test_test_pack_manifest_catalog_contract.py` | Manifest/catalog parseability, scenario IDs, artifact links, no live defaults |
| #3874 | `tests/unit/test_pack/test_operator_drill_evidence_pack_contract.py` | Evidence pack template, timestamps, operator fields, PASS/WARN/FAIL, no credentials in evidence |
| #3875 | `tests/unit/test_pack/test_kill_switch_drill_simulation_contract.py` | Simulated drill states (active/inactive/unknown), fail-closed unknown |
| #3876 | `tests/unit/test_pack/test_mock_exchange_cdb_integration_contract.py` | MockExchange shim boundary, order lifecycle, Valkey/cdb_redis separation |
| #3877 | `tests/unit/test_pack/test_chaos_scenario_assertion_contract.py` | Deterministic scenario generation, assertion PASS/FAIL, operator-only drill paths |
| #3878 | `tests/unit/test_pack/test_metrics_smoke_contract.py` | Metrics snapshot evaluation, no-data detection, PASS/WARN/FAIL semantics |

Shared helpers: `tests/unit/test_pack/_test_pack_contract_helpers.py`  
Fixtures: `tests/fixtures/test_pack/`

## Why contract / fixture / simulation tests

- **Testart:** Contract-Test + Simulation (see `knowledge/testing/README.md`).
- **Fail-closed:** Missing artifacts, unknown kill-switch state, no-data metrics,
  or credential-like evidence content fails CI before operators treat partial packs as PASS.
- **No runtime:** No BLUE/RED, no HTTP to risk service, no kill-switch file writes,
  no live Prometheus/Grafana, no dockerized chaos drills in standard CI.

## Validation commands

```bash
pytest -q tests/unit/test_pack/
pytest -q tests/unit -k "mock_exchange or mockexchange or chaos or assertion or metrics or smoke or snapshot or no_data or test_pack"
ruff check tests/unit/test_pack/
```

## Non-goals

- New scenarios or MockExchange architecture.
- Productive operator drills or Alertmanager/Grafana mutations.
- Runtime-mutating LR-041/LR-042 drill execution in standard CI.
- `CURRENT_STATUS.md` / ledger updates while #3872 remains open.
