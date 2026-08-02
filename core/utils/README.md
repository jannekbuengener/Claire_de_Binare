# Core utilities

Shared infrastructure helpers imported by services (Redis/Postgres clients, rate limiter, clock, UUID generation).

## Where to write / Where not to write
*   **Write here:** Pool-backed clients and small shared helpers used by multiple services.
*   **Do NOT write here:** Domain models ([`core/domain/`](../domain/README.md)), decision contracts ([`core/contracts/`](../contracts/README.md)), service-local glue.

## Key modules
*   `redis_client.py` — `create_redis_client` / shared connection pools
*   `postgres_client.py` — Postgres helpers
*   `clock.py`, `uuid_gen.py`, `rate_limiter.py`

## Navigation
- [Core overview](../README.md)
- [Domain](../domain/README.md)
- [Services](../../services/README.md)
