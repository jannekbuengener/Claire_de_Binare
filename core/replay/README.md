# Replay (`core/replay/`)

Deterministische Replay-, Shadow- und Envelope-Hilfen. Kein eigenständiger Service — wird von Services, Tools und Tests importiert.

## Scope

| Modul | Zweck |
|---|---|
| [`canonical_json.py`](canonical_json.py) | Sortierte JSON-Serialisierung für stabile Hashes |
| [`envelopes.py`](envelopes.py) | `DecisionEnvelopeV1` → `OrderEnvelopeV1` → `FillEnvelopeV1` |
| [`publisher.py`](publisher.py) | Replay-Publisher für Shadow-Streams |
| [`decision_contract_v1`](../contracts/decision_contract_v1.py) | TRACE_CONTRACT_V1 Bundle (siehe [`core/contracts/README.md`](../contracts/README.md)) |
| [`replay_report_builder.py`](replay_report_builder.py) | Replay-Report-Aggregation |
| [`determinism.py`](determinism.py) | Determinismus-Checks |
| [`scenario_harness.py`](scenario_harness.py) | Szenario-Packs und Harness |

## SSOT boundary

- Live-Readiness bleibt [`docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`](../../docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md) (**NO-GO** für Echtgeld).
- Replay-Evidence ist kein LR-Go.

## Tests

| Pfad | Marker |
|---|---|
| [`tests/replay/`](../../tests/replay/) | Replay-spezifische Tests |
| [`tests/unit/`](../../tests/unit/) | Unit-Tests mit Replay-Mocks |

```bash
pytest -v tests/replay/
make test-unit
```

## Related

- [`core/contracts/README.md`](../contracts/README.md)
- [`knowledge/systems/`](../../knowledge/systems/) — Architektur-Notizen (repo-backed)
- [`services/validation/README.md`](../../services/validation/README.md)
