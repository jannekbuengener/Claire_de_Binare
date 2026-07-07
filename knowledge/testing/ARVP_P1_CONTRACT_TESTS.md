# ARVP P1 Contract Tests

Scope: issues #3826–#3829 (parent #3820).

| Issue | Test module | Protects |
|-------|-------------|----------|
| #3826 | `test_arvp_scenario_pack_matrix_contract.py` | Strategy × scenario-pack matrix, adapter validation, fail-closed unsupported/blocked combos |
| #3827 | `test_arvp_window_qualification_contract.py` | Window cadence/gap/warmup, regime + paper availability, honest PASS/WARN/BLOCKED |
| #3828 | `test_arvp_evidence_harvester_mapping_contract.py` | Harvester gaps/safety → packet limitations; no coverage→profitability promotion |
| #3829 | `test_arvp_runtime_negative_controls_contract.py` | Invalid/blocked runtime inputs produce no orders/fills/executor/DB writes |

Run:

```bash
pytest -q tests/unit/arvp/ -m contract
```

Boundaries: fixture/unit only; no Docker, live DB, harvester runtime, or LR/live go.
