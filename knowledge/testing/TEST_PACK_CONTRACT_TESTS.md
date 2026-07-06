# Test Pack Contract Tests

Status: active (Issue #3872 child slice — P0)
Scope: Test Pack manifest, operator drill evidence, kill-switch simulation — test-only

## Purpose

Contract tests distinguish **frozen Test Pack artifacts** from live runtime proof.
They guard manifest/catalog integrity, operator evidence pack shape, and
kill-switch drill simulation semantics without Docker, alerts, or real kill-switch
activation. LR remains NO-GO; simulation and drill evidence are not Live-Go.

| Issue | Test module | Rule protected |
|---|---|---|
| #3873 | `tests/unit/test_pack/test_test_pack_manifest_catalog_contract.py` | Manifest/catalog parseability, scenario IDs, artifact links, no live defaults |
| #3874 | `tests/unit/test_pack/test_operator_drill_evidence_pack_contract.py` | Evidence pack template, timestamps, operator fields, PASS/WARN/FAIL, no-secret |
| #3875 | `tests/unit/test_pack/test_kill_switch_drill_simulation_contract.py` | Simulated drill states (active/inactive/unknown), fail-closed unknown |

Shared helpers: `tests/unit/test_pack/_test_pack_contract_helpers.py`  
Fixtures: `tests/fixtures/test_pack/`

## Why contract / fixture / simulation tests

- **Testart:** Contract-Test + Simulation (see `knowledge/testing/README.md`).
- **Fail-closed:** Missing artifacts, unknown kill-switch state, or secret-like
  evidence content fails CI before operators treat partial packs as PASS.
- **No runtime:** No BLUE/RED, no HTTP to risk service, no kill-switch file writes.

## Validation commands

```bash
pytest -q tests/unit/test_pack/
pytest -q tests/unit -k "test_pack or manifest or scenario or operator or drill or kill_switch or evidence"
ruff check tests/unit/test_pack/
```

## Non-goals

- New scenarios or MockExchange architecture.
- Productive operator drills or Alertmanager/Grafana mutations.
- `CURRENT_STATUS.md` / ledger updates while #3872 remains open.
