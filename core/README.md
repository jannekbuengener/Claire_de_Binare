# Shared core logic and domain models.

## Where to write / Where not to write
*   **Write here:** Python core modules, domain models, shared utilities, contracts under `core/contracts/`.
*   **Do NOT write here:** Service-specific business logic, long-lived runtime processes, Docker/compose config.

## Key entrypoints
*   [Domain models (core/domain/)](domain/)
*   [Shared utilities (core/utils/)](utils/)
*   [Decision / trace contracts (core/contracts/)](contracts/)
*   [Replay envelopes (core/replay/)](replay/)
*   [Service implementations (services/)](../services/)

## SSOT boundary
Contract and status SSOTs live outside this directory — see `knowledge/contracts/README.md` and `CURRENT_STATUS.md`.
