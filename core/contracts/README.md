# Contracts (`core/contracts/`)

Python-Implementierung von Entscheidungs- und Adapter-Verträgen. Schema-Artefakte und narrative Specs liegen zusätzlich unter `docs/contracts/` und `knowledge/contracts/`.

## Scope

| Modul | Zweck |
|---|---|
| [`decision_contract_v1.py`](decision_contract_v1.py) | TRACE_CONTRACT_V1: `build_decision_contract_v1_bundle`, Money/Quantity-Quantisierung (`Decimal`) |
| [`external_adapter_contracts.py`](external_adapter_contracts.py) | Externe Adapter-Grenzen |
| [`external_adapter_registry.py`](external_adapter_registry.py) | Adapter-Registry |
| [`primary_breakout_v1_config.py`](primary_breakout_v1_config.py) | Strategie-Config-Surface |

## SSOT boundary

- Operativer LR-Status: [`docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`](../../docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md) (**NO-GO**).
- Docs-Index: [`docs/contracts/README.md`](../../docs/contracts/README.md).

## Tests

```bash
pytest -v tests/unit -k "contract"
pytest -v tests/unit/risk/test_contract_enforcement.py
```

## Related

- [`core/replay/README.md`](../replay/README.md) — Envelopes und kanonisches JSON
- [`services/risk/README.md`](../../services/risk/README.md) — Risk-Gate nutzt Decision Contract
