---
relations:
  role: doc
  domain: tests
  upstream: []
  downstream: []
---
# Tests — taxonomy and CI

## Layout

| Tree | Marker / convention | Containers | Notes |
|---|---|---|---|
| [`unit/`](unit/) | `@pytest.mark.unit` | None (CI default) | Per-module tests; no tree README |
| [`integration/`](integration/README.md) | `@pytest.mark.integration` | Mocked externals only | CI |
| [`replay/`](replay/README.md) | folder convention | Usually none | Deterministic replay |
| [`e2e/`](e2e/README.md) | `@pytest.mark.e2e` | BLUE+RED (`make docker-up`) | Not CI default |
| [`local/`](local/) | `@pytest.mark.local_only` | Running stack; not CI | No tree README |
| [`smoke/`](smoke/README.md) | `@pytest.mark.smoke` (where set) | MCP deps for runtime smoke | |
| [`chaos/`](chaos/) | `@pytest.mark.chaos` | Destructive / local | No tree README |
| [`contract/`](contract/) | `@pytest.mark.contract` | None / mocks | Contract checks |
| [`surrealdb/`](surrealdb/) | SurrealDB-local suites | Optional local DB | Context/brain tests |
| [`tools/`](tools/) | Tool-module tests | None | |
| [`fixtures/`](fixtures/README.md) | Shared fixtures | N/A | Deterministic inputs |
| `load/`, `performance/`, `resilience/` | specialty markers | Varies | Not CI default |

## CI (no containers)

```bash
make test
ruff check .
pytest -q -k "not test_mcp_time_server_runtime"
```

Equivalently: `make test-unit && make test-integration`.

## With stack

```bash
make docker-up
make test-e2e
pytest -v -m local_only   # explicit local_only only
```

## SSOT boundary

- Green CI does not imply live-readiness Go; see [`docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`](../docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md) (**NO-GO**).

## Related

- [`pytest.ini`](../pytest.ini) — markers and defaults
- [`Makefile`](../Makefile) — `test`, `test-unit`, `test-integration`, `test-e2e`, `test-coverage`
- [`knowledge/testing/README.md`](../knowledge/testing/README.md) — Test-First contract

## Navigation

- [Projektübersicht](../README.md)
- [Dokumentationsindex](../docs/index.md)
- [Developer onboarding](../DEVELOPER_ONBOARDING.md)
