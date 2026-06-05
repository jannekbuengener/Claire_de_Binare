# Integration tests (`tests/integration/`)

Tests mit gemockten externen Abhängigkeiten (Redis, Postgres, Exchange). Laufen in CI ohne Docker-Stack.

## Marker

- `@pytest.mark.integration`
- Ausgeschlossen von Default-CI: `e2e`, `local_only` (siehe [`pytest.ini`](../../pytest.ini))

## Commands

```bash
make test-integration
pytest -v -m "integration and not e2e and not local_only"
```

## SSOT boundary

- Kein E2E-Stack nötig; für echte Container siehe [`tests/e2e/`](../e2e/) und [`tests/README.md`](../README.md).
- LR bleibt **NO-GO** — Integration-Grün beweist keine Live-Freigabe.

## Related

- [`tests/README.md`](../README.md) — Gesamt-Taxonomie
- [`Makefile`](../../Makefile) — `test`, `test-integration`
