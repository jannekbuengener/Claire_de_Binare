---
relations:
  role: doc
  domain: tests
  upstream: []
  downstream: []
---
# Tests — taxonomy and CI

## Layout

| Tree | Marker / convention | Containers | README |
|---|---|---|---|
| [`unit/`](unit/) | `@pytest.mark.unit` | None (CI default) | — (per-module tests) |
| [`integration/`](integration/) | `@pytest.mark.integration` | Mocked externals only | [README](integration/README.md) |
| [`replay/`](replay/) | folder convention | Usually none | [README](replay/README.md) |
| [`e2e/`](e2e/) | `@pytest.mark.e2e` | BLUE+RED (`make docker-up`) | — |
| [`local/`](local/) | `@pytest.mark.local_only` | Running stack; not CI | — |
| [`smoke/`](smoke/) | `@pytest.mark.smoke` (where set) | MCP deps for runtime smoke | [README](smoke/README.md) |
| [`chaos/`](chaos/) | `@pytest.mark.chaos` | Destructive / local | — |

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
- [`tests/fixtures/README.md`](fixtures/README.md) — deterministic fixtures
