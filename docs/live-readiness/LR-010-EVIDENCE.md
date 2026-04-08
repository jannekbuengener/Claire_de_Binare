# LR-010 Evidence: Risk Engine Deterministic Unit Test Coverage

**Issue:** #779
**Status:** PASS
**Date:** 2026-03-19
**PASS confirmed:** 2026-03-19

## Ziel

LR-010 verlangt deterministische, isolierte Testabdeckung für das Kernverhalten der Risk Engine. Das Control ist erfüllt, wenn zentrale Entscheidungslogik und sicherheitskritische Boundary Conditions durch reproduzierbare Unit-Tests belegt sind, ohne Abhängigkeit von laufenden Services oder externem Zustand.

## Scope

Diese Evidenz deckt die folgenden deterministischen Unit-Test-Bereiche ab:

- Circuit-Breaker-Verhalten in `services/risk/circuit_breakers.py`
- Risk-Service-Initialisierung, Konfigurationsvalidierung und Cooldown-Logik
- Signal-Serialisierung und Contract-Invarianten
- Core-Risk-Engine-Entscheidungen wie Approve/Reject, Position Sizing, Stop-Loss-Generierung und Invalid-Input-Handling

Diese Evidenz behauptet ausdrücklich **nicht** Integration-, Chaos- oder Live-Run-Nachweise. Diese liegen in anderen Controls und Evidence-Artefakten.

## Evidence Anchors

- `tests/unit/risk/test_circuit_breakers.py`
  - Breaker-Thresholds, Multi-Breaker-Interaktion, Bypass-Handling, Boundary Cases
- `tests/unit/risk/test_service.py`
  - Service-Initialisierung, Config-Validierung, Cooldown-Logik
- `tests/unit/risk/test_signal_serialization.py`
  - Serialisierung, Roundtrip, Type Coercion, None-Handling
- `tests/unit/risk/test_contract_enforcement.py`
  - Contract-Enforcement-Invarianten
- `tests/unit/risk/test_shadow_unwind_suppression.py`
  - Shadow-Mode-Unwind-Suppression
- `tests/unit/risk/test_metrics_endpoint.py`
  - Metrics-Endpoint-Verhalten
- `tests/unit/risk/test_flask_import_guard.py`
  - Import-Guard-Verhalten
- `tests/unit/verlosung/test_risk_engine_core.py`
  - Approve/Reject-Pfade, Position Sizing, Stop-Loss-Generierung
- `tests/unit/verlosung/test_risk_engine_edge_cases.py`
  - Invalid Price, Exposure Limit, Short-Signal-Stop-Loss, Notional-Edge-Cases

## CI Path

Die oben genannten Testanker liegen im regulären CI-Testpfad:

```yaml
# .github/workflows/ci.yml
- name: Tests
  run: pytest -q -k "not test_mcp_time_server_runtime"
```

Da der CI-Befehl die Repo-Test-Suite ohne Directory-Exclusion für die genannten Pfade ausführt, sind die LR-010-Unit-Tests Teil des CI-Ausführungspfads.

## Verification Commands

```bash
pytest -q tests/unit/risk tests/unit/verlosung
pytest --collect-only -q tests/unit/risk tests/unit/verlosung
```

## Status Interpretation

IMPLEMENTED ist gerechtfertigt, wenn die oben genannten control-spezifischen Testanker vorhanden sind und im CI-Pfad liegen.

PASS erfordert einen bestätigten grünen CI-Run mit nachvollziehbarer Referenz auf main.

**PASS-Referenz (verifiziert 2026-03-19):**

- Run ID: `23295248170`
- Commit: `e164abe474c64981036ceee86222b7db95e48e32`
- Branch: `main`
- Job: `ci (Unit/Integration + Lint gesammelt)` — conclusion: `success`
- Step: `Tests` (`pytest -q -k "not test_mcp_time_server_runtime"`) — conclusion: `success`
- URL: https://github.com/jannekbuengener/Claire_de_Binare/actions/runs/23295248170

Alle LR-010-Testanker liegen im `tests/unit/risk/` und `tests/unit/verlosung/` Pfad, der vom obigen CI-Run ohne Directory-Exclusion ausgeführt wurde.

## Go/No-Go Relevanz

LR-010 bleibt ein Hard Gate in `governance/p5_canary_readiness.yaml`, weil ein Defekt in der Core-Risk-Logik Canary-Schutzmechanismen direkt unterlaufen kann. Deterministische Unit-Tests sind der erste Verifikations-Layer vor Integration, Soak und operativer Freigabe.
