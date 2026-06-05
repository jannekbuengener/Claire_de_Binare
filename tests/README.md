---
relations:
  role: doc
  domain: tests
  upstream: []
  downstream: []
---
# Tests — unit, integration, replay, e2e

## Where to write / Where not to write
*   **Write here:** Tests under `unit/`, `integration/`, `replay/`, `e2e/`, `local/`.
*   **Do NOT write here:** Production services, non-test utilities.

## Key entrypoints
*   [Unit tests (tests/unit/)](unit/)
*   [Integration tests (tests/integration/)](integration/)
*   [Replay tests (tests/replay/)](replay/)
*   [E2E tests (tests/e2e/)](e2e/) — requires running stack (`@pytest.mark.e2e`)
*   [Pytest config (pytest.ini)](../pytest.ini)
*   [Makefile targets (Makefile)](../Makefile)

## CI mode (no containers)

```bash
make test
ruff check .
pytest -q -k "not test_mcp_time_server_runtime"
```

E2E / `local_only`: `make docker-up` then `make test-e2e` or `pytest -m local_only`.
