# Shared core logic and domain models.

## Where to write / Where not to write
*   **Write here:** Python core modules, domain models, shared utilities, contracts under `core/contracts/`.
*   **Do NOT write here:** Service-specific business logic, long-lived runtime processes, Docker/compose config.

## Key entrypoints
*   [`core/domain/`](domain/README.md) — domain models
*   [`core/utils/`](utils/README.md) — shared utilities (Redis/Postgres clients, clock, UUID)
*   [`core/contracts/`](contracts/README.md) — decision / trace contracts
*   [`core/replay/`](replay/README.md) — replay envelopes and canonical JSON
*   [`services/`](../services/README.md) — service implementations

## Other packages (leaf / secondary)

| Package | Role |
|---|---|
| [`clients/`](clients/) | Exchange/API clients (no area README; import from services) |
| [`config/`](config/) | Feature flags / trading mode helpers |
| [`indicators/`](indicators/) | Technical indicators |
| [`safety/`](safety/) | Kill-switch helpers |

## SSOT boundary
Contract and status SSOTs live outside this directory — see [`knowledge/contracts/README.md`](../knowledge/contracts/README.md) and [`CURRENT_STATUS.md`](../CURRENT_STATUS.md).

## Navigation

- [Projektübersicht](../README.md)
- [Dokumentationsindex](../docs/index.md)
- [Services](../services/README.md)
