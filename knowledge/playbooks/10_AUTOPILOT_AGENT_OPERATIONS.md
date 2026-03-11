# Autopilot / Agent Operations (2025-12-25)

## TL;DR
Autonomie ja, aber nur mit Guardrails: minimal scope, tests mandatory, live-data gated → fixtures.

## Gates
- E2E: `E2E_RUN=1`
- Extern/Live: `CDB_EXTERNAL_TESTS=1` (oder äquivalent) + marker

## Live → Fixture → Mock Pattern
1) Live Probe (opt-in) einmalig
2) Response/Request in Fixture (secrets redacted)
3) Offline Tests replayen Fixture deterministisch
