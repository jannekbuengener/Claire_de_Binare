# ARVP P0 Contract Tests

Scope: issues #3821–#3823 (parent #3820).

| Issue | Test module | Protects |
|-------|-------------|----------|
| #3821 | `tests/unit/arvp/test_arvp_runtime_event_chain_contract.py` | Paper runtime chain SIGNAL→DECISION→ORDER→FILL via ChainDetector |
| #3822 | `tests/unit/arvp/test_arvp_calibration_gate_regression_contract.py` | Replay→paper reference→compare→calibration→ARVP gate regression |
| #3823 | `tests/unit/arvp/test_arvp_campaign_supervisor_state_machine_contract.py` | Campaign supervisor terminal states, probe layer, GitHub reporter read-only |

Run:

```bash
pytest -q tests/unit/arvp/test_arvp_runtime_event_chain_contract.py tests/unit/arvp/test_arvp_calibration_gate_regression_contract.py tests/unit/arvp/test_arvp_campaign_supervisor_state_machine_contract.py -m contract
```

Boundaries: fixture/unit only; no Docker, live DB, harvester runtime, or LR/live go.
