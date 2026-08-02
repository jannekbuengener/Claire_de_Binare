# Core domain models

Shared domain types and event models used across services.

## Where to write / Where not to write
*   **Write here:** Domain models, events, shared secret-handling types that belong in the domain layer.
*   **Do NOT write here:** Service orchestration, Redis/Postgres wiring (see [`core/utils/`](../utils/README.md)), compose/runtime config.

## Key files
*   `models.py` — domain models
*   `event.py` — event types

## Navigation
- [Core overview](../README.md)
- [Contracts](../contracts/README.md)
- [Utils](../utils/README.md)
