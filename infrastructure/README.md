# Infrastructure

Runtime and deployment infrastructure for Claire de Binare (Compose, database,
monitoring, Hermes, SurrealDB, scripts). This area is **not** a Live-Go or
secrets surface.

## Purpose

Own the executable and environment layout that BLUE/RED and local ops use.
Product code lives under `services/` and `core/`; governance and status SSOTs
live under `docs/` and `knowledge/`.

## Main areas

| Area | Role |
|---|---|
| [`compose/`](compose/README.md) | Compose canon (BLUE/RED, base/test labs) |
| [`database/`](database/README.md) | DB migrations and database ops docs |
| [`monitoring/`](monitoring/) | Prometheus/Grafana stack assets (local RED) |
| [`hermes/`](hermes/README.md) | Hermes Hetzner/ops packaging (no Live-Go) |
| [`surrealdb/`](surrealdb/README.md) | Local SurrealDB context runtime assets |
| [`scripts/`](scripts/README.md) | Infra helper scripts |
| [`actions-runner/`](actions-runner/README.md) | Historical/self-hosted runner notes |
| [`healthchecks/`](healthchecks/) | Healthcheck helpers |
| [`tls/`](tls/) | Local TLS material layout (no secrets in git) |
| `config/`, `docs/`, `logs/` | Infra-local config/docs/logs (non-canon status) |

## Boundaries

- **No secrets** in this tree. Secrets stay outside the repo (`SECRETS_PATH` /
  Docker secrets).
- **No Runtime-Go / Live-Go** from infra docs. LR remains **NO-GO**
  ([`docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`](../docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md)).
- Board stage `trade-capable` ≠ Live capital.
- Prefer [`tools/cdb.ps1`](../tools/cdb.ps1) / Makefile targets over ad-hoc
  compose invocations when operating from Windows.

## Quick entry

```bash
docker compose -f infrastructure/compose/compose.blue.yml up -d
docker compose -f infrastructure/compose/compose.red.yml up -d
```

See [`compose/README.md`](compose/README.md) for canon vs CI-lab baselines.

## Navigation

- [Projektübersicht](../README.md)
- [Services](../services/README.md)
- [Config](../config/README.md)
- [Runbooks](../docs/runbooks/README.md)
