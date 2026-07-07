# Main Runtime P1 Contract Tests

Scope: Issues #3836–#3840 (parent #3830).

| Issue | Test module |
|-------|-------------|
| #3836 Redis/Postgres/Ledger IO | `tests/unit/utils/test_runtime_io_ledger_contract.py` |
| #3837 Config / safety gates | `tests/unit/config/test_config_safety_gate_contract.py` |
| #3838 Main runtime flow | `tests/unit/runtime/test_main_runtime_flow_contract.py` |
| #3839 Health / metrics | `tests/unit/runtime/test_health_metrics_contract.py` |
| #3840 Profitability validation | `tests/unit/validation/test_profitability_validation_regression_contract.py` |

Guards (all modules):

- fixture/mock only — no live Redis, Postgres, Docker, or exchange
- fail-closed negative controls preferred over happy-path-only coverage
- health/metrics outputs must not imply Live-Go or LR-Go
- profitability scoring remains evidence-only (no promotion semantics)

LR remains **NO-GO**. Board stage `trade-capable` is orthogonal.
