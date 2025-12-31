---
relations:
  role: doc
  domain: tests
  upstream: []
  downstream: []
---
# All unit, integration, and replay tests.

## Where to write / Where not to write
*   **Write here:** Test files organized by `unit/`, `integration/`, and `replay/` categories.
*   **Do NOT write here:** Production code, non-test utilities, actual service implementations.

## Key entrypoints
*   [Unit Tests (tests/unit/)](tests/unit/)
*   [Integration Tests (tests/integration/)](tests/integration/)
*   [Replay Tests (tests/replay/)](tests/replay/)
*   [Pytest Configuration (pytest.ini)](pytest.ini)
*   [Makefile Test Commands (Makefile)](Makefile)

