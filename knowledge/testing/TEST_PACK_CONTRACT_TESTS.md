# Test Pack Contract Tests

Status: active (Issue #3872 child slices — P0 + P1 + P2)
Scope: Test Pack manifest, operator drill evidence, kill-switch simulation,
MockExchange boundary, chaos assertions, metrics smoke, docs/issue-pack drift — test-only

## Purpose

Contract tests distinguish **frozen Test Pack artifacts** from live runtime proof.
They guard manifest/catalog integrity, operator evidence pack shape,
kill-switch drill simulation semantics, MockExchange adapter boundaries,
deterministic chaos assertion evaluation, metrics-smoke PASS/WARN/FAIL
semantics, and docs/issue-pack/prompt/scenario drift visibility without Docker,
alerts, live exchange, or real monitoring instances.
LR remains NO-GO; simulation and drill evidence are not Live-Go.

Drift detection is **detect-only**: tests report missing paths and stale TODO
hooks but do not auto-fix docs/templates or create GitHub issues.

| Issue | Test module | Rule protected |
|---|---|---|
| #3873 | `tests/unit/test_pack/test_test_pack_manifest_catalog_contract.py` | Manifest/catalog parseability, scenario IDs, artifact links, no live defaults |
| #3874 | `tests/unit/test_pack/test_operator_drill_evidence_pack_contract.py` | Evidence pack template, timestamps, operator fields, PASS/WARN/FAIL, no credentials in evidence |
| #3875 | `tests/unit/test_pack/test_kill_switch_drill_simulation_contract.py` | Simulated drill states (active/inactive/unknown), fail-closed unknown |
| #3876 | `tests/unit/test_pack/test_mock_exchange_cdb_integration_contract.py` | MockExchange shim boundary, order lifecycle, Valkey/cdb_redis separation |
| #3877 | `tests/unit/test_pack/test_chaos_scenario_assertion_contract.py` | Deterministic scenario generation, assertion PASS/FAIL, operator-only drill paths |
| #3878 | `tests/unit/test_pack/test_metrics_smoke_contract.py` | Metrics snapshot evaluation, no-data detection, PASS/WARN/FAIL semantics |
| #3879 | `tests/unit/test_pack/test_docs_issue_pack_drift_contract.py` | README/issue-pack/prompt/scenario path drift, stale TODO hook visibility, no-auto-fix contract |

Shared helpers: `tests/unit/test_pack/_test_pack_contract_helpers.py`  
Fixtures: `tests/fixtures/test_pack/` (includes `docs_drift_canon_v1.json`)

## Why contract / fixture / simulation tests

- **Testart:** Contract-Test + Simulation (see `knowledge/testing/README.md`).
- **Fail-closed:** Missing artifacts, unknown kill-switch state, no-data metrics,
  credential-like evidence content, or unresolved active-canon doc paths fail CI
  before operators treat partial packs as PASS.
- **Stale hooks visible:** Known frozen-pack TODO hooks (ingestion/metrics wiring,
  optional adapters doc) are cataloged by tests — not silently auto-fixed.
- **No runtime:** No BLUE/RED, no HTTP to risk service, no kill-switch file writes,
  no live Prometheus/Grafana, no dockerized chaos drills in standard CI.

## Validation commands

```bash
pytest -q tests/unit/test_pack/
pytest -q tests/unit -k "test_pack or docs or issue_pack or drift or template or prompt or scenario or todo"
ruff check tests/unit/test_pack/
```

## Non-goals

- New scenarios or MockExchange architecture.
- Productive operator drills or Alertmanager/Grafana mutations.
- Runtime-mutating LR-041/LR-042 drill execution in standard CI.
- Auto-fix of docs/templates or automatic issue creation from Test Pack.
- `CURRENT_STATUS.md` / ledger updates while #3872 remains open.
